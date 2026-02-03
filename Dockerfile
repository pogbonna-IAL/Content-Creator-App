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
ENV PYTHONPATH=/app/src:/app

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
    redis>=5.0.0 \
    piper-tts>=1.2.0 \
    gtts>=2.4.0 \
    pydub>=0.25.1

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
ENV PYTHONPATH=/app/src:/app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY api_server.py ./
COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY scripts/ ./scripts/

# Copy src directory
# IMPORTANT: Railway build context must include src/ directory
# If this fails, ensure:
# 1. src/ directory is committed to git and pushed to repository
# 2. railway.json buildContext is set to "." (project root)
# 3. Railway build cache is cleared (Settings -> Clear Build Cache)
# 4. Check that Railway is building from the correct branch/commit
COPY src ./src/
# Note: config files are included in src/content_creation_crew/config/

# Verify src directory was copied correctly
RUN test -d ./src && echo "✓ src directory copied successfully" || (echo "✗ ERROR: src directory not found after COPY" && echo "Build context contents:" && ls -la / && exit 1)

# Verify services directory exists
RUN test -d ./src/content_creation_crew/services && echo "✓ services directory found" || (echo "✗ ERROR: services directory not found" && echo "src contents:" && ls -la ./src/content_creation_crew/ 2>/dev/null || echo "content_creation_crew directory not found" && exit 1)

# Verify password_validator module exists
RUN test -f ./src/content_creation_crew/services/password_validator.py && echo "✓ password_validator.py found" || (echo "✗ ERROR: password_validator.py not found" && echo "services contents:" && ls -la ./src/content_creation_crew/services/ 2>/dev/null || echo "services directory not found" && exit 1)

# Install hatchling build backend (required for package imports)
RUN pip install --no-cache-dir hatchling setuptools wheel

# Install the package in editable mode
RUN pip install -e . || echo "Package install failed, will use PYTHONPATH"

# Verify the package can be imported
RUN python -c "import content_creation_crew; print('✓ content_creation_crew imported successfully')" || \
    (echo "⚠ Warning: Package import test failed" && \
     echo "Continuing anyway - PYTHONPATH should handle imports at runtime")

# Verify password_validator can be imported
RUN python -c "from content_creation_crew.services.password_validator import get_password_validator; print('✓ password_validator imported successfully')" || \
    (echo "✗ ERROR: password_validator import failed" && \
     echo "PYTHONPATH:" && echo $PYTHONPATH && \
     echo "Python path:" && python -c "import sys; print('\n'.join(sys.path))" && \
     echo "Checking for file:" && ls -la ./src/content_creation_crew/services/password_validator.py 2>&1 && \
     exit 1)

# Create directory for database and data
RUN mkdir -p /app/data

# Download Piper TTS voice models during build (optional)
# If download fails, build continues - model will be downloaded on first use
RUN mkdir -p /app/models/piper && \
    echo "========================================" && \
    echo "Downloading Piper TTS models..." && \
    echo "========================================" && \
    (python -c "import sys; \
               from piper import download_voice; \
               import os; \
               import shutil; \
               print('[INFO] Using piper-tts library to download model...'); \
               voice_path = None; \
               try: \
                   voice_path = download_voice('en_US-lessac-medium', '/app/models/piper'); \
                   print(f'[OK] Downloaded to: {voice_path}'); \
               except Exception as e: \
                   print(f'[WARN] Download with underscore failed: {e}'); \
                   try: \
                       voice_path = download_voice('en-US-lessac-medium', '/app/models/piper'); \
                       print(f'[OK] Downloaded to: {voice_path}'); \
                   except Exception as e2: \
                       print(f'[WARN] Download with hyphen also failed: {e2}'); \
                       print('[INFO] Model will be downloaded on first use'); \
                       sys.exit(0); \
               if not voice_path or not os.path.exists(voice_path): \
                   print('[WARN] Download succeeded but file not found'); \
                   sys.exit(0); \
               file_size = os.path.getsize(voice_path); \
               if file_size < 1000: \
                   print(f'[WARN] Downloaded file too small: {file_size} bytes'); \
                   sys.exit(0); \
               print(f'[OK] Model file verified: {file_size:,} bytes'); \
               target_path = '/app/models/piper/en_US-lessac-medium.onnx'; \
               if voice_path != target_path: \
                   if os.path.exists(target_path): \
                       os.remove(target_path); \
                   if os.path.isdir(voice_path): \
                       model_file = os.path.join(voice_path, 'model.onnx'); \
                       if os.path.exists(model_file): \
                           shutil.copy2(model_file, target_path); \
                       else: \
                           print('[WARN] Model directory found but model.onnx not inside'); \
                           sys.exit(0); \
                   else: \
                       shutil.copy2(voice_path, target_path); \
               if not os.path.exists(target_path): \
                   print('[WARN] Failed to copy model to target location'); \
                   sys.exit(0); \
               final_size = os.path.getsize(target_path); \
               print(f'[OK] Model ready at: {target_path} ({final_size:,} bytes)');" || \
     echo "[WARN] Piper model download failed - will be downloaded on first use") && \
    echo "Checking for downloaded model..." && \
    if [ -f /app/models/piper/en_US-lessac-medium.onnx ]; then \
        FILE_SIZE=$(stat -c%s /app/models/piper/en_US-lessac-medium.onnx 2>/dev/null || stat -f%z /app/models/piper/en_US-lessac-medium.onnx 2>/dev/null || echo "0") && \
        if [ "$FILE_SIZE" -gt 1000 ]; then \
            echo "[OK] Piper model ready: $FILE_SIZE bytes" && \
            ls -lh /app/models/piper/en_US-lessac-medium.onnx; \
        else \
            echo "[WARN] Model file exists but is too small: $FILE_SIZE bytes"; \
        fi; \
    else \
        echo "[INFO] Model not found - will be downloaded automatically on first use"; \
    fi && \
    echo "========================================" && \
    echo "[INFO] Piper TTS model setup complete" && \
    echo "[INFO] Note: If model not downloaded, it will be fetched on first use" && \
    echo "========================================"

# Set default PIPER_MODEL_PATH if not already set
ENV PIPER_MODEL_PATH=/app/models/piper

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
