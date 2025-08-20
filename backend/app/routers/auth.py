"""Authentication routes for OAuth2 login"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..oauth import (
    clear_auth_cookies,
    exchange_code_for_token,
    generate_pkce_challenge,
    generate_state,
    get_google_auth_url,
    set_auth_cookies,
    store_oauth_state,
    validate_oauth_state,
)
from ..security import TokenData, create_access_token, create_refresh_token, get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_frontend_url(request: Request) -> str:
    """Extract and validate frontend URL from request headers.

    This function implements strict URL validation to prevent open redirects.
    Only whitelisted domains are allowed.
    """
    host = request.headers.get("host", "")

    # Don't log full URLs to prevent information disclosure
    logger.info(f"Determining frontend URL - host_present: {bool(host)}")

    # Define allowed hosts to prevent SSRF attacks
    allowed_hosts = {
        "localhost:3000",
        "localhost:3001",
        "127.0.0.1:3000",
        "sopher.ai",
        "api.sopher.ai",
        "www.sopher.ai",
    }

    # Validate and determine the frontend URL
    if host:
        # Extract hostname without port for validation
        hostname = host.split(":")[0] if ":" in host else host

        # Check if it's a localhost development environment
        if hostname in ["localhost", "127.0.0.1"]:
            # For localhost, preserve the port from the host header
            if ":" in host:
                port = host.split(":")[1]
                # Validate port is numeric and within valid range (1-65535)
                try:
                    port_num = int(port)
                    if 1 <= port_num <= 65535:
                        # nosemgrep: directly-returned-format-string
                        return f"http://localhost:{port}/"
                    else:
                        # Invalid port range, use default
                        return "http://localhost:3000/"
                except ValueError:
                    # Non-numeric port, use default
                    return "http://localhost:3000/"
            else:
                return "http://localhost:3000/"

        # Check if it's an allowed production host
        elif host in allowed_hosts or hostname in ["sopher.ai", "api.sopher.ai"]:
            # Always redirect to main domain for production
            return "https://sopher.ai/"
        else:
            # Unrecognized host - use safe default
            # Log without exposing the actual host value
            logger.warning("Unrecognized host header detected, using default")
            return "https://sopher.ai/"
    else:
        # No host header - use production URL as fallback
        return "https://sopher.ai/"


@router.get("/config/status")
async def oauth_config_status():
    """Check OAuth configuration status (for debugging)"""
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

    return {
        "google_oauth_configured": bool(google_client_id and google_client_secret),
        "client_id_set": bool(google_client_id),
        "client_secret_set": bool(google_client_secret),
        "redirect_uri": os.getenv(
            "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3000/api/backend/auth/callback/google"
        ),
        "message": (
            "OAuth is properly configured"
            if google_client_id and google_client_secret
            else "OAuth credentials are missing. See docs for setup instructions."
        ),
    }


@router.get("/login/google")
async def login_google():
    """Initiate Google OAuth2 login flow"""
    state = generate_state()
    verifier, challenge = generate_pkce_challenge()

    # Store state and verifier for validation
    await store_oauth_state(state, verifier)

    # Generate authorization URL
    auth_url = get_google_auth_url(state, challenge)

    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback/google")
@router.head("/callback/google")  # Support HEAD requests for health checks
async def callback_google(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth2 callback"""
    # Handle HEAD requests (return empty response)
    if request.method == "HEAD":
        return Response(status_code=status.HTTP_200_OK)

    # Log all callback parameters for debugging
    # Sanitize user-provided inputs to prevent log injection
    sanitized_error = (
        error.replace("\r", "").replace("\n", "").replace("\t", "") if error else error
    )
    sanitized_error_desc = (
        error_description.replace("\r", "").replace("\n", "").replace("\t", "")
        if error_description
        else error_description
    )
    logger.info(
        f"OAuth callback - code_present: {bool(code)}, "
        f"state_present: {bool(state)}, error: {sanitized_error}"
    )

    # Handle OAuth errors from Google
    if error:
        logger.error(f"OAuth error from Google: {sanitized_error} - {sanitized_error_desc}")
        # Redirect to frontend with error
        frontend_url = _get_frontend_url(request)
        # URL encode the error to prevent injection
        from urllib.parse import quote

        error_param = quote(sanitized_error) if sanitized_error else ""
        error_url = f"{frontend_url}?oauth=error&error={error_param}"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

    # Validate required parameters
    if not code or not state:
        logger.error(f"Missing OAuth parameters - code: {bool(code)}, state: {bool(state)}")
        # Redirect to frontend with error instead of raising exception
        frontend_url = _get_frontend_url(request)
        error_url = f"{frontend_url}?oauth=error&error=missing_parameters"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

    # Validate state and get PKCE verifier
    try:
        verifier = await validate_oauth_state(state)
    except Exception as e:
        logger.error(f"Failed to validate OAuth state: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate OAuth state. Please try logging in again.",
        )

    if not verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    try:
        # Exchange code for tokens and get user info
        token, userinfo = await exchange_code_for_token(code, verifier)
    except HTTPException as http_e:
        # Re-raise HTTPExceptions (like missing credentials) as-is
        logger.error(f"OAuth HTTP error: {http_e.detail}")
        raise
    except Exception as e:
        logger.error(f"OAuth token exchange failed: {type(e).__name__}", exc_info=True)
        # Check if it's a configuration issue
        if "GOOGLE_CLIENT_ID" in str(e) or "GOOGLE_CLIENT_SECRET" in str(e):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not properly configured. Please contact the administrator.",
            )
        # Check for common OAuth errors
        error_msg = str(e).lower()
        if "invalid_grant" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The authorization code has expired or is invalid. Please try again.",
            )
        elif "redirect_uri_mismatch" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth redirect URI mismatch. Please contact the administrator.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to authenticate with Google: {str(e)}",
            )

    # Extract user information
    provider_sub = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")

    if not provider_sub or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete user information from Google",
        )

    # Find or create user
    result = await db.execute(select(User).where(User.provider_sub == provider_sub))
    user = result.scalar_one_or_none()

    if user:
        # Update existing user
        user.email = email
        user.name = name  # type: ignore[assignment]
        user.picture = picture  # type: ignore[assignment]
    else:
        # Create new user
        user = User(
            email=email,
            name=name,
            picture=picture,
            provider="google",
            provider_sub=provider_sub,
            role="author",
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    # Create our own JWT tokens
    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Log successful authentication with more details
    logger.info(f"User {user.email} authenticated successfully")
    logger.info(f"User details - ID: {user.id}, Role: {user.role}, Provider: {user.provider}")

    # Get frontend URL using helper function
    frontend_url = _get_frontend_url(request)
    frontend_url += "?oauth=success"

    # Create redirect response and set cookies on it
    redirect_response = RedirectResponse(url=frontend_url, status_code=status.HTTP_302_FOUND)
    set_auth_cookies(redirect_response, access_token, refresh_token, request)

    logger.info(f"OAuth flow complete - Setting cookies and redirecting to {frontend_url}")
    logger.info(
        f"Cookie details - Access token length: {len(access_token)}, "
        f"Refresh token length: {len(refresh_token)}"
    )

    # Add debug headers in development
    debug_mode = (
        os.getenv("ENVIRONMENT", "development") == "development"
        or os.getenv("DEBUG_AUTH") == "true"
    )
    if debug_mode:
        redirect_response.headers["X-Auth-Status"] = "success"
        redirect_response.headers["X-User-Email"] = str(user.email)

    return redirect_response


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Clear authentication cookies"""
    clear_auth_cookies(response, request)
    return {"message": "Logged out successfully"}


@router.get("/verify")
async def verify_auth(request: Request):
    """Verify authentication cookies are present"""
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    logger.info(
        f"Cookie verification - access: {bool(access_token)}, " f"refresh: {bool(refresh_token)}"
    )

    return {
        "authenticated": access_token is not None,
        "has_access_token": access_token is not None,
        "has_refresh_token": refresh_token is not None,
        "host": request.headers.get("host", ""),
        "cookies_present": list(request.cookies.keys()),
    }


@router.get("/me")
async def get_me(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile"""
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "role": user.role,
        "monthly_budget_usd": float(user.monthly_budget_usd),
    }
