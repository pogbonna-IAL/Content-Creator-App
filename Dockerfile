# Backend Dockerfile for Content Creation Crew
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

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
    fastapi-sso>=0.4.0 \
    pydantic[email]>=2.0.0 \
    python-dotenv>=1.0.0

# Copy application code
COPY . .

# Install the package in editable mode so imports work
# This makes the content_creation_crew package importable
RUN pip install -e . || (echo "Package install failed, using PYTHONPATH fallback" && true)

# Add src directory to PYTHONPATH (ensures package can be imported even if install fails)
# This is critical for the content_creation_crew package to be found
ENV PYTHONPATH=/app/src:/app:${PYTHONPATH}

# Create directory for database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "api_server.py"]

