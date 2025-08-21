"""Usage and budget tracking endpoints"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Cost, Session, User
from ..pricing import estimate_book_cost
from ..security import TokenData, get_current_user

router = APIRouter(prefix="/users/me", tags=["usage"])


class UsageResponse(BaseModel):
    """User usage statistics"""

    total_usd: float
    month_usd: float
    monthly_budget_usd: float
    remaining_budget_usd: float
    by_agent: Dict[str, float]
    by_model: Dict[str, float]


class BudgetUpdateRequest(BaseModel):
    """Request to update monthly budget"""

    monthly_budget_usd: float


class EstimateRequest(BaseModel):
    """Request for cost estimation"""

    model: str = "gpt-5"
    target_chapters: int = 12
    avg_prompt_tokens: int = 2000
    avg_completion_tokens: int = 4000


class EstimateResponse(BaseModel):
    """Cost estimation response"""

    estimated_usd: float
    total_prompt_tokens: int
    total_completion_tokens: int
    breakdown: Dict[str, float]
    model: str
    chapters: int


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """Get current user's usage statistics"""

    # Convert user_id string to UUID
    from uuid import UUID

    try:
        user_uuid = UUID(current_user.user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Get user record
    user_result = await db.execute(select(User).where(User.id == user_uuid))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get total usage
    total_result = await db.execute(
        select(func.sum(Cost.usd))
        .join(Session, Cost.session_id == Session.id)
        .where(Session.user_id == user_uuid)
    )
    total_usd = float(total_result.scalar() or 0)

    # Get current month's usage
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_result = await db.execute(
        select(func.sum(Cost.usd))
        .join(Session, Cost.session_id == Session.id)
        .where(
            Session.user_id == user_uuid,
            Cost.created_at >= current_month,
        )
    )
    month_usd = float(month_result.scalar() or 0)

    # Get usage by agent
    agent_result = await db.execute(
        select(Cost.agent, func.sum(Cost.usd))
        .join(Session, Cost.session_id == Session.id)
        .where(Session.user_id == user_uuid)
        .group_by(Cost.agent)
    )
    by_agent = {row[0]: float(row[1]) for row in agent_result}

    # Get usage by model
    model_result = await db.execute(
        select(Cost.model, func.sum(Cost.usd))
        .join(Session, Cost.session_id == Session.id)
        .where(
            Session.user_id == user_uuid,
            Cost.model.isnot(None),
        )
        .group_by(Cost.model)
    )
    by_model = {row[0]: float(row[1]) for row in model_result}

    # Calculate remaining budget
    monthly_budget = float(user.monthly_budget_usd)
    remaining_budget = max(0, monthly_budget - month_usd)

    return UsageResponse(
        total_usd=total_usd,
        month_usd=month_usd,
        monthly_budget_usd=monthly_budget,
        remaining_budget_usd=remaining_budget,
        by_agent=by_agent,
        by_model=by_model,
    )


@router.post("/budget")
async def update_budget(
    request: BudgetUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, float]:
    """Update user's monthly budget"""

    # Validate budget
    if request.monthly_budget_usd < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget must be non-negative",
        )

    if request.monthly_budget_usd > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget cannot exceed $10,000",
        )

    # Convert user_id string to UUID
    from uuid import UUID

    try:
        user_uuid = UUID(current_user.user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Get user record
    user_result = await db.execute(select(User).where(User.id == user_uuid))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update budget
    user.monthly_budget_usd = request.monthly_budget_usd  # type: ignore[assignment]
    await db.commit()

    return {"monthly_budget_usd": float(user.monthly_budget_usd)}


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_cost(
    request: EstimateRequest,
    current_user: TokenData = Depends(get_current_user),
) -> EstimateResponse:
    """Estimate cost for generating a book"""

    # Get estimate
    estimate = estimate_book_cost(
        model=request.model,
        target_chapters=request.target_chapters,
        avg_prompt_tokens_per_chapter=request.avg_prompt_tokens,
        avg_completion_tokens_per_chapter=request.avg_completion_tokens,
    )

    return EstimateResponse(
        estimated_usd=estimate["estimated_usd"],  # type: ignore[arg-type]
        total_prompt_tokens=estimate["total_prompt_tokens"],  # type: ignore[arg-type]
        total_completion_tokens=estimate["total_completion_tokens"],  # type: ignore[arg-type]
        breakdown=estimate["breakdown"],  # type: ignore[arg-type]
        model=estimate["model"],  # type: ignore[arg-type]
        chapters=estimate["chapters"],  # type: ignore[arg-type]
    )
