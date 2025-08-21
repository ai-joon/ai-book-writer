"""Simplified unit tests for OAuth implementation."""

import base64
import hashlib
from unittest.mock import patch

from fastapi import Request, Response

from app.oauth import clear_auth_cookies, generate_pkce_challenge, generate_state, set_auth_cookies


class TestOAuthCore:
    """Test core OAuth functionality."""

    def test_generate_state(self):
        """Test state generation for CSRF protection."""
        state = generate_state()

        # Should be a random string
        assert isinstance(state, str)
        assert len(state) > 20

        # Should be unique
        state2 = generate_state()
        assert state != state2

    def test_generate_pkce_challenge(self):
        """Test PKCE challenge generation."""
        verifier, challenge = generate_pkce_challenge()

        # Verify verifier format
        assert isinstance(verifier, str)
        assert 43 <= len(verifier) <= 128

        # Verify challenge is base64url encoded SHA256
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        assert challenge == expected

    def test_set_auth_cookies_localhost(self):
        """Test cookie setting for localhost."""
        response = Response()
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 3000),
        }
        request = Request(scope)

        set_auth_cookies(response, "access_token", "refresh_token", request)

        cookies = response.headers.getlist("set-cookie")
        assert len(cookies) == 2

        # Check no domain is set for localhost
        for cookie in cookies:
            assert "Domain=" not in cookie

    def test_set_auth_cookies_production(self):
        """Test cookie setting for production domain."""
        response = Response()
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [(b"x-forwarded-host", b"app.sopher.ai"), (b"x-forwarded-proto", b"https")],
            "server": ("backend", 8000),
        }
        request = Request(scope)

        with patch.dict("os.environ", {"ENV": "production"}):
            set_auth_cookies(response, "access_token", "refresh_token", request)

        cookies = response.headers.getlist("set-cookie")

        # Check domain is set correctly
        for cookie in cookies:
            if "access_token" in cookie or "refresh_token" in cookie:
                assert "Domain=sopher.ai" in cookie
                assert "Secure" in cookie

    def test_clear_auth_cookies(self):
        """Test cookie clearing."""
        response = Response()
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 3000),
        }
        request = Request(scope)

        clear_auth_cookies(response, request)

        cookies = response.headers.getlist("set-cookie")
        assert len(cookies) == 2

        # Check cookies are cleared (max_age=0)
        for cookie in cookies:
            assert "Max-Age=0" in cookie or "max-age=0" in cookie
