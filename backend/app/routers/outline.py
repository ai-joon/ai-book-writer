"""Outline generation endpoint with SSE streaming"""

import hashlib
import json
import logging
import time
from datetime import datetime
from typing import AsyncIterator, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from litellm import acompletion
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ..agents.agents import BookWritingAgents
from ..cache import cache
from ..db import get_db
from ..errors import ErrorCode, api_error
from ..metrics import MetricsTracker, active_sessions
from ..models import Artifact, Cost, Event, Session, User
from ..pricing import calculate_cost_usd
from ..schemas import OutlineRequest
from ..security import TokenData, get_current_user

router = APIRouter(prefix="/projects/{project_id}", tags=["outline"])

logger = logging.getLogger(__name__)


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

                    # Calculate cost using pricing module
                    total_cost = calculate_cost_usd(model, prompt_tokens, completion_tokens)

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
        err_response = api_error(
            ErrorCode.OUTLINE_STREAM_INIT_FAILED.value,
            "Could not start the outline stream.",
            hint="Retry in a few seconds. If it persists, check service readiness or credentials.",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        body_bytes = bytes(err_response.body)
        body = body_bytes.decode()
        data = json.loads(body)
        logger.error(
            f"outline stream failed: {e}",
            extra={
                "error_id": data["error_id"],
                "request_id": data["request_id"],
                "error_code": data["error_code"],
                "path": request.url.path,
                "method": request.method,
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )
        yield {"event": "error", "data": body}
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
) -> Response:
    """Stream outline generation via Server-Sent Events"""

    # Check user's budget before starting
    user_result = await db.execute(select(User).where(User.id == user.user_id))
    user_record = user_result.scalar_one_or_none()

    if not user_record:
        return api_error(
            ErrorCode.OUTLINE_STREAM_INIT_FAILED.value,
            "User not found.",
            status=status.HTTP_404_NOT_FOUND,
        )

    # Get current month's usage
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_usage_result = await db.execute(
        select(func.sum(Cost.usd))
        .join(Session, Cost.session_id == Session.id)
        .where(
            Session.user_id == user.user_id,
            Cost.created_at >= current_month,
        )
    )
    month_usage = month_usage_result.scalar() or 0

    # Check if budget exceeded
    if month_usage >= user_record.monthly_budget_usd:
        return api_error(
            "BUDGET_EXCEEDED",
            f"Monthly budget of ${user_record.monthly_budget_usd} exceeded.",
            hint="Please increase your budget or wait for the next billing cycle.",
            details={
                "current_usage": float(month_usage),
                "budget": float(user_record.monthly_budget_usd),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # Validate brief length
    if len(brief) < 10 or len(brief) > 10000:
        MetricsTracker.track_api_request(request.method, request.url.path, 422)
        response = api_error(
            ErrorCode.OUTLINE_INVALID_PARAMETER.value,
            "Brief must be between 10 and 10000 characters.",
            hint="Ensure 'brief' is 10-10000 characters.",
            details={"field": "brief"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        data = json.loads(response.body)
        logger.error(
            "invalid parameter",
            extra={
                "error_id": data["error_id"],
                "request_id": data["request_id"],
                "error_code": data["error_code"],
                "path": request.url.path,
                "method": request.method,
                "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
            },
        )
        return response

    # Validate target_chapters
    if target_chapters < 1 or target_chapters > 50:
        MetricsTracker.track_api_request(request.method, request.url.path, 422)
        response = api_error(
            ErrorCode.OUTLINE_INVALID_PARAMETER.value,
            "Target chapters must be between 1 and 50.",
            hint="Provide a value between 1 and 50.",
            details={"field": "target_chapters"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        data = json.loads(response.body)
        logger.error(
            "invalid parameter",
            extra={
                "error_id": data["error_id"],
                "request_id": data["request_id"],
                "error_code": data["error_code"],
                "path": request.url.path,
                "method": request.method,
                "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
            },
        )
        return response

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
    MetricsTracker.track_api_request(request.method, request.url.path, 200)

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
