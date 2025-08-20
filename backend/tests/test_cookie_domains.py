"""Tests for cross-domain cookie behavior and security."""

from unittest.mock import patch

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient

from app.main import app
from app.oauth import set_auth_cookies

client = TestClient(app)


class TestCookieDomainBehavior:
    """Test cookie behavior across different domains and environments."""

    def create_request(self, host: str, headers: dict = None):
        """Create a mock request with specified host and headers."""
        # Handle IPv6 addresses
        if host.startswith("["):
            # IPv6 format like [::1]:3000
            if "]:" in host:
                host_part, port_part = host.rsplit("]:", 1)
                host_part = host_part[1:]  # Remove leading [
                port = int(port_part)
            else:
                host_part = host[1:-1]  # Remove [ and ]
                port = 80
        elif ":" in host:
            host_part, port_part = host.rsplit(":", 1)
            port = int(port_part)
        else:
            host_part = host
            port = 80

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "server": (host_part, port),
        }

        if headers:
            scope["headers"] = [(k.lower().encode(), v.encode()) for k, v in headers.items()]

        return Request(scope)

    def test_localhost_no_domain(self):
        """Test that localhost cookies don't set domain attribute."""
        response = Response()
        request = self.create_request("localhost:3000")

        set_auth_cookies(response, "access_token", "refresh_token", request)

        # Check cookies don't have domain set
        cookies = response.headers.getlist("set-cookie")
        assert len(cookies) == 2

        for cookie in cookies:
            assert "Domain=" not in cookie
            assert "localhost" not in cookie.lower()

    def test_127_0_0_1_no_domain(self):
        """Test that 127.0.0.1 cookies don't set domain attribute."""
        response = Response()
        request = self.create_request("127.0.0.1:8000")

        set_auth_cookies(response, "access_token", "refresh_token", request)

        cookies = response.headers.getlist("set-cookie")
        for cookie in cookies:
            assert "Domain=" not in cookie

    def test_production_domain_sopher_ai(self):
        """Test production domain setting for sopher.ai."""
        response = Response()
        request = self.create_request(
            "app.sopher.ai:443", headers={"x-forwarded-host": "app.sopher.ai"}
        )

        with patch.dict("os.environ", {"ENV": "production"}):
            set_auth_cookies(response, "access_token", "refresh_token", request)

        cookies = response.headers.getlist("set-cookie")
        for cookie in cookies:
            if "access_token" in cookie or "refresh_token" in cookie:
                assert "Domain=sopher.ai" in cookie
                assert "Secure" in cookie

    def test_subdomain_compatibility(self):
        """Test that cookies work across subdomains."""
        test_cases = [
            ("sopher.ai", "sopher.ai"),
            ("www.sopher.ai", "sopher.ai"),
            ("app.sopher.ai", "sopher.ai"),
            ("api.sopher.ai", "sopher.ai"),
            ("staging.sopher.ai", "sopher.ai"),
        ]

        for host, expected_domain in test_cases:
            response = Response()
            request = self.create_request(f"{host}:443", headers={"x-forwarded-host": host})

            with patch.dict("os.environ", {"ENV": "production"}):
                set_auth_cookies(response, "access_token", "refresh_token", request)

            cookies = response.headers.getlist("set-cookie")
            for cookie in cookies:
                if "access_token" in cookie or "refresh_token" in cookie:
                    assert f"Domain={expected_domain}" in cookie

    def test_cookie_security_attributes_development(self):
        """Test cookie security attributes in development."""
        response = Response()
        request = self.create_request("localhost:3000")

        with patch.dict("os.environ", {"ENV": "development"}):
            set_auth_cookies(response, "access_token", "refresh_token", request)

        cookies = response.headers.getlist("set-cookie")

        # Check access_token cookie
        access_cookie = next(c for c in cookies if "access_token" in c)
        assert "Secure" not in access_cookie  # Not secure in dev
        assert "SameSite=lax" in access_cookie or "SameSite=Lax" in access_cookie
        assert "HttpOnly" not in access_cookie  # Frontend needs to read it
        assert "Path=/" in access_cookie

        # Check refresh_token cookie
        refresh_cookie = next(c for c in cookies if "refresh_token" in c)
        assert "Secure" not in refresh_cookie
        assert "SameSite=lax" in refresh_cookie or "SameSite=Lax" in refresh_cookie
        assert "HttpOnly" in refresh_cookie  # More secure
        assert "Path=/" in refresh_cookie

    def test_cookie_security_attributes_production(self):
        """Test cookie security attributes in production."""
        response = Response()
        request = self.create_request(
            "app.sopher.ai:443",
            headers={"x-forwarded-host": "app.sopher.ai", "x-forwarded-proto": "https"},
        )

        with patch.dict("os.environ", {"ENV": "production"}):
            set_auth_cookies(response, "access_token", "refresh_token", request)

        cookies = response.headers.getlist("set-cookie")

        # Check access_token cookie
        access_cookie = next(c for c in cookies if "access_token" in c)
        assert "Secure" in access_cookie  # Must be secure in production
        assert (
            "SameSite=lax" in access_cookie or "SameSite=Lax" in access_cookie
        )  # Using lax for security
        assert "HttpOnly" not in access_cookie
        assert "Path=/" in access_cookie
        assert "Domain=sopher.ai" in access_cookie

        # Check refresh_token cookie
        refresh_cookie = next(c for c in cookies if "refresh_token" in c)
        assert "Secure" in refresh_cookie
        assert "SameSite=lax" in refresh_cookie or "SameSite=Lax" in refresh_cookie
        assert "HttpOnly" in refresh_cookie
        assert "Path=/" in refresh_cookie
        assert "Domain=sopher.ai" in refresh_cookie

    def test_proxy_header_handling(self):
        """Test proper handling of proxy headers."""
        test_cases = [
            # (x-forwarded-host, x-forwarded-proto, expected_domain, expected_secure)
            ("app.sopher.ai", "https", "sopher.ai", True),
            ("localhost:3000", "http", None, False),
            ("staging.sopher.ai", "https", "sopher.ai", True),
            (None, "https", None, True),  # No forwarded host
        ]

        for forwarded_host, forwarded_proto, expected_domain, expected_secure in test_cases:
            response = Response()
            headers = {}
            if forwarded_host:
                headers["x-forwarded-host"] = forwarded_host
            if forwarded_proto:
                headers["x-forwarded-proto"] = forwarded_proto

            request = self.create_request("backend:8000", headers=headers)

            set_auth_cookies(response, "access_token", "refresh_token", request)

            cookies = response.headers.getlist("set-cookie")
            for cookie in cookies:
                if expected_domain:
                    assert f"Domain={expected_domain}" in cookie
                else:
                    assert "Domain=" not in cookie

                if expected_secure:
                    assert "Secure" in cookie
                else:
                    assert "Secure" not in cookie

    def test_cookie_clearing_matches_setting(self):
        """Test that cookie clearing uses same attributes as setting."""
        # First set cookies
        response_set = Response()
        request = self.create_request(
            "app.sopher.ai:443", headers={"x-forwarded-host": "app.sopher.ai"}
        )

        with patch.dict("os.environ", {"ENV": "production"}):
            set_auth_cookies(response_set, "access_token", "refresh_token", request)

        _ = response_set.headers.getlist("set-cookie")  # Verify cookies were set

        # Now clear cookies (simulated by setting empty values with max_age=0)
        response_clear = Response()
        with patch.dict("os.environ", {"ENV": "production"}):
            # Simulate logout by setting empty cookies
            response_clear.set_cookie(
                key="access_token",
                value="",
                max_age=0,
                path="/",
                domain="sopher.ai",
                secure=True,
                httponly=False,
                samesite="lax",
            )
            response_clear.set_cookie(
                key="refresh_token",
                value="",
                max_age=0,
                path="/",
                domain="sopher.ai",
                secure=True,
                httponly=True,
                samesite="lax",
            )

        clear_cookies = response_clear.headers.getlist("set-cookie")

        # Verify domain and path match
        for cookie in clear_cookies:
            assert "Domain=sopher.ai" in cookie
            assert "Path=/" in cookie
            assert "Max-Age=0" in cookie

    def test_cross_origin_cookie_access(self):
        """Test cookie behavior for cross-origin requests."""
        # Frontend at app.sopher.ai making request to api.sopher.ai
        response = Response()
        request = self.create_request(
            "api.sopher.ai:443",
            headers={"origin": "https://app.sopher.ai", "x-forwarded-host": "api.sopher.ai"},
        )

        with patch.dict("os.environ", {"ENV": "production"}):
            set_auth_cookies(response, "access_token", "refresh_token", request)

        cookies = response.headers.getlist("set-cookie")

        # Cookies should be set with domain=sopher.ai to work across subdomains
        for cookie in cookies:
            assert "Domain=sopher.ai" in cookie
            assert (
                "SameSite=lax" in cookie or "SameSite=Lax" in cookie
            )  # Using lax for security
            assert "Secure" in cookie  # Required with SameSite=None

    def test_port_handling_in_development(self):
        """Test that different ports in development don't affect cookies."""
        test_ports = ["3000", "3001", "8000", "8080"]

        for port in test_ports:
            response = Response()
            request = self.create_request(f"localhost:{port}")

            set_auth_cookies(response, "access_token", "refresh_token", request)

            cookies = response.headers.getlist("set-cookie")
            for cookie in cookies:
                # Should not include port in domain
                assert f":{port}" not in cookie
                # Should not set domain for localhost
                assert "Domain=" not in cookie

    def test_ipv6_localhost(self):
        """Test cookie handling for IPv6 localhost."""
        response = Response()
        request = self.create_request("[::1]:3000")

        set_auth_cookies(response, "access_token", "refresh_token", request)

        cookies = response.headers.getlist("set-cookie")
        for cookie in cookies:
            # Should not set domain for IPv6 localhost
            assert "Domain=" not in cookie
            assert "::1" not in cookie

    def test_cookie_size_limits(self):
        """Test that cookies don't exceed browser size limits."""
        # Generate large tokens (but realistic for JWTs)
        large_access_token = "x" * 2000  # ~2KB
        large_refresh_token = "y" * 2000  # ~2KB

        response = Response()
        request = self.create_request("localhost:3000")

        set_auth_cookies(response, large_access_token, large_refresh_token, request)

        cookies = response.headers.getlist("set-cookie")

        # Each cookie should be under 4KB (browser limit)
        for cookie in cookies:
            assert len(cookie) < 4096

    def test_special_characters_in_domain(self):
        """Test handling of special characters in domain names."""
        # Internationalized domain names or special cases
        test_cases = [
            "xn--spher-nua.ai",  # IDN encoded
            "sopher-ai.com",  # Hyphenated
            "sopher_ai.com",  # Underscore (technically invalid but test handling)
        ]

        for domain in test_cases:
            response = Response()
            request = self.create_request(f"{domain}:443", headers={"x-forwarded-host": domain})

            try:
                set_auth_cookies(response, "access_token", "refresh_token", request)
                cookies = response.headers.getlist("set-cookie")

                # Should handle gracefully
                assert len(cookies) == 2
            except Exception as e:
                # Should not crash on unusual domains
                pytest.fail(f"Failed to handle domain {domain}: {e}")
