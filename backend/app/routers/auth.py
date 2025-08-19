"""Authentication routes for OAuth2 login"""

import logging

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
async def callback_google(
    request: Request,
    response: Response,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth2 callback"""
    # Validate state and get PKCE verifier
    verifier = await validate_oauth_state(state)
    if not verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    try:
        # Exchange code for tokens and get user info
        token, userinfo = await exchange_code_for_token(code, verifier)
    except HTTPException:
        # Re-raise HTTPExceptions (like missing credentials) as-is
        raise
    except Exception as e:
        logger.error(f"OAuth token exchange failed: {e}")
        # Check if it's a configuration issue
        if "GOOGLE_CLIENT_ID" in str(e) or "GOOGLE_CLIENT_SECRET" in str(e):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not properly configured. Please contact the administrator.",
            )
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

    # Set cookies and redirect to frontend
    set_auth_cookies(response, access_token, refresh_token, request)

    # Redirect to frontend home page with proper host validation
    # When proxied through frontend, use the host header but validate it first
    host = request.headers.get("host", "")

    # Define allowed hosts to prevent SSRF attacks
    allowed_hosts = {
        "localhost:3000",
        "localhost:3001",
        "127.0.0.1:3000",
        "sopher.ai",
        "api.sopher.ai",
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
                # Validate port is numeric
                try:
                    int(port)
                    frontend_url = f"http://localhost:{port}/"
                except ValueError:
                    frontend_url = "http://localhost:3000/"
            else:
                frontend_url = "http://localhost:3000/"

        # Check if it's an allowed production host
        elif host in allowed_hosts or hostname in ["sopher.ai", "api.sopher.ai"]:
            # Always redirect to main domain for production
            frontend_url = "https://sopher.ai/"
        else:
            # Unrecognized host - use safe default
            logger.warning(f"Unrecognized host header: {host}")
            frontend_url = "https://sopher.ai/"
    else:
        # No host header - use production URL as fallback
        frontend_url = "https://sopher.ai/"

    return RedirectResponse(url=frontend_url, status_code=status.HTTP_302_FOUND)


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Clear authentication cookies"""
    clear_auth_cookies(response, request)
    return {"message": "Logged out successfully"}


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
