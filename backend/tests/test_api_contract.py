"""API contract tests for sopher.ai backend"""

import pytest
import httpx
from httpx import AsyncClient
from fastapi.testclient import TestClient
import json
from unittest.mock import patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.main import app
from app.schemas import OutlineRequest, ChapterDraftRequest, ContinuityReport


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_token():
    """Mock JWT token"""
    with patch("app.security.verify_token") as mock:
        mock.return_value = type('TokenData', (), {
            'user_id': 'test-user',
            'project_id': str(uuid4()),
            'role': 'author'
        })()
        yield mock


@pytest.mark.asyncio
async def test_health_endpoints(async_client: AsyncClient):
    """Test health check endpoints"""
    # Test healthz
    response = await async_client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    
    # Test livez
    response = await async_client.get("/livez")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_demo_token_generation(async_client: AsyncClient):
    """Test demo token generation"""
    response = await async_client.post("/auth/demo-token")
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


@pytest.mark.asyncio
async def test_outline_request_validation(async_client: AsyncClient, mock_token):
    """Test outline generation request validation"""
    project_id = str(uuid4())
    
    # Test missing brief
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/outline/stream",
        json={},
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 422
    
    # Test brief too short
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/outline/stream",
        json={"brief": "short"},
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 422
    
    # Test invalid target_chapters
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/outline/stream",
        json={
            "brief": "A valid book brief that is long enough",
            "target_chapters": 100
        },
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_outline_stream_contract(async_client: AsyncClient, mock_token):
    """Test outline streaming endpoint contract"""
    project_id = str(uuid4())
    
    with patch("app.routers.outline.BookWritingAgents") as mock_agents:
        # Mock the agents
        mock_agent_instance = AsyncMock()
        mock_agent_instance.generate_concepts = AsyncMock(return_value={"concepts": "test"})
        mock_agents.return_value = mock_agent_instance
        
        with patch("app.routers.outline.acompletion") as mock_completion:
            # Mock LLM response
            async def mock_stream():
                yield {"choices": [{"delta": {"content": "Test"}}]}
                yield {"choices": [{"delta": {"content": " outline"}}]}
                yield {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}
            
            mock_completion.return_value = mock_stream()
            
            # Make request
            response = await async_client.post(
                f"/api/v1/projects/{project_id}/outline/stream",
                json={
                    "brief": "A compelling story about AI and humanity",
                    "target_chapters": 10
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should return SSE response
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_cost_tracking(async_client: AsyncClient, mock_token):
    """Test that costs are tracked properly"""
    project_id = str(uuid4())
    
    with patch("app.routers.outline.Cost") as mock_cost:
        with patch("app.routers.outline.BookWritingAgents"):
            with patch("app.routers.outline.acompletion") as mock_completion:
                # Mock LLM with usage data
                async def mock_stream():
                    yield {"usage": {
                        "prompt_tokens": 1000,
                        "completion_tokens": 500
                    }}
                
                mock_completion.return_value = mock_stream()
                
                # Make request
                await async_client.post(
                    f"/api/v1/projects/{project_id}/outline/stream",
                    json={
                        "brief": "Test brief for cost tracking",
                        "target_chapters": 5
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Verify cost was tracked
                assert mock_cost.called


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting functionality"""
    from app.security import RateLimiter
    from app.cache import cache
    
    # Mock cache
    cache.redis = AsyncMock()
    cache.increment = AsyncMock(side_effect=[1, 2, 3, 61])  # 61st request
    
    limiter = RateLimiter(requests=60, window=60)
    
    # First 60 requests should pass
    for i in range(3):
        result = await limiter.check_rate_limit("test-key", cache)
        assert result is True
    
    # 61st request should fail
    result = await limiter.check_rate_limit("test-key", cache)
    assert result is False


def test_schemas_json_serializable():
    """Test that all schemas are JSON serializable"""
    # Test OutlineRequest
    outline_req = OutlineRequest(
        brief="Test brief",
        style_guide="Test style",
        genre="Fiction",
        target_chapters=10
    )
    json.dumps(outline_req.model_dump())
    
    # Test ChapterDraftRequest
    chapter_req = ChapterDraftRequest(
        outline="Test outline",
        chapter_number=1,
        style_guide="Test style"
    )
    json.dumps(chapter_req.model_dump())
    
    # Test ContinuityReport
    report = ContinuityReport(
        inconsistencies=[{"issue": "Name change"}],
        suggestions=["Fix name"],
        timeline_issues=[],
        character_issues=[],
        confidence_score=0.95
    )
    json.dumps(report.model_dump())