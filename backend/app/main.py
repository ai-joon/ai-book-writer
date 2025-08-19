"""Main FastAPI application for sopher.ai"""

import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

import litellm
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .cache import cache
from .db import close_db, init_db
from .errors import ErrorCode, api_error
from .logging import clear_request_context, parse_trace_context, set_request_context, setup_logging
from .metrics import MetricsTracker, metrics_router
from .routers import auth, outline, usage
from .security import create_access_token

# Configure structured logging early
logger = setup_logging()

# Configure LiteLLM
# For LiteLLM 1.48.x, use string type for cache configuration
litellm.cache = litellm.Cache(
    type="redis",  # type: ignore[arg-type]
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

    # Check OAuth configuration
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if not google_client_id or not google_client_secret:
        logger.warning(
            "Google OAuth credentials not configured. Authentication will not work. "
            "Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables. "
            "See docs/oauth-fix-guide.md for setup instructions."
        )

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
# When credentials are included, we must specify exact origins (not wildcards)
default_origins = "https://sopher.ai,https://api.sopher.ai,http://localhost:3000"
cors_origins = os.getenv("CORS_ORIGINS", default_origins).split(",")
# Remove any whitespace from origins
cors_origins = [origin.strip() for origin in cors_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Request-ID"],
)

# Request ID handled by our logging middleware below

# Add compression middleware for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)


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
        exc_info=True,
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
        exc_info=True,
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
    logger.exception(
        "unhandled error",
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


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log all HTTP requests with GCP-compatible structured logging and track metrics."""
    # Start timer
    start_time = time.time()
    perf_start = time.perf_counter()

    # Extract or generate request ID
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # Extract trace context if present
    trace_header = request.headers.get("X-Cloud-Trace-Context")
    trace_id = None
    span_id = None
    if trace_header:
        trace_id, span_id = parse_trace_context(trace_header)

    # Get request details
    method = request.method
    url = str(request.url)
    user_agent = request.headers.get("User-Agent", "")
    referer = request.headers.get("Referer", "")

    # Get client IP (considering proxy headers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        remote_ip = forwarded_for.split(",")[0].strip()
    else:
        remote_ip = request.client.host if request.client else ""

    # Set context for this request
    set_request_context(
        request_id=request_id,
        trace_id=trace_id,
        span_id=span_id,
    )

    # Store request ID in request state for other middleware
    request.state.request_id = request_id

    try:
        # Process the request
        response = await call_next(request)

        # Calculate latency
        latency = time.time() - start_time
        process_time = time.perf_counter() - perf_start

        # Determine severity based on status code
        if response.status_code >= 500:
            severity = "ERROR"
        elif response.status_code >= 400:
            severity = "WARNING"
        else:
            severity = "INFO"

        # Build HTTP request info for logging
        http_request_info = {
            "requestMethod": method,
            "requestUrl": url,
            "status": response.status_code,
            "userAgent": user_agent,
            "remoteIp": remote_ip,
            "referer": referer,
            "latency": f"{latency:.3f}s",
        }

        # Update context with HTTP request info
        set_request_context(http_request=http_request_info)

        # Log the request
        if severity == "ERROR":
            logger.error("request completed", extra={"http_status": response.status_code})
        elif severity == "WARNING":
            logger.warning("request completed", extra={"http_status": response.status_code})
        else:
            logger.info("request completed", extra={"http_status": response.status_code})

        # Add request ID and process time to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        # Track metrics for successful requests
        if response.status_code < 400:
            MetricsTracker.track_api_request(
                method=request.method, endpoint=request.url.path, status_code=response.status_code
            )

        return response  # type: ignore[no-any-return]

    finally:
        # Clear context after request
        clear_request_context()


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
app.include_router(usage.router, prefix="/api/v1", tags=["usage"])


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
