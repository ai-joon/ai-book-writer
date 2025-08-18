"""Middleware utilities for request handling."""

from __future__ import annotations

import logging
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from .errors import request_id_ctx_var

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to attach a request ID to each request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID", f"req-{uuid4()}")
        request.state.request_id = request_id
        request_id_ctx_var.set(request_id)
        logger.info(
            "request start",
            extra={"request_id": request_id, "path": request.url.path, "method": request.method},
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
