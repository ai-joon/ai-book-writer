# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . \
    && pip cache purge

# Production runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with specific UID for security
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -d /home/appuser -s /bin/bash -c "App User" appuser && \
    mkdir -p /home/appuser && \
    chown -R appuser:appgroup /home/appuser

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

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

# Production-optimized command with proper signal handling
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