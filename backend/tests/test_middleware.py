"""Tests for middleware request ID handling."""

import re
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware import RequestIDMiddleware


@pytest.fixture
def app_with_middleware():
    """Create test app with RequestIDMiddleware."""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"request_id": getattr(request.state, "request_id", None)}

    return app


@pytest.fixture
def client(app_with_middleware):
    """Create test client with middleware."""
    return TestClient(app_with_middleware)


def test_middleware_preserves_existing_request_id(client):
    """Middleware should preserve existing X-Request-ID headers."""
    existing_id = "user-provided-123"
    response = client.get("/test", headers={"X-Request-ID": existing_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == existing_id
    assert response.json()["request_id"] == existing_id


def test_middleware_generates_request_id(client):
    """Middleware should generate request ID when none provided."""
    response = client.get("/test")

    assert response.status_code == 200

    # Should generate a req-{uuid} format ID
    request_id = response.headers["X-Request-ID"]
    assert re.match(
        r"req-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", request_id
    )
    assert response.json()["request_id"] == request_id


def test_middleware_sets_response_header(client):
    """Middleware should set X-Request-ID header on all responses."""
    response = client.get("/test")

    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None
    assert len(response.headers["X-Request-ID"]) > 0


@patch("app.middleware.logger")
def test_middleware_logs_request_start(mock_logger, client):
    """Middleware should log request start with correlation info."""
    client.get("/test", headers={"X-Request-ID": "test-123"})

    # Should log request start
    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args
    assert "request start" in call_args[0]

    # Check extra fields
    extra = call_args[1]["extra"]
    assert extra["request_id"] == "test-123"
    assert extra["path"] == "/test"
    assert extra["method"] == "GET"


def test_middleware_handles_context_var_isolation():
    """Request ID context should be isolated between requests."""
    from app.errors import request_id_ctx_var

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    # Track context values across requests
    context_values = []

    @app.get("/test")
    async def test_endpoint():
        context_values.append(request_id_ctx_var.get())
        return {"ok": True}

    client = TestClient(app)

    # Make concurrent requests with different IDs
    client.get("/test", headers={"X-Request-ID": "request-1"})
    client.get("/test", headers={"X-Request-ID": "request-2"})

    # Context should be properly isolated
    assert len(context_values) == 2
    assert context_values[0] == "request-1"
    assert context_values[1] == "request-2"
