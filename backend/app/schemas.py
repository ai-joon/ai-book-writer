"""Pydantic schemas for API request/response"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Create a new project"""

    name: str = Field(..., min_length=1, max_length=200)
    settings: Dict[str, Any] = Field(default_factory=dict)


class ProjectResponse(BaseModel):
    """Project response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None


class SessionCreate(BaseModel):
    """Create a new session"""

    project_id: UUID
    context: Dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """Session response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: str
    context: Dict[str, Any]
    created_at: datetime


class OutlineRequest(BaseModel):
    """Request to generate an outline"""

    brief: str = Field(..., min_length=10, max_length=10000)
    style_guide: Optional[str] = Field(None, max_length=5000)
    genre: Optional[str] = Field(None, max_length=50)
    target_chapters: int = Field(default=10, ge=1, le=50)
    model: Literal["gpt-5", "claude-sonnet-4.0", "gemini-2.5-pro"] = "gpt-5"


class ChapterDraftRequest(BaseModel):
    """Request to draft a chapter"""

    outline: str = Field(..., min_length=10)
    chapter_number: int = Field(..., ge=1)
    style_guide: Optional[str] = None
    character_bible: Optional[Dict[str, Any]] = None
    previous_chapters: Optional[List[str]] = None


class EditRequest(BaseModel):
    """Request to edit content"""

    content: str = Field(..., min_length=10)
    edit_type: Literal["structural", "line", "copy", "proof"] = "structural"
    instructions: Optional[str] = None


class ContinuityCheckRequest(BaseModel):
    """Request continuity check"""

    chapters: List[str] = Field(..., min_length=1)
    character_bible: Optional[Dict[str, Any]] = None
    timeline: Optional[List[Dict[str, Any]]] = None


class ContinuityReport(BaseModel):
    """Continuity check report"""

    inconsistencies: List[Dict[str, Any]]
    suggestions: List[str]
    timeline_issues: List[Dict[str, Any]]
    character_issues: List[Dict[str, Any]]
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class CostReport(BaseModel):
    """Cost report for a session or project"""

    total_usd: float
    total_tokens: int
    by_agent: Dict[str, Dict[str, Any]]
    by_model: Dict[str, Dict[str, Any]]
    period_start: datetime
    period_end: datetime


class TokenStreamEvent(BaseModel):
    """SSE event for token streaming"""

    event: Literal["token", "checkpoint", "error", "complete"]
    data: str
    metadata: Optional[Dict[str, Any]] = None


class AgentStatus(BaseModel):
    """WebSocket message for agent status"""

    agent: str
    status: Literal["idle", "thinking", "writing", "reviewing", "complete", "error"]
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    message: Optional[str] = None
    tokens_used: Optional[int] = None
