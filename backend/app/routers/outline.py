"""Outline generation endpoint with SSE streaming"""

import hashlib
import json
import time
from typing import AsyncIterator, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from litellm import acompletion
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ..agents.agents import BookWritingAgents
from ..cache import cache
from ..db import get_db
from ..metrics import MetricsTracker, active_sessions
from ..models import Artifact, Cost, Event, Session
from ..schemas import OutlineRequest
from ..security import TokenData, get_current_user

router = APIRouter(prefix="/projects/{project_id}", tags=["outline"])


async def event_generator(
    request: Request,
    project_id: UUID,
    outline_request: OutlineRequest,
    session: Session,
    db: AsyncSession,
    user: TokenData,
) -> AsyncIterator[dict]:
    """Generate SSE events for outline streaming"""

    active_sessions.inc()
    start_time = time.perf_counter()
    tokens_emitted = 0
    model = outline_request.model

    try:
        # Check cache
        cache_key = cache.cache_key(
            "outline",
            str(project_id),
            outline_request.model,
            hashlib.md5(outline_request.brief.encode()).hexdigest(),
        )

        cached_result = await cache.get(cache_key)
        if cached_result:
            MetricsTracker.track_cache(hit=True, cache_type="outline")
            yield {
                "event": "checkpoint",
                "data": json.dumps({"source": "cache", "content": cached_result}),
            }
            yield {"event": "complete", "data": json.dumps({"cached": True, "tokens": 0})}
            return

        MetricsTracker.track_cache(hit=False, cache_type="outline")

        # Create outline generation prompt
        agents = BookWritingAgents(model=model)

        # First, generate concepts
        yield {
            "event": "checkpoint",
            "data": json.dumps({"stage": "generating_concepts", "progress": 0.1}),
        }

        concepts = await agents.generate_concepts(brief=outline_request.brief, plot_seeds=None)

        yield {
            "event": "checkpoint",
            "data": json.dumps({"stage": "concepts_complete", "progress": 0.3}),
        }

        # Stream outline generation
        with MetricsTracker.track_inference(model, "outliner", "outline_generation"):

            prompt = f"""Create a detailed {outline_request.target_chapters}-chapter book outline.

Brief: {outline_request.brief}

Style Guide: {outline_request.style_guide or 'Standard narrative structure'}

Genre: {outline_request.genre or 'General fiction'}

Concepts: {json.dumps(concepts)}

Provide a comprehensive outline with:
1. Book title and subtitle
2. Target audience and themes
3. Chapter-by-chapter breakdown including:
   - Chapter number and title
   - Key events and plot points
   - Character development
   - Scene settings
   - Emotional beats
   - Cliffhangers/hooks
   - Estimated word count (3000-5000 per chapter)

Format as structured markdown."""

            # Stream tokens from LLM
            stream = await acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                max_tokens=4096,
                temperature=0.7,
            )

            buffer = []
            checkpoint_counter = 0

            async for chunk in stream:
                if await request.is_disconnected():
                    break

                choice = chunk.get("choices", [{}])[0]
                delta = choice.get("delta", {})
                content = delta.get("content", "")

                if content:
                    tokens_emitted += 1
                    buffer.append(content)

                    # Send token event
                    yield {"event": "token", "data": content}

                    # Send checkpoint every 100 tokens
                    if tokens_emitted % 100 == 0:
                        checkpoint_counter += 1
                        progress = min(0.3 + (tokens_emitted / 4000) * 0.6, 0.9)
                        yield {
                            "event": "checkpoint",
                            "data": json.dumps(
                                {
                                    "checkpoint": checkpoint_counter,
                                    "tokens": tokens_emitted,
                                    "progress": progress,
                                    "preview": "".join(buffer[-500:]),
                                }
                            ),
                        }

                # Get usage info if available
                if chunk.get("usage"):
                    usage = chunk["usage"]
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)

                    # Track metrics
                    MetricsTracker.track_tokens(
                        model=model,
                        agent="outliner",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    )

                    # Calculate cost (example rates)
                    cost_per_1k_prompt = 0.003
                    cost_per_1k_completion = 0.015
                    total_cost = (prompt_tokens / 1000) * cost_per_1k_prompt + (
                        completion_tokens / 1000
                    ) * cost_per_1k_completion

                    MetricsTracker.track_cost(model, "outliner", total_cost)

                    # Save cost to database
                    cost_record = Cost(
                        session_id=session.id,
                        agent="outliner",
                        model=model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        usd=total_cost,
                    )
                    db.add(cost_record)

        # Final outline
        final_outline = "".join(buffer)

        # Save to cache
        await cache.set(cache_key, final_outline, ttl=3600)

        # Save artifact to database
        artifact = Artifact(
            session_id=session.id,
            kind="outline",
            meta={
                "brief": outline_request.brief,
                "chapters": outline_request.target_chapters,
                "tokens": tokens_emitted,
            },
            blob=final_outline.encode(),
        )
        db.add(artifact)

        # Log event
        event = Event(
            session_id=session.id,
            type="outline_generated",
            payload={
                "tokens": tokens_emitted,
                "duration": time.perf_counter() - start_time,
                "model": model,
            },
        )
        db.add(event)

        await db.commit()

        # Send completion event
        yield {
            "event": "complete",
            "data": json.dumps(
                {
                    "tokens": tokens_emitted,
                    "duration": time.perf_counter() - start_time,
                    "outline_id": str(artifact.id),
                }
            ),
        }

    except Exception as e:
        MetricsTracker.track_model_error(model, type(e).__name__)
        yield {"event": "error", "data": json.dumps({"error": str(e)})}
    finally:
        active_sessions.dec()


@router.get("/outline/stream")
async def stream_outline(
    project_id: UUID,
    request: Request,
    brief: str,
    style_guide: Optional[str] = None,
    genre: Optional[str] = None,
    target_chapters: int = 10,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> EventSourceResponse:
    """Stream outline generation via Server-Sent Events"""

    # Validate brief length
    if len(brief) < 10 or len(brief) > 10000:
        raise HTTPException(status_code=422, detail="Brief must be between 10 and 10000 characters")

    # Validate target_chapters
    if target_chapters < 1 or target_chapters > 50:
        raise HTTPException(status_code=422, detail="Target chapters must be between 1 and 50")

    # Create outline request from query parameters
    outline_request = OutlineRequest(
        brief=brief,
        style_guide=style_guide,
        genre=genre,
        target_chapters=target_chapters,
    )

    # Create session
    session = Session(
        project_id=project_id,
        user_id=user.user_id,
        context={
            "brief": outline_request.brief,
            "style_guide": outline_request.style_guide,
            "genre": outline_request.genre,
            "target_chapters": outline_request.target_chapters,
            "model": outline_request.model,
        },
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Track API request
    MetricsTracker.track_api_request("POST", "/outline/stream", 200)

    return EventSourceResponse(
        event_generator(
            request=request,
            project_id=project_id,
            outline_request=outline_request,
            session=session,
            db=db,
            user=user,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )
