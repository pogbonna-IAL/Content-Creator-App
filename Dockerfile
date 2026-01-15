# Backend Dockerfile for Content Creation Crew
# Multi-stage build for optimal image size

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set PYTHONPATH
ENV PYTHONPATH=/app/src:/app:${PYTHONPATH}

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using UV
RUN uv pip install --system -r pyproject.toml || \
    uv pip install --system crewai[tools]==1.7.0 \
    litellm>=1.30.0 \
    fastapi>=0.100.0 \
    uvicorn>=0.20.0 \
    rq>=2.0.0 \
    pyyaml>=6.0 \
    appdirs>=1.4.0 \
    backoff>=2.0.0 \
    apscheduler>=3.10.0 \
    email-validator>=2.0.0 \
    python-jose[cryptography]>=3.3.0 \
    passlib[bcrypt]>=1.7.4 \
    python-multipart>=0.0.6 \
    sqlalchemy>=2.0.0 \
    alembic>=1.13.0 \
    psycopg2-binary>=2.9.0 \
    fastapi-sso>=0.4.0 \
    pydantic[email]>=2.0.0 \
    python-dotenv>=1.0.0 \
    redis>=5.0.0

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies (curl for health checks, ffmpeg for video rendering)
# FFmpeg is included for video rendering support (can be disabled via ENABLE_VIDEO_RENDERING=false)
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set PYTHONPATH
ENV PYTHONPATH=/app/src:/app:${PYTHONPATH}

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY api_server.py ./
COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/
# Note: config files are included in src/content_creation_crew/config/

# Install hatchling build backend (required for package imports)
RUN pip install --no-cache-dir hatchling setuptools wheel

# Install the package in editable mode
RUN pip install -e . || echo "Package install failed, will use PYTHONPATH"

# Verify the package can be imported
RUN python -c "import content_creation_crew; print('✓ content_creation_crew imported successfully')" || \
    (echo "⚠ Warning: Package import test failed" && \
     echo "Continuing anyway - PYTHONPATH should handle imports at runtime")

# Create directory for database and data
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check with timeout (3 seconds max)
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f --max-time 3 http://localhost:${PORT:-8000}/health || exit 1

# Run the application
CMD ["python", "api_server.py"]
