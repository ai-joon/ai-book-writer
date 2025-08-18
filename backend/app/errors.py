"""Utilities for standardized API errors."""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
from uuid import uuid4

from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Context variable to store request ID
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")


class ErrorCode(str, Enum):
    """Common API error codes."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    OUTLINE_INVALID_PARAMETER = "OUTLINE_INVALID_PARAMETER"
    OUTLINE_STREAM_INIT_FAILED = "OUTLINE_STREAM_INIT_FAILED"


class APIError(BaseModel):
    """Pydantic model for API error responses."""

    error_id: str
    error_code: str
    message: str
    hint: Optional[str] = None
    details: Optional[Dict[str, object]] = None
    request_id: str
    timestamp: str


def generate_error_id() -> str:
    """Generate a UUIDv4 error ID."""

    return str(uuid4())


def api_error(
    code: str,
    message: str,
    *,
    hint: str | None = None,
    details: Dict[str, object] | None = None,
    status: int = 400,
) -> JSONResponse:
    """Create a standardized API error response."""

    error = APIError(
        error_id=generate_error_id(),
        error_code=code,
        message=message,
        hint=hint,
        details=details,
        request_id=request_id_ctx_var.get(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return JSONResponse(status_code=status, content=error.model_dump())
