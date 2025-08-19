"""OAuth2 authentication module for Google login"""

import hashlib
import os
import secrets
from base64 import urlsafe_b64encode
from typing import Optional
from urllib.parse import urlencode

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException, Request, Response, status

from .cache import cache

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback/google"
)

# Google OAuth2 endpoints
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# OAuth2 scopes
OAUTH_SCOPES = ["openid", "email", "profile"]


def generate_state() -> str:
    """Generate a secure random state for CSRF protection"""
    return secrets.token_urlsafe(32)


def generate_pkce_challenge() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge for OAuth2"""
    verifier = secrets.token_urlsafe(32)
    challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


async def store_oauth_state(state: str, verifier: str) -> None:
    """Store OAuth state and PKCE verifier in cache"""
    await cache.set(f"oauth:state:{state}", {"verifier": verifier}, ttl=600)  # 10 minutes


async def validate_oauth_state(state: str) -> Optional[str]:
    """Validate OAuth state and return PKCE verifier"""
    data = await cache.get(f"oauth:state:{state}")
    if data:
        await cache.delete(f"oauth:state:{state}")  # One-time use
        return str(data.get("verifier")) if data.get("verifier") else None
    return None


def get_google_oauth_client() -> AsyncOAuth2Client:
    """Create Google OAuth2 client"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth credentials not configured",
        )

    return AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
        scope=" ".join(OAUTH_SCOPES),
        authorize_url=GOOGLE_AUTHORIZE_URL,
        token_url=GOOGLE_TOKEN_URL,
    )


def get_google_auth_url(state: str, code_challenge: str) -> str:
    """Generate Google OAuth2 authorization URL with PKCE"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str, code_verifier: str) -> tuple[dict, dict]:
    """Exchange authorization code for tokens and fetch user info"""
    client = get_google_oauth_client()

    # Exchange code for token
    token = await client.fetch_token(
        GOOGLE_TOKEN_URL,
        code=code,
        code_verifier=code_verifier,
    )

    # Fetch user info
    client.token = token
    resp = await client.get(GOOGLE_USERINFO_URL)
    resp.raise_for_status()
    userinfo = resp.json()

    return token, userinfo


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    request: Request,
) -> None:
    """Set authentication cookies with appropriate security settings"""
    # Determine if we're in production
    is_production = request.url.hostname not in ["localhost", "127.0.0.1"]

    # Don't set domain - let browser handle it (works better with proxies)
    # This allows cookies to be accessible on the same domain as the request

    # Set access token cookie (1 hour)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=3600,
        httponly=True,
        samesite="lax",
        secure=is_production,
        path="/",
    )

    # Set refresh token cookie (7 days)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=7 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=is_production,
        path="/",
    )


def clear_auth_cookies(response: Response, request: Request) -> None:
    """Clear authentication cookies"""
    is_production = request.url.hostname not in ["localhost", "127.0.0.1"]

    # Don't set domain - match how cookies were set
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=is_production,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=is_production,
        httponly=True,
        samesite="lax",
    )
