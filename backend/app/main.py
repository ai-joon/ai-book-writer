"""Main FastAPI application for sopher.ai"""

import logging
import os
from contextlib import asynccontextmanager

import litellm
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .cache import cache
from .db import close_db, init_db
from .metrics import MetricsTracker, metrics_router
from .routers import outline
from .security import create_access_token

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.cache = litellm.Cache(
    type="redis",
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
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


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    MetricsTracker.track_api_request(
        method=request.method, endpoint=request.url.path, status_code=422
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    MetricsTracker.track_api_request(
        method=request.method, endpoint=request.url.path, status_code=exc.status_code
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


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
