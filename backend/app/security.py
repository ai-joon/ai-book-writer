"""Security and authentication"""

import hashlib
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# API key encryption
FERNET_KEY = os.getenv("FERNET_KEY", Fernet.generate_key().decode())
fernet = Fernet(FERNET_KEY.encode())

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer scheme (make it optional for cookie support)
security = HTTPBearer(auto_error=False)


class TokenData:
    """Token payload data"""

    def __init__(
        self, user_id: str, project_id: Optional[str] = None, role: str = "author", **kwargs
    ):
        self.user_id = user_id
        self.project_id = project_id
        self.role = role
        self.extra = kwargs


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        return TokenData(
            user_id=user_id,
            project_id=payload.get("project_id"),
            role=payload.get("role", "author"),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
) -> TokenData:
    """Get current user from JWT token (Bearer or Cookie)"""
    token = None

    # First try Bearer token from Authorization header
    if credentials:
        token = credentials.credentials

    # Fall back to cookie if no Bearer token
    if not token and access_token_cookie:
        token = access_token_cookie

    # Also support query parameter for SSE endpoints (backward compatibility)
    if not token:
        token = request.query_params.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(token)


async def get_current_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Verify user has admin role"""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key for storage"""
    return str(fernet.encrypt(api_key.encode()).decode())


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for use"""
    return str(fernet.decrypt(encrypted_key.encode()).decode())


def hash_api_key_id(api_key: str) -> str:
    """Create SHA-256 hash of API key for identification"""
    return hashlib.sha256(api_key.encode()).hexdigest()


class RateLimiter:
    """Rate limiting helper"""

    def __init__(self, requests: int = 60, window: int = 60):
        self.requests = requests
        self.window = window

    async def check_rate_limit(self, key: str, cache_client) -> bool:
        """Check if rate limit exceeded"""
        from .cache import cache

        count = await cache.increment(f"rate:{key}", ttl=self.window)
        return count <= self.requests


# Default rate limiter
rate_limiter = RateLimiter(requests=60, window=60)
