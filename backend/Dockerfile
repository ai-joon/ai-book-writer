# Build stage with dependency caching optimization
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
# Group frequently changing packages separately for better caching
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip and install build tools in separate layer for caching
RUN pip install --no-cache-dir --upgrade pip==24.3.1 setuptools==75.1.0 wheel==0.44.0

# Copy requirements first for better layer caching
COPY requirements.txt ./

# Install dependencies and create wheels (optimized for caching)
RUN pip wheel --no-cache-dir \
    --wheel-dir /tmp/wheels \
    -r requirements.txt \
    && pip install --no-cache-dir \
    --find-links /tmp/wheels \
    -r requirements.txt

# Copy pyproject.toml and install package in development mode (minimal impact)
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . --no-deps

# Production runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install minimal runtime dependencies in single layer
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with specific UID for security
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -d /home/appuser -s /bin/bash -c "App User" appuser && \
    mkdir -p /home/appuser && \
    chown -R appuser:appgroup /home/appuser

# Install dependencies from wheels (faster than copying site-packages)
RUN pip install --no-cache-dir --upgrade pip==24.3.1
COPY --from=builder /tmp/wheels /tmp/wheels
COPY --from=builder /app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links /tmp/wheels -r /tmp/requirements.txt \
    && rm -rf /tmp/wheels /tmp/requirements.txt

# Copy application code with proper ownership
COPY --chown=appuser:appgroup app ./app

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /tmp/app && \
    chown -R appuser:appgroup /app/logs /tmp/app

# Set comprehensive environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    TMPDIR=/tmp/app \
    HOME=/home/appuser

# Switch to non-root user
USER appuser

# Expose application and metrics ports
EXPOSE 8000 9000

# Enhanced health check with proper error handling
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f -X GET http://localhost:8000/healthz || exit 1

# Production-optimized command with proper signal handling using dumb-init
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