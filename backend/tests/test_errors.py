"""Tests for standardized API error utilities."""

import json
from datetime import datetime
from unittest.mock import patch
from uuid import UUID

from fastapi.responses import JSONResponse

from app.errors import ErrorCode, api_error, generate_error_id, request_id_ctx_var


def test_generate_error_id_produces_uuid4():
    """generate_error_id should return a valid UUID4 string."""
    eid = generate_error_id()
    uuid_obj = UUID(eid, version=4)
    assert str(uuid_obj) == eid


def test_api_error_builds_response_with_context():
    """api_error should include request context and structured fields."""
    request_id_ctx_var.set("req-test-123")
    fixed_id = "00000000-0000-4000-8000-000000000000"
    with patch("app.errors.generate_error_id", return_value=fixed_id):
        response = api_error(
            ErrorCode.NOT_FOUND,
            "Resource missing",
            hint="Verify resource identifier",
            details={"item": "value"},
            status=404,
        )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    payload = json.loads(response.body)
    assert payload["error_id"] == fixed_id
    assert payload["error_code"] == ErrorCode.NOT_FOUND
    assert payload["message"] == "Resource missing"
    assert payload["hint"] == "Verify resource identifier"
    assert payload["details"] == {"item": "value"}
    assert payload["request_id"] == "req-test-123"
    # timestamp is ISO8601
    datetime.fromisoformat(payload["timestamp"])
