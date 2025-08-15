# syntax=docker/dockerfile:1.4

# Build stage with cached dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools with apt cache
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    rm -f /var/lib/apt/lists/lock && apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists*

# Upgrade pip and build tools
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip==24.3.1 setuptools==75.1.0 wheel==0.44.0

# Install python dependencies using cached wheels when possible
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefer-binary -r requirements.txt

COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefer-binary -e . --no-deps

# Production runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install minimal runtime dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    rm -f /var/lib/apt/lists/lock && apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    dumb-init \
    && rm -rf /var/lib/apt/lists*

# Create non-root user
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -d /home/appuser -s /bin/bash -c "App User" appuser && \
    mkdir -p /home/appuser && \
    chown -R appuser:appgroup /home/appuser

# Copy installed packages and application code
COPY --from=builder /usr/local /usr/local
COPY --chown=appuser:appgroup app ./app

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /tmp/app && \
    chown -R appuser:appgroup /app/logs /tmp/app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    TMPDIR=/tmp/app \
    HOME=/home/appuser

USER appuser

EXPOSE 8000 9000

HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f -X GET http://localhost:8000/healthz || exit 1

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--access-log", \
     "--use-colors", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]