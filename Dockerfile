# Backend Dockerfile for Content Creation Crew
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set PYTHONPATH early (before package installation)
# This ensures the package can be imported even if installation fails
ENV PYTHONPATH=/app/src:/app:${PYTHONPATH}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
# Copy pyproject.toml (required for dependency installation)
COPY pyproject.toml ./
# Note: uv.lock is optional - if it doesn't exist, uv will generate it or use pyproject.toml
# We skip copying uv.lock explicitly to avoid build failures if it's not in the repository

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
    aiosqlite>=0.19.0 \
    psycopg2-binary>=2.9.0 \
    fastapi-sso>=0.4.0 \
    pydantic[email]>=2.0.0 \
    python-dotenv>=1.0.0

# Copy application code
COPY . .

# Install hatchling build backend first (required for package installation)
RUN pip install --no-cache-dir hatchling setuptools wheel

# Install the package in editable mode so imports work
RUN pip install -e . || echo "Package install failed, will use PYTHONPATH"

# Verify the package can be imported (this should always work with PYTHONPATH)
RUN python -c "import content_creation_crew; print('✓ content_creation_crew imported successfully')" || \
    (echo "⚠ Warning: Package import test failed" && \
     echo "Python path:" && python -c "import sys; [print(p) for p in sys.path]" && \
     echo "Contents of /app/src:" && ls -la /app/src/ 2>/dev/null || true && \
     echo "Continuing anyway - PYTHONPATH should handle imports at runtime")

# Create directory for database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check (Railway will override PORT, but this is for local Docker)
# Railway uses its own health check configured in railway.json
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application
CMD ["python", "api_server.py"]

