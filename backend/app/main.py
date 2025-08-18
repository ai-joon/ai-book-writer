"""Main FastAPI application for sopher.ai"""

import json
import logging
import os
from contextlib import asynccontextmanager

import litellm
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from litellm.types.caching import LiteLLMCacheType
from starlette.exceptions import HTTPException as StarletteHTTPException

from .cache import cache
from .db import close_db, init_db
from .errors import ErrorCode, api_error
from .metrics import MetricsTracker, metrics_router
from .middleware import RequestIDMiddleware
from .routers import auth, outline
from .security import create_access_token

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configure LiteLLM
cache_type: LiteLLMCacheType = LiteLLMCacheType.REDIS
litellm.cache = litellm.Cache(
    type=cache_type,
    host=os.getenv("REDIS_HOST", "localhost"),
    port=os.getenv("REDIS_PORT", "6379"),
    db=int(os.getenv("REDIS_DB", "0")),
)
litellm.success_callback = ["prometheus"]
litellm.failure_callback = ["prometheus"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting sopher.ai backend...")
    await init_db()
    await cache.connect()
    logger.info("Database and cache connected")

    yield

    # Shutdown
    logger.info("Shutting down sopher.ai backend...")
    await cache.disconnect()
    await close_db()
    logger.info("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="sopher.ai",
    description="AI-powered book writing system",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Request-ID"],
)

# Request ID middleware
app.add_middleware(RequestIDMiddleware)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    MetricsTracker.track_api_request(
        method=request.method, endpoint=request.url.path, status_code=422
    )
    response = api_error(
        ErrorCode.VALIDATION_ERROR.value,
        "Invalid request.",
        hint="Check request body against schema.",
        details={"errors": exc.errors()},
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
    body = json.loads(response.body)
    logger.error(
        "validation error",
        extra={
            "error_id": body["error_id"],
            "request_id": body["request_id"],
            "error_code": body["error_code"],
            "path": request.url.path,
            "method": request.method,
            "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
        },
    )
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    MetricsTracker.track_api_request(
        method=request.method, endpoint=request.url.path, status_code=exc.status_code
    )
    code_map = {
        status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED.value,
        status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN.value,
        status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND.value,
        status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED.value,
    }
    error_code = code_map.get(exc.status_code, ErrorCode.HTTP_ERROR.value)
    response = api_error(
        error_code,
        str(exc.detail),
        status=exc.status_code,
    )
    body = json.loads(response.body)
    logger.error(
        "http error",
        extra={
            "error_id": body["error_id"],
            "request_id": body["request_id"],
            "error_code": body["error_code"],
            "path": request.url.path,
            "method": request.method,
            "status": exc.status_code,
        },
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected errors"""
    MetricsTracker.track_api_request(
        method=request.method, endpoint=request.url.path, status_code=500
    )
    response = api_error(
        ErrorCode.INTERNAL_ERROR.value,
        "An internal error occurred.",
        hint="Please try again later.",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    body = json.loads(response.body)
    logger.error(
        f"unhandled error: {exc}",
        extra={
            "error_id": body["error_id"],
            "request_id": body["request_id"],
            "error_code": body["error_code"],
            "path": request.url.path,
            "method": request.method,
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
    return response


# Health check endpoints
@app.get("/healthz", tags=["health"])
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": "sopher.ai"}


@app.get("/readyz", tags=["health"])
async def readiness_check():
    """Readiness check - verify dependencies"""
    try:
        # Check Redis
        await cache.redis.ping()
        return {"status": "ready", "redis": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "error": str(e)},
        )


@app.get("/livez", tags=["health"])
async def liveness_check():
    """Liveness check"""
    return {"status": "alive"}


# Demo endpoint to generate JWT token (for development)
@app.post("/auth/demo-token", tags=["auth"])
async def get_demo_token():
    """Get a demo JWT token for testing"""
    token_data = {
        "user_id": "demo-user",
        "project_id": "00000000-0000-0000-0000-000000000000",
        "role": "author",
    }
    access_token = create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(metrics_router, prefix="/api", tags=["metrics"])
app.include_router(outline.router, prefix="/api/v1", tags=["outline"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "sopher.ai",
        "version": "0.1.0",
        "description": "AI-powered book writing system",
        "docs": "/docs",
        "health": "/healthz",
        "metrics": "/api/metrics",
    }


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track all HTTP requests"""
    import time

    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Track metrics for successful requests
    if response.status_code < 400:
        MetricsTracker.track_api_request(
            method=request.method, endpoint=request.url.path, status_code=response.status_code
        )

    return response
