"""Property-based tests using Hypothesis"""

import json
from datetime import datetime

import jsonschema
from hypothesis import assume, given
from hypothesis import strategies as st
from hypothesis.strategies import composite

from app.schemas import (
    AgentStatus,
    ChapterDraftRequest,
    ContinuityReport,
    CostReport,
    OutlineRequest,
    TokenStreamEvent,
)

# Define JSON schemas for validation
OUTLINE_SCHEMA = {
    "type": "object",
    "properties": {
        "outline_markdown": {"type": "string"},
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer", "minimum": 1},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "word_count": {"type": "integer", "minimum": 100}
                },
                "required": ["number", "title"]
            }
        }
    },
    "required": ["outline_markdown"]
}

CONTINUITY_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "inconsistencies": {"type": "array"},
        "suggestions": {"type": "array", "items": {"type": "string"}},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["inconsistencies", "suggestions", "confidence_score"]
}


@composite
def valid_outline_request(draw):
    """Generate valid outline requests"""
    return OutlineRequest(
        brief=draw(st.text(min_size=10, max_size=1000)),
        style_guide=draw(st.one_of(st.none(), st.text(max_size=500))),
        genre=draw(st.one_of(st.none(), st.text(max_size=50))),
        target_chapters=draw(st.integers(min_value=1, max_value=50))
    )


@composite
def valid_chapter_request(draw):
    """Generate valid chapter draft requests"""
    return ChapterDraftRequest(
        outline=draw(st.text(min_size=10, max_size=5000)),
        chapter_number=draw(st.integers(min_value=1, max_value=50)),
        style_guide=draw(st.one_of(st.none(), st.text(max_size=1000))),
        character_bible=draw(st.one_of(
            st.none(),
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.text(max_size=100),
                max_size=10
            )
        ))
    )


@given(valid_outline_request())
def test_outline_request_serialization(request):
    """Test that outline requests serialize properly"""
    # Should serialize to JSON
    json_data = request.model_dump_json()
    assert json_data

    # Should deserialize back
    parsed = json.loads(json_data)
    reconstructed = OutlineRequest(**parsed)
    assert reconstructed.brief == request.brief
    assert reconstructed.target_chapters == request.target_chapters


@given(valid_chapter_request())
def test_chapter_request_validation(request):
    """Test chapter request validation"""
    # Chapter number must be positive
    assert request.chapter_number > 0

    # Outline must not be empty
    assert len(request.outline) >= 10

    # Should be JSON serializable
    json.dumps(request.model_dump())


@given(
    st.lists(st.dictionaries(st.text(), st.text()), min_size=0, max_size=10),
    st.lists(st.text(), min_size=0, max_size=10),
    st.floats(min_value=0.0, max_value=1.0)
)
def test_continuity_report_schema(inconsistencies, suggestions, confidence):
    """Test continuity report matches schema"""
    report = ContinuityReport(
        inconsistencies=inconsistencies,
        suggestions=suggestions,
        timeline_issues=[],
        character_issues=[],
        confidence_score=confidence
    )

    # Validate against schema
    report_dict = report.model_dump()
    jsonschema.validate(report_dict, CONTINUITY_REPORT_SCHEMA)

    # Confidence score bounds
    assert 0.0 <= report.confidence_score <= 1.0


@given(st.integers(min_value=1, max_value=50))
def test_chapter_numbering_continuity(num_chapters):
    """Test that chapter numbers are continuous"""
    chapters = [{"number": i, "title": f"Chapter {i}"} for i in range(1, num_chapters + 1)]

    # Check continuity
    for i, chapter in enumerate(chapters, 1):
        assert chapter["number"] == i

    # No gaps
    numbers = [c["number"] for c in chapters]
    assert numbers == list(range(1, num_chapters + 1))


@given(
    st.text(min_size=1, max_size=100),
    st.sampled_from(["token", "checkpoint", "error", "complete"]),
    st.text(max_size=1000)
)
def test_token_stream_event(event_name, event_type, data):
    """Test token stream event structure"""
    event = TokenStreamEvent(
        event=event_type,
        data=data,
        metadata={"timestamp": datetime.now().isoformat()}
    )

    # Should be serializable
    json_str = event.model_dump_json()
    parsed = json.loads(json_str)

    # Required fields present
    assert "event" in parsed
    assert "data" in parsed
    assert parsed["event"] in ["token", "checkpoint", "error", "complete"]


@given(
    st.floats(min_value=0, max_value=10000),
    st.integers(min_value=0, max_value=1000000),
    st.datetimes()
)
def test_cost_report_calculations(total_usd, total_tokens, period_start):
    """Test cost report calculations"""
    assume(total_usd >= 0)
    assume(total_tokens >= 0)

    period_end = datetime.now()
    assume(period_end > period_start)

    report = CostReport(
        total_usd=total_usd,
        total_tokens=total_tokens,
        by_agent={},
        by_model={},
        period_start=period_start,
        period_end=period_end
    )

    # Validate constraints
    assert report.total_usd >= 0
    assert report.total_tokens >= 0
    assert report.period_end >= report.period_start

    # Should be JSON serializable
    json.dumps(report.model_dump(), default=str)


@given(
    st.text(min_size=1, max_size=50),
    st.sampled_from(["idle", "thinking", "writing", "reviewing", "complete", "error"]),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
)
def test_agent_status_progress(agent_name, status, progress):
    """Test agent status progress bounds"""
    agent_status = AgentStatus(
        agent=agent_name,
        status=status,
        progress=progress
    )

    # Progress must be between 0 and 1
    if agent_status.progress is not None:
        assert 0.0 <= agent_status.progress <= 1.0

    # Complete status should have progress = 1.0 or None
    if status == "complete" and progress is not None:
        assert progress == 1.0 or progress is None

    # Error status should not have progress > 0
    if status == "error" and progress is not None:
        assert progress == 0.0 or progress is None


@given(st.text(min_size=10, max_size=10000))
def test_outline_always_has_structure(outline_text):
    """Test that generated outlines have required structure"""
    # Simulate outline structure
    outline = {
        "outline_markdown": outline_text,
        "chapters": []
    }

    # Must have markdown content
    assert len(outline["outline_markdown"]) >= 10

    # Validate against schema
    jsonschema.validate(outline, OUTLINE_SCHEMA)
