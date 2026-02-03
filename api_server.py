#!/usr/bin/env python
"""
FastAPI server for Content Creation Crew
Provides REST API endpoint for the web UI
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

# Prevent LiteLLM from importing proxy modules we don't need
os.environ['LITELLM_DISABLE_PROXY'] = '1'
# Set LiteLLM timeout to a reasonable default (will be overridden by crew.py with CREWAI_TIMEOUT)
# Default to 360 seconds (6 minutes) as a safe fallback
# Note: crew.py will override this with CREWAI_TIMEOUT + 60 seconds buffer
os.environ['LITELLM_REQUEST_TIMEOUT'] = '360'
os.environ['LITELLM_TIMEOUT'] = '360'
os.environ['LITELLM_CONNECTION_TIMEOUT'] = '60'

# Also configure litellm directly if available
try:
    import litellm
    litellm.request_timeout = 360  # Will be overridden by crew.py
    litellm.timeout = 360  # Will be overridden by crew.py
    litellm.drop_params = True  # Don't drop timeout params
    
    # Configure httpx timeout for Ollama connections
    # httpx has a default timeout of 600 seconds, we need to override it
    # Use 360 seconds (6 minutes) as default, will be overridden by crew.py if needed
    try:
        import httpx
        default_timeout = 360.0  # 6 minutes default
        # Patch httpx.Client to use extended timeout by default
        # LiteLLM creates httpx clients internally, so we need to patch the Client class
        _original_client_init = httpx.Client.__init__
        def _patched_client_init(self, *args, timeout=None, **kwargs):
            # If timeout is not provided or is <= 300 seconds, use default timeout
            if timeout is None:
                timeout = httpx.Timeout(default_timeout, connect=60.0)
            elif isinstance(timeout, (int, float)):
                if timeout <= 300:
                    # Extend timeout to default
                    timeout = httpx.Timeout(default_timeout, connect=60.0)
                else:
                    # Use provided timeout but ensure connect timeout is reasonable
                    timeout = httpx.Timeout(timeout, connect=60.0)
            elif isinstance(timeout, httpx.Timeout):
                # If it's already a Timeout object, check if read timeout is <= 300
                read_timeout = getattr(timeout, 'read', None) or getattr(timeout, 'timeout', None)
                if read_timeout is None or read_timeout <= 300:
                    # Extend timeout to default
                    timeout = httpx.Timeout(default_timeout, connect=60.0)
            return _original_client_init(self, *args, timeout=timeout, **kwargs)
        httpx.Client.__init__ = _patched_client_init
        
        # Also patch AsyncClient for async operations
        _original_async_client_init = httpx.AsyncClient.__init__
        def _patched_async_client_init(self, *args, timeout=None, **kwargs):
            if timeout is None:
                timeout = httpx.Timeout(default_timeout, connect=60.0)
            elif isinstance(timeout, (int, float)):
                if timeout <= 300:
                    timeout = httpx.Timeout(default_timeout, connect=60.0)
                else:
                    timeout = httpx.Timeout(timeout, connect=60.0)
            elif isinstance(timeout, httpx.Timeout):
                read_timeout = getattr(timeout, 'read', None) or getattr(timeout, 'timeout', None)
                if read_timeout is None or read_timeout <= 300:
                    timeout = httpx.Timeout(default_timeout, connect=60.0)
            return _original_async_client_init(self, *args, timeout=timeout, **kwargs)
        httpx.AsyncClient.__init__ = _patched_async_client_init
    except (ImportError, AttributeError):
        pass
except ImportError:
    pass

# Handle missing fastapi-sso gracefully
try:
    import fastapi_sso
except ImportError:
    # Create a dummy module to prevent ImportError when LiteLLM tries to import it
    import types
    fastapi_sso = types.ModuleType('fastapi_sso')
    fastapi_sso.sso = types.ModuleType('fastapi_sso.sso')
    fastapi_sso.sso.base = types.ModuleType('fastapi_sso.sso.base')
    fastapi_sso.sso.base.OpenID = type('OpenID', (), {})
    sys.modules['fastapi_sso'] = fastapi_sso
    sys.modules['fastapi_sso.sso'] = fastapi_sso.sso
    sys.modules['fastapi_sso.sso.base'] = fastapi_sso.sso.base

# Windows signal compatibility patch
if sys.platform == 'win32':
    import signal
    for sig_name, sig_value in [('SIGHUP', 1), ('SIGTSTP', 20), ('SIGCONT', 18), 
                                  ('SIGQUIT', 3), ('SIGUSR1', 10), ('SIGUSR2', 12)]:
        if not hasattr(signal, sig_name):
            setattr(signal, sig_name, sig_value)

# Import the package __init__ first to ensure its patch runs
# Ensure src directory is in Python path for Railway/Docker deployments
# PYTHONPATH should be set to /app/src:/app in Dockerfile, but add fallbacks

# Add src to Python path (relative to api_server.py)
src_path = os.path.join(os.path.dirname(__file__), "src")
if os.path.exists(src_path) and src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add /app/src if we're in Docker/Railway (should already be in PYTHONPATH, but ensure it)
docker_src_path = "/app/src"
if os.path.exists(docker_src_path) and docker_src_path not in sys.path:
    sys.path.insert(0, docker_src_path)

# Import content_creation_crew package - CRITICAL: this must succeed
# The package __init__.py contains important patches that must run before other imports
import content_creation_crew  # noqa: F401

# Import config and logging setup FIRST (before other imports that may use them)
from content_creation_crew.config import config
from content_creation_crew.logging_config import setup_logging, RequestIDMiddleware

# Set up structured logging with environment and request ID
setup_logging(env=config.ENV, log_level=config.LOG_LEVEL)
import logging
logger = logging.getLogger(__name__)

# Force immediate log output for Railway
import sys
print("=" * 60, file=sys.stdout, flush=True)
print(f"LOGGING TEST - Environment: {config.ENV}, Log Level: {config.LOG_LEVEL}", file=sys.stdout, flush=True)
logger.info("=" * 60)
logger.info("LOGGING TEST - This should appear in Railway logs")
logger.info(f"Environment: {config.ENV}")
logger.info(f"Log Level: {config.LOG_LEVEL}")
logger.info("=" * 60)
sys.stdout.flush()

# Set up PII redaction filter for all logs
try:
    from content_creation_crew.logging_filter import setup_pii_redaction
    setup_pii_redaction()
    logger.info("✓ PII redaction filter enabled (emails, tokens, passwords will be redacted)")
except Exception as e:
    logger.warning(f"Failed to enable PII redaction filter: {e}")

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from content_creation_crew.crew import ContentCreationCrew
from content_creation_crew.auth_routes import router as auth_router
from content_creation_crew.oauth_routes import router as oauth_router
from content_creation_crew.subscription_routes import router as subscription_router
from content_creation_crew.billing_routes import router as billing_router
from content_creation_crew.auth import get_current_user
from content_creation_crew.database import init_db, User, get_db, Session, engine, ContentArtifact
from content_creation_crew.services.subscription_service import SubscriptionService
from content_creation_crew.services.plan_policy import PlanPolicy
from content_creation_crew.services.content_cache import get_cache
from sqlalchemy import text
import asyncio
import json
from typing import AsyncGenerator

# Start scheduled jobs (GDPR cleanup, etc.)
try:
    import os as _os
    if _os.getenv("DISABLE_SCHEDULER", "false").lower() not in ("true", "1", "yes"):
        from content_creation_crew.services.scheduled_jobs import start_scheduler
        start_scheduler()
        logger.info("✓ Scheduled jobs started (GDPR cleanup daily at 2 AM)")
    else:
        logger.info("Scheduled jobs disabled via DISABLE_SCHEDULER env var")
except Exception as e:
    logger.warning(f"Failed to start scheduled jobs: {e}. GDPR cleanup can still be run manually via cron or scripts/gdpr_cleanup.py")

# Validate FFmpeg availability at startup (if video rendering enabled)
try:
    from content_creation_crew.services.ffmpeg_check import validate_ffmpeg_startup
    validate_ffmpeg_startup(
        enable_video_rendering=config.ENABLE_VIDEO_RENDERING,
        timeout=5.0
    )
except RuntimeError as e:
    # FFmpeg required but missing - fail fast
    logger.critical(f"Startup validation failed: {e}")
    if config.ENV in ["staging", "prod"]:
        # Fail fast in staging/prod
        sys.exit(1)
    else:
        # Warn in dev but continue
        logger.warning("Continuing in dev mode despite FFmpeg validation failure")
except Exception as e:
    logger.warning(f"FFmpeg validation check failed: {e}")
    # Continue anyway - validation will happen when video rendering is attempted

# Disable debug mode in staging/prod
debug_mode = config.ENV == "dev"

# Lifespan event handler (replaces deprecated @app.on_event)
@asynccontextmanager
async def lifespan(app):
    """
    FastAPI lifespan event handler.
    Runs database migrations automatically on application startup.
    This ensures migrations are applied before the app accepts requests.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 Application Startup - Running Database Migrations")
    logger.info("=" * 60)
    
    try:
        # Run database migrations using Alembic
        logger.info("Initializing database and running migrations...")
        init_db()
        logger.info("✅ Database migrations completed successfully")
    except Exception as e:
        error_msg = f"❌ Database initialization/migration failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        # In production/staging, fail fast if migrations fail
        if config.ENV in ["staging", "prod"]:
            logger.critical("=" * 60)
            logger.critical("FATAL: Database migrations failed in production environment")
            logger.critical("Application cannot start without a properly migrated database")
            logger.critical("=" * 60)
            logger.critical("Troubleshooting steps:")
            logger.critical("1. Check DATABASE_URL is correctly set in Railway")
            logger.critical("2. Verify PostgreSQL service is running and accessible")
            logger.critical("3. Check Railway logs for connection errors")
            logger.critical("4. Manually run migrations: alembic upgrade head")
            logger.critical("=" * 60)
            # Exit with error code to prevent app from starting
            sys.exit(1)
        else:
            # In dev, warn but continue (allows for manual migration)
            logger.warning("⚠️  Continuing in dev mode despite migration failure")
            logger.warning("⚠️  Database features may not work until migrations are applied")
            logger.warning("⚠️  Run 'alembic upgrade head' to apply migrations manually")
    
    yield  # Application runs here
    
    # Shutdown (if needed in the future)
    logger.info("Application shutting down...")

app = FastAPI(
    lifespan=lifespan,
    title="Content Creation Crew API",
    description="""
    Content Creation Crew API - AI-powered content generation platform.
    
    ## Features
    
    * **Content Generation**: Generate blog posts, social media content, audio scripts, and video scripts
    * **Voice Generation**: Text-to-speech (TTS) voiceover generation
    * **Video Rendering**: Render videos from scripts with narration
    * **Job Management**: Track content generation jobs with real-time progress via SSE
    * **Subscription Tiers**: Tiered access with usage limits
    
    ## Authentication
    
    All endpoints (except `/health`, `/meta`, `/metrics`) require authentication via Bearer token.
    Obtain a token by logging in at `/v1/auth/login`.
    
    ## Rate Limits
    
    Rate limits are applied per subscription tier. See `/docs/rate-limits.md` for details.
    
    ## SSE Streaming
    
    Job progress is streamed via Server-Sent Events (SSE) at `/v1/content/jobs/{id}/stream`.
    """,
    version=config.BUILD_VERSION or "0.1.0",
    debug=debug_mode,
    docs_url="/docs" if debug_mode else None,
    redoc_url="/redoc" if debug_mode else None,
    openapi_tags=[
        {
            "name": "content",
            "description": "Content generation endpoints. Create jobs, track progress, and retrieve artifacts."
        },
        {
            "name": "auth",
            "description": "Authentication endpoints. Sign up, log in, and manage user accounts."
        },
        {
            "name": "subscription",
            "description": "Subscription management. View tiers, usage, and plan information."
        },
        {
            "name": "billing",
            "description": "Billing endpoints. Manage payments and subscriptions."
        },
        {
            "name": "health",
            "description": "Health check and system information endpoints."
        }
    ],
)

# Add request ID middleware for structured logging (must be first)
app.add_middleware(RequestIDMiddleware)

# Add HTTP attributes logging middleware (after request ID, before other middleware)
try:
    from content_creation_crew.middleware.http_attributes_logger import HTTPAttributesLoggerMiddleware
    app.add_middleware(HTTPAttributesLoggerMiddleware)
    logger.info("✓ HTTP attributes logging middleware enabled")
except Exception as e:
    logger.warning(f"Failed to enable HTTP attributes logging middleware: {e}")

# Add metrics collection middleware (after request ID, before other middleware)
try:
    from content_creation_crew.middleware.metrics_middleware import MetricsMiddleware
    app.add_middleware(MetricsMiddleware)
    logger.info("Metrics collection middleware enabled")
except Exception as e:
    logger.warning(f"Failed to enable metrics middleware: {e}")

# Add request size limit middleware
try:
    from content_creation_crew.middleware.security import RequestSizeLimitMiddleware
    app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)  # 10MB
    logger.info("Request size limit middleware enabled (10MB)")
except Exception as e:
    logger.warning(f"Failed to enable request size limit middleware: {e}")

# Add rate limiting middleware (Redis-backed with in-memory fallback)
try:
    from content_creation_crew.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiting middleware enabled")
except Exception as e:
    logger.warning(f"Failed to enable rate limiting middleware: {e}")

# Enable CORS for Next.js frontend using config with strict settings
# Restrict methods and headers based on environment
allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
allowed_headers = [
    "Content-Type",
    "Authorization",
    "X-Request-ID",
    "Accept",
    "Origin",
    "Referer",
]

# In production, be more restrictive
if config.ENV in ["staging", "prod"]:
    # Remove PUT and PATCH if not needed
    allowed_methods = ["GET", "POST", "DELETE", "OPTIONS"]
    # Only allow essential headers
    allowed_headers = [
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "Accept",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
    expose_headers=["X-Request-ID"],  # Expose request ID to clients
    max_age=86400,  # Cache preflight requests for 24 hours (86400 seconds)
)

# #region agent log
# Add middleware to log CORS headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
import json as json_module
import time

class CORSDebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        try:
            with open('.cursor/debug.log', 'a') as f:
                log_entry = {
                    "sessionId": "debug-session",
                    "runId": "cors-headers",
                    "hypothesisId": "D",
                    "location": "api_server.py:360",
                    "message": "CORS response headers",
                    "data": {
                        "access_control_allow_origin": response.headers.get("access-control-allow-origin", "NOT_SET"),
                        "access_control_allow_credentials": response.headers.get("access-control-allow-credentials", "NOT_SET"),
                        "access_control_allow_methods": response.headers.get("access-control-allow-methods", "NOT_SET"),
                        "request_origin": request.headers.get("origin", "NOT_SET"),
                        "request_method": request.method,
                        "request_path": str(request.url.path)
                    },
                    "timestamp": int(time.time() * 1000)
                }
                f.write(json_module.dumps(log_entry) + '\n')
        except Exception:
            pass
        return response

app.add_middleware(CORSDebugMiddleware)
# #endregion

logger.info(f"✓ CORS configured with preflight caching (max_age: 86400s / 24h)")

# Request size limit middleware (M4)
from content_creation_crew.middleware.request_size_limit import RequestSizeLimitMiddleware

app.add_middleware(
    RequestSizeLimitMiddleware,
    max_request_bytes=config.MAX_REQUEST_BYTES,
    max_upload_bytes=config.MAX_UPLOAD_BYTES
)

# Global exception handlers (M3) - Error hygiene
from content_creation_crew.middleware.error_handler import (
    database_error_handler,
    validation_error_handler,
    http_exception_handler,
    generic_exception_handler
)
from sqlalchemy.exc import SQLAlchemyError
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Register exception handlers in order of specificity
app.add_exception_handler(SQLAlchemyError, database_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

logger.info("✓ Global exception handlers configured (M3 - error hygiene)")

# Include authentication routes
app.include_router(auth_router)
app.include_router(oauth_router)

# #region agent log
# Add middleware to log all requests to help debug 404s
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
import json as json_module
import time

class RequestDebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        import logging
        debug_logger = logging.getLogger(__name__)
        
        # Log request details
        log_data = {
            "sessionId": "debug-session",
            "runId": "request-debug",
            "hypothesisId": "E",
            "location": "api_server.py:430",
            "message": "Incoming request",
            "data": {
                "method": request.method,
                "path": str(request.url.path),
                "full_url": str(request.url),
                "headers": dict(request.headers),
                "query_params": dict(request.query_params)
            },
            "timestamp": int(time.time() * 1000)
        }
        debug_logger.warning(f"[DEBUG] Request: {json_module.dumps(log_data)}")
        
        response = await call_next(request)
        
        # Log response details
        log_data = {
            "sessionId": "debug-session",
            "runId": "request-debug",
            "hypothesisId": "E",
            "location": "api_server.py:450",
            "message": "Response sent",
            "data": {
                "status_code": response.status_code,
                "path": str(request.url.path),
                "response_headers": dict(response.headers)
            },
            "timestamp": int(time.time() * 1000)
        }
        debug_logger.warning(f"[DEBUG] Response: {json_module.dumps(log_data)}")
        
        return response

app.add_middleware(RequestDebugMiddleware)
# #endregion

app.include_router(subscription_router)
app.include_router(billing_router)

# #region agent log
# Add a test endpoint and log registered routes
@app.get("/api/test-routing")
async def test_routing():
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("[DEBUG] Test routing endpoint hit successfully")
    return {"message": "Routing works", "status": "ok"}

# Log all registered routes for debugging
import logging
route_logger = logging.getLogger(__name__)
all_routes = []
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        all_routes.append(f"{list(route.methods)} {route.path}")
route_logger.warning(f"[DEBUG] Registered routes count: {len(all_routes)}")
route_logger.warning(f"[DEBUG] Sample routes (first 20): {all_routes[:20]}")
# #endregion

# Include v1 content routes
from content_creation_crew.content_routes import router as content_router
app.include_router(content_router)

# Include GDPR routes
from content_creation_crew.gdpr_routes import router as gdpr_router
app.include_router(gdpr_router)
logger.info("✓ GDPR routes registered")

# Register Admin routes (M6)
from content_creation_crew.admin_routes import router as admin_router
app.include_router(admin_router)
logger.info("✓ Admin routes registered")

# Register Invoice routes
from content_creation_crew.invoice_routes import router as invoice_router
app.include_router(invoice_router)
logger.info("✓ Invoice routes registered")

# Register Refund routes
from content_creation_crew.refund_routes import router as refund_router
app.include_router(refund_router)
logger.info("✓ Refund routes registered")

# Add static file serving for storage (voiceovers, etc.)
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

# Serve storage files
storage_path = Path(os.getenv("STORAGE_PATH", "./storage"))
if storage_path.exists():
    # Mount main storage directory at /v1/storage
    app.mount("/v1/storage", StaticFiles(directory=str(storage_path)), name="storage")
    
    # Also mount voiceovers subdirectory at /voiceovers for easier access
    voiceovers_path = storage_path / "voiceovers"
    if voiceovers_path.exists():
        app.mount("/voiceovers", StaticFiles(directory=str(voiceovers_path)), name="voiceovers")
        logger.info(f"Voiceover files served from {voiceovers_path} at /voiceovers/")
    
    logger.info(f"Storage files served from {storage_path} at /v1/storage/")
else:
    logger.warning(f"Storage path {storage_path} does not exist, file serving disabled")

# Add exception handlers with request ID support
from content_creation_crew.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


class TopicRequest(BaseModel):
    topic: str
    content_types: list[str] = None  # Optional: ['blog', 'social', 'audio', 'video']


class ContentResponse(BaseModel):
    content: str
    topic: str
    generated_at: str


@app.get("/")
async def root():
    return {"message": "Content Creation Crew API", "status": "running"}


async def _check_ollama_health(ollama_url: str) -> bool:
    """Check Ollama health with timeout"""
    import httpx
    async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
        response = await client.get(f"{ollama_url}/api/tags")
        return response.status_code == 200


@app.get("/health/pool")
async def health_pool():
    """
    Database connection pool health check
    
    Returns detailed pool statistics for monitoring
    """
    from content_creation_crew.db.pool_monitor import get_pool_stats, check_pool_health
    
    stats = get_pool_stats()
    is_healthy, message = check_pool_health()
    
    response = {
        "healthy": is_healthy,
        "message": message,
        "pool_stats": stats
    }
    
    status_code = 200 if is_healthy else 503
    return JSONResponse(content=response, status_code=status_code)


@app.get("/health")
async def health():
    """
    Comprehensive health check endpoint (M5)
    
    Verifies:
    - Database connectivity (CRITICAL)
    - Redis connectivity (optional)
    - Storage availability and free space (optional)
    - LLM provider (Ollama) connectivity (optional)
    
    Returns:
    - 200 if critical components (database) are healthy
    - 503 only if critical components are DOWN
    
    Note: Optional components (LLM, Redis) can be DEGRADED without affecting health status.
    This ensures Railway health checks pass as long as the database is accessible.
    
    Strict timeouts enforced (never hangs)
    """
    from content_creation_crew.services.health_check import get_health_checker, HealthStatus
    
    health_checker = get_health_checker()
    result = await health_checker.check_all()
    
    # Add service metadata
    result["service"] = "content-creation-crew"
    result["environment"] = config.ENV
    
    # Determine health status based on critical vs optional components
    components = result.get("components", {})
    database_status = components.get("database", {}).get("status", "unknown")
    
    # Critical components that must be OK for service to be healthy
    critical_components = ["database"]
    
    # Check if any critical component is DOWN
    critical_down = any(
        components.get(comp, {}).get("status") == HealthStatus.DOWN.value
        for comp in critical_components
    )
    
    # Return 503 only if critical components are DOWN
    # Return 200 if critical components are OK (even if optional components are DEGRADED)
    if critical_down or database_status == HealthStatus.DOWN.value:
        return JSONResponse(
            content=result,
            status_code=503
        )
    
    # Service is healthy (critical components OK, optional components may be degraded)
    return JSONResponse(
        content=result,
        status_code=200
    )


@app.get("/health/ready")
async def health_ready():
    """
    Simple readiness check for Railway/deployment health checks.
    
    Returns 200 if the service is ready to accept requests.
    This is a lightweight check that doesn't verify all components.
    """
    try:
        # Quick database connectivity check
        from content_creation_crew.db.engine import test_connection
        if test_connection():
            return {"status": "ready", "service": "content-creation-crew"}
        else:
            return JSONResponse(
                content={"status": "not_ready", "reason": "database_unavailable"},
                status_code=503
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            content={"status": "not_ready", "reason": str(e)},
            status_code=503
        )


@app.get("/meta")
async def meta():
    """
    Metadata endpoint for build version and deployment information
    """
    return {
        "service": "content-creation-crew",
        "version": config.BUILD_VERSION,
        "commit": config.BUILD_COMMIT,
        "build_time": config.BUILD_TIME,
        "environment": config.ENV,
    }


@app.get("/metrics")
@app.get("/v1/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus text format including DB pool metrics
    """
    from content_creation_crew.services.metrics import get_metrics_collector
    from content_creation_crew.db.pool_monitor import get_pool_metrics_for_prometheus
    from fastapi.responses import Response
    
    collector = get_metrics_collector()
    metrics_text = collector.format_prometheus()
    
    # Add DB pool metrics
    try:
        pool_metrics = get_pool_metrics_for_prometheus()
        for metric_name, value in pool_metrics.items():
            metrics_text += f"\n# HELP {metric_name} Database connection pool metric\n"
            metrics_text += f"# TYPE {metric_name} gauge\n"
            metrics_text += f"{metric_name} {value}\n"
    except Exception as e:
        logger.warning(f"Failed to add pool metrics: {e}")
    
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


async def run_crew_async(topic: str, tier: str = 'free', content_types: list = None, use_cache: bool = True) -> AsyncGenerator[str, None]:
    """
    Run the crew asynchronously and stream progress updates
    
    Args:
        topic: Content topic
        tier: User subscription tier
        content_types: List of content types to generate
        use_cache: Whether to use content cache (default: True)
    """
    import logging
    import sys
    logger = logging.getLogger(__name__)
    
    def flush_buffers():
        """Flush stdout and stderr buffers to ensure immediate output"""
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
    
    try:
        # Get model name and prompt version for cache key
        from content_creation_crew.schemas import PROMPT_VERSION
        # Model name will be set when crew_instance is created below
        model_name = None  # Will be set after crew_instance creation
        
        
        # Send initial status
        status_msg = json.dumps({'type': 'status', 'message': 'Initializing crew...'})
        yield f"data: {status_msg}\n\n"
        flush_buffers()
        logger.info("Sent initial status")
        
        # Check if Ollama is accessible before starting
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
                if response.status_code != 200:
                    raise Exception("Ollama is not responding correctly")
            logger.info(f"Ollama connection verified at {config.OLLAMA_BASE_URL}")
        except Exception as ollama_error:
            error_msg = json.dumps({
                'type': 'error',
                'message': f'Ollama is not accessible at {config.OLLAMA_BASE_URL}. Please ensure Ollama is running. Error: {str(ollama_error)}',
                'error_type': 'OllamaConnectionError'
            })
            yield f"data: {error_msg}\n\n"
            flush_buffers()
            logger.error(f"Ollama connection check failed: {ollama_error}")
            return
        
        # Initialize crew with tier-appropriate configuration
        crew_instance = ContentCreationCrew(tier=tier, content_types=content_types)
        crew_obj = crew_instance._build_crew(content_types=content_types)
        # Store model name for later use in validation and caching
        model_name = crew_instance._get_model_for_tier(tier)
        status_msg = json.dumps({'type': 'status', 'message': f'Crew initialized with {tier} tier. Starting research...'})
        yield f"data: {status_msg}\n\n"
        flush_buffers()
        logger.info(f"Sent crew initialized status for tier: {tier}")
        
        # Run crew in executor to avoid blocking
        # Send periodic keep-alive messages during execution to prevent Node.js timeout
        loop = asyncio.get_event_loop()
        logger.info("Starting crew execution (this may take several minutes)...")
        
        # Send initial keep-alive
        yield ": keep-alive\n\n"
        flush_buffers()
        
        # Create a wrapper that runs executor and sends keep-alive during execution
        executor_done = False
        result = None
        executor_error = None
        
        async def run_executor():
            nonlocal executor_done, result, executor_error
            try:
                # Get timeout from config (default 5 minutes)
                from content_creation_crew.config import config
                timeout_seconds = config.CREWAI_TIMEOUT
                
                logger.info(f"Starting crew kickoff for topic: {topic} (timeout: {timeout_seconds}s)")
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: crew_obj.kickoff(inputs={'topic': topic})
                    ),
                    timeout=timeout_seconds
                )
                logger.info("Crew kickoff completed successfully")
                executor_done = True
            except asyncio.TimeoutError:
                error_msg = f"Content generation timed out after {timeout_seconds} seconds"
                logger.error(f"Crew execution timed out: {error_msg}")
                executor_error = TimeoutError(error_msg)
                executor_done = True
            except KeyboardInterrupt:
                logger.warning("Crew execution interrupted by user")
                executor_error = Exception("Content generation was interrupted")
                executor_done = True
            except Exception as e:
                logger.error(f"Crew execution failed: {type(e).__name__} - {str(e)}", exc_info=True)
                executor_error = e
                executor_done = True
        
        # Start the executor task
        executor_task = asyncio.create_task(run_executor())
        
        # Send keep-alive messages every 15 seconds while executor is running
        keep_alive_count = 0
        while not executor_done:
            # Wait for either executor completion or 15 seconds (whichever comes first)
            done, pending = await asyncio.wait(
                [executor_task],
                timeout=15.0,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            if done:
                # Executor completed
                break
            else:
                # Timeout - executor still running, send keep-alive
                keep_alive_count += 1
                yield ": keep-alive\n\n"
                flush_buffers()
                logger.debug(f"Sent keep-alive #{keep_alive_count} during crew execution")
        
        # Ensure executor completed and get result
        await executor_task
        
        if executor_error:
            raise executor_error
        
        status_msg = json.dumps({'type': 'status', 'message': 'Content generation completed. Extracting content...'})
        yield f"data: {status_msg}\n\n"
        flush_buffers()
        logger.info(f"Crew execution completed. Result type: {type(result)}")
        
        # Get prompt version for validation and caching (model_name already set above)
        from content_creation_crew.schemas import PROMPT_VERSION
        
        # Extract content asynchronously with validation
        raw_content = await extract_content_async(result, topic, logger)
        
        # Validate and repair blog content
        from content_creation_crew.content_validator import validate_and_repair_content
        is_valid, validated_model, content, was_repaired = validate_and_repair_content(
            'blog', raw_content, model_name, allow_repair=True
        )
        if not is_valid:
            logger.warning("Blog content validation failed, using fallback extraction")
            content = clean_content(raw_content)
        else:
            logger.info(f"Blog content validated successfully (repaired: {was_repaired})")
        
        # Extract and validate social media content
        raw_social = await extract_social_media_content_async(result, topic, logger)
        if raw_social:
            is_valid, validated_model, social_media_content, was_repaired = validate_and_repair_content(
                'social', raw_social, model_name, allow_repair=True
            )
            if not is_valid:
                logger.warning("Social media content validation failed, using fallback extraction")
                social_media_content = clean_content(raw_social) if raw_social else ""
            else:
                logger.info(f"Social media content validated successfully (repaired: {was_repaired})")
                social_media_content = social_media_content if social_media_content else ""
        else:
            social_media_content = ""
        
        # Extract and validate audio content
        raw_audio = await extract_audio_content_async(result, topic, logger)
        if raw_audio:
            is_valid, validated_model, audio_content, was_repaired = validate_and_repair_content(
                'audio', raw_audio, model_name, allow_repair=True
            )
            if not is_valid:
                logger.warning("Audio content validation failed, using fallback extraction")
                audio_content = clean_content(raw_audio) if raw_audio else ""
            else:
                logger.info(f"Audio content validated successfully (repaired: {was_repaired})")
                audio_content = audio_content if audio_content else ""
        else:
            audio_content = ""
        
        # Extract and validate video content
        raw_video = await extract_video_content_async(result, topic, logger)
        if raw_video:
            is_valid, validated_model, video_content, was_repaired = validate_and_repair_content(
                'video', raw_video, model_name, allow_repair=True
            )
            if not is_valid:
                logger.warning("Video content validation failed, using fallback extraction")
                video_content = clean_content(raw_video) if raw_video else ""
            else:
                logger.info(f"Video content validated successfully (repaired: {was_repaired})")
                video_content = video_content if video_content else ""
        else:
            video_content = ""
        
        # Check if we have ANY content (blog, audio, video, or social media)
        # Don't fail if blog content is missing but other content types exist
        has_any_content = (
            (content and len(content.strip()) >= 10) or
            (audio_content and len(audio_content.strip()) >= 10) or
            (video_content and len(video_content.strip()) >= 10) or
            (social_media_content and len(social_media_content.strip()) >= 10)
        )
        
        if not has_any_content:
            # Last resort: try to get content from result directly
            logger.warning("Content extraction still failed, trying direct result extraction...")
            if hasattr(result, 'tasks_output') and result.tasks_output:
                last_task = result.tasks_output[-1]
                if hasattr(last_task, 'raw') and last_task.raw:
                    content = str(last_task.raw)
                elif hasattr(last_task, 'output') and last_task.output:
                    content = str(last_task.output)
                else:
                    content = str(last_task)
            
            if not content or len(content.strip()) < 10:
                content = str(result)
            
            content = clean_content(content)
            
            # Re-check after fallback
            has_any_content = (
                (content and len(content.strip()) >= 10) or
                (audio_content and len(audio_content.strip()) >= 10) or
                (video_content and len(video_content.strip()) >= 10) or
                (social_media_content and len(social_media_content.strip()) >= 10)
            )
        
        if not has_any_content:
            error_msg = json.dumps({
                'type': 'error', 
                'message': f'Content extraction failed - no valid content found for any requested content type. Blog length: {len(content) if content else 0}, Audio length: {len(audio_content) if audio_content else 0}, Video length: {len(video_content) if video_content else 0}, Social length: {len(social_media_content) if social_media_content else 0}. Check server logs for details.'
            })
            yield f"data: {error_msg}\n\n"
            logger.error(f"Content extraction failed - no valid content found. Blog: {len(content) if content else 0}, Audio: {len(audio_content) if audio_content else 0}, Video: {len(video_content) if video_content else 0}, Social: {len(social_media_content) if social_media_content else 0}")
            return
        
        # Determine primary content type for streaming
        # If audio is requested and blog is missing/empty, stream audio instead
        primary_content = content if (content and len(content.strip()) >= 10) else ""
        primary_content_type = 'blog'
        
        if content_types and 'audio' in content_types and audio_content and len(audio_content.strip()) >= 10:
            if not primary_content:
                primary_content = audio_content
                primary_content_type = 'audio'
        
        logger.info(f"Content extracted successfully. Blog length: {len(content) if content else 0}, Audio length: {len(audio_content) if audio_content else 0}")
        logger.info(f"Primary content type for streaming: {primary_content_type}, length: {len(primary_content)}")
        
        # Stream primary content in chunks for real-time display
        if primary_content:
            chunk_size = 100  # characters per chunk
            total_length = len(primary_content)
            
            logger.info(f"Starting to stream {total_length} characters in chunks of {chunk_size}")
            
            # Send content chunks with keep-alive comments to prevent timeout
            chunk_count = 0
            for i in range(0, total_length, chunk_size):
                chunk = primary_content[i:i + chunk_size]
                progress = min(100, int((i + len(chunk)) / total_length * 100))
                chunk_data = {
                    'type': 'content',
                    'chunk': chunk,
                    'progress': progress,
                    'content_type': primary_content_type  # Indicate which content type is being streamed
                }
                sse_message = f"data: {json.dumps(chunk_data)}\n\n"
                yield sse_message
                chunk_count += 1
                
                # Flush buffers every chunk to ensure immediate delivery
                if chunk_count % 5 == 0:  # Flush every 5 chunks to balance performance
                    flush_buffers()
                
                # Send keep-alive comment every 10 chunks (approximately every 0.5 seconds)
                # This prevents Node.js undici from timing out
                if chunk_count % 10 == 0:
                    yield ": keep-alive\n\n"
                    flush_buffers()
                
                if i % 500 == 0:  # Log every 5 chunks
                    logger.debug(f"Sent chunk {chunk_count}, progress: {progress}%")
                await asyncio.sleep(0.05)  # Small delay for smooth streaming
        
        # Cache the generated content for future requests
        if use_cache:
            cache = get_cache()
            cache_data = {
                'content': content,
                'social_media_content': social_media_content,
                'audio_content': audio_content,
                'video_content': video_content,
                'generated_at': datetime.now().isoformat()
            }
            cache.set(topic, cache_data, prompt_version=PROMPT_VERSION, model=model_name)
            logger.info(f"Cached content for topic: {topic} (prompt_version: {PROMPT_VERSION}, model: {model_name})")
        
        # Send completion message with full content (CRITICAL - this ensures full content is delivered)
        # Ensure JSON encoding doesn't truncate large content
        completion_data = {
            'type': 'complete',
            'content': content,  # Full content - this is the source of truth
            'social_media_content': social_media_content,  # Social media content
            'audio_content': audio_content,  # Audio content
            'video_content': video_content,  # Video content
            'topic': topic,
            'generated_at': datetime.now().isoformat(),
            'total_length': len(content),  # Include length for verification
            'social_media_length': len(social_media_content) if social_media_content else 0,
            'audio_length': len(audio_content) if audio_content else 0,
            'video_length': len(video_content) if video_content else 0,
            'cached': False,
            'prompt_version': PROMPT_VERSION,
            'model': model_name
        }
        
        # Use ensure_ascii=False to preserve all characters and ensure no truncation
        completion_json = json.dumps(completion_data, ensure_ascii=False)
        completion_msg = f"data: {completion_json}\n\n"
        
        logger.info(f"Sending completion message with FULL content, length: {len(content)}")
        logger.info(f"Completion JSON length: {len(completion_json)}")
        logger.info(f"Completion message content preview: {content[:300]}")
        
        # Verify the content wasn't truncated during JSON encoding
        decoded_check = json.loads(completion_json)
        if len(decoded_check.get('content', '')) != len(content):
            logger.error(f"Content truncation detected! Original: {len(content)}, Encoded: {len(decoded_check.get('content', ''))}")
        else:
            logger.info("✓ Content verified - no truncation in JSON encoding")
        
        yield completion_msg
        flush_buffers()
        
        # Send a final flush to ensure the message is sent
        yield "\n"  # Extra newline to ensure message is complete
        flush_buffers()
        
        logger.info("Streaming completed successfully - full content sent in completion message")
        
    except Exception as e:
        # Provide more detailed error information
        error_type = type(e).__name__
        error_message = str(e) if str(e) else "Unknown error occurred"
        
        # Check for common error types and provide helpful messages
        if "terminated" in error_message.lower() or error_type == "Terminated":
            error_message = "Content generation was terminated. This may be due to a timeout or connection issue. Please check if Ollama is running and try again."
        elif "connection" in error_message.lower() or "connect" in error_message.lower():
            error_message = f"Connection error: {error_message}. Please ensure Ollama is running at {config.OLLAMA_BASE_URL}"
        elif "timeout" in error_message.lower():
            error_message = f"Request timeout: {error_message}. The content generation took too long. Please try with a simpler topic or check server logs."
        
        error_detail = {
            'type': 'error',
            'message': error_message,
            'error_type': error_type
        }
        
        error_msg = json.dumps(error_detail)
        logger.error(f"Error in async crew execution: {error_type} - {error_message}", exc_info=True)
        yield f"data: {error_msg}\n\n"
        flush_buffers()


def extract_content_from_result(result, task_name: str = None) -> str:
    """
    Extract content directly from CrewAI result object without file I/O.
    This is faster and more reliable than waiting for files.
    
    Args:
        result: CrewAI result object
        task_name: Optional task name to look for (e.g., 'editing_task')
        
    Returns:
        Extracted content string
    """
    content = ""
    
    # Try to extract from result object directly (fastest method)
    if hasattr(result, 'tasks_output') and result.tasks_output:
        # Look for the requested task (e.g., editing task for blog, social_media task for social)
        for task in reversed(result.tasks_output):
            # Check if this is the task we're looking for
            if task_name:
                task_name_lower = task_name.lower()
                # If no description, check task name/type attributes
                if hasattr(task, 'description'):
                    task_desc = str(task.description).lower()
                    # Flexible matching: 'social' should match 'social_media', 'social_media_standalone', etc.
                    if task_name_lower == 'social':
                        # For 'social', match any task with 'social' in description
                        if 'social' not in task_desc:
                            continue
                    elif task_name_lower not in task_desc:
                        continue
                elif hasattr(task, 'name') or hasattr(task, 'task_name'):
                    # Try matching by task name/type
                    task_name_attr = str(getattr(task, 'name', getattr(task, 'task_name', ''))).lower()
                    if task_name_lower == 'social':
                        if 'social' not in task_name_attr:
                            continue
                    elif task_name_lower not in task_name_attr:
                        continue
                else:
                    # No way to identify task, skip filtering
                    pass
            
            # Try different attributes in order of preference
            if hasattr(task, 'raw') and task.raw:
                content = str(task.raw)
                if len(content.strip()) > 10:
                    return content
            elif hasattr(task, 'output') and task.output:
                content = str(task.output)
                if len(content.strip()) > 10:
                    return content
            elif hasattr(task, 'content') and task.content:
                content = str(task.content)
                if len(content.strip()) > 10:
                    return content
    
    # Fallback to result object directly (for standalone tasks or when task matching fails)
    if not content or len(content.strip()) < 10:
        # If we're looking for social media and didn't find it in tasks, try result object
        # This handles standalone social media where there's only one task
        if task_name and task_name.lower() == 'social':
            # For social, try to get the last task output (should be social media task)
            if hasattr(result, 'tasks_output') and result.tasks_output:
                last_task = result.tasks_output[-1]
                if hasattr(last_task, 'raw') and last_task.raw:
                    content = str(last_task.raw)
                elif hasattr(last_task, 'output') and last_task.output:
                    content = str(last_task.output)
                elif hasattr(last_task, 'content') and last_task.content:
                    content = str(last_task.content)
        
        # Final fallback to result object attributes
        if not content or len(content.strip()) < 10:
            if hasattr(result, 'raw') and result.raw:
                content = str(result.raw)
            elif hasattr(result, 'content') and result.content:
                content = str(result.content)
            elif hasattr(result, 'output') and result.output:
                content = str(result.output)
            else:
                content = str(result)
    
    return content


async def extract_content_async(result, topic: str, logger) -> str:
    """Extract content from result asynchronously - optimized to use result objects first"""
    content = ""
    extraction_method = None
    
    logger.debug(f"[EXTRACT] Starting blog content extraction for topic='{topic}'")
    logger.debug(f"[EXTRACT] Result type: {type(result)}, has tasks_output: {hasattr(result, 'tasks_output')}")
    
    # First, try extracting directly from result object (fastest, no I/O)
    logger.info("[EXTRACT] Attempting direct extraction from result object...")
    extract_start = time.time()
    content = extract_content_from_result(result, 'editing')
    extract_duration = time.time() - extract_start
    
    if content and len(content.strip()) > 10:
        extraction_method = "result_object"
        logger.info(f"[EXTRACT] Successfully extracted content from result object in {extract_duration:.3f}s, length={len(content)}")
        logger.debug(f"[EXTRACT] Content preview (first 200 chars): {content[:200]}...")
        return content
    
    logger.debug(f"[EXTRACT] Direct extraction result: length={len(content) if content else 0}, duration={extract_duration:.3f}s")
    
    # Fallback to file-based extraction (slower, but more reliable for some cases)
    # Removed 1-second delay - check file immediately
    logger.info("[EXTRACT] Direct extraction failed, trying file-based extraction...")
    file_extract_start = time.time()
    
    # Try reading the file multiple times (reduced attempts for faster failure)
    output_file = Path("content_output.md")
    for attempt in range(3):  # Reduced from 5 to 3 attempts for faster failure
        if output_file.exists():
            try:
                file_content = output_file.read_text(encoding='utf-8')
                if file_content and len(file_content.strip()) > 10:
                    logger.info(f"File read attempt {attempt + 1}, file length: {len(file_content)}")
                    
                    # First try: look for separator
                    if "---" in file_content:
                        parts = file_content.split("---", 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            logger.info(f"Extracted from file after separator, length: {len(content)}")
                            if len(content) > 10:
                                break
                    
                    # Second try: skip metadata lines and get actual content
                    lines = file_content.split('\n')
                    content_lines = []
                    skip_patterns = [
                        '# Content Creation:',
                        '**Generated on:**',
                        '---',
                        'I now can give a great answer',  # Common prefix
                    ]
                    
                    skip_until_content = True
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Skip empty lines at the start
                        if skip_until_content and not line_stripped:
                            continue
                        
                        # Check if this is a skip pattern
                        should_skip = False
                        for pattern in skip_patterns:
                            if pattern.lower() in line_stripped.lower():
                                should_skip = True
                                skip_until_content = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Found content - start collecting
                        skip_until_content = False
                        content_lines.append(line)
                    
                    if content_lines:
                        content = '\n'.join(content_lines).strip()
                        logger.info(f"Extracted from file (skipping metadata), length: {len(content)}")
                        if len(content) > 10:
                            break
                    
                    # Fallback: use entire file if it's substantial
                    if len(file_content.strip()) > 100:
                        content = file_content.strip()
                        logger.info(f"Using entire file content, length: {len(content)}")
                        break
                        
            except Exception as e:
                logger.warning(f"Error reading file (attempt {attempt + 1}): {e}")
        # Removed sleep delay - check immediately for faster failure
        if attempt < 2:  # Only wait between attempts, not after last attempt
            await asyncio.sleep(0.05)  # OPTIMIZATION: Reduced from 0.2s to 0.05s for faster retries (75% reduction)
    
    # Final fallback: extract from result object (should have been tried first, but just in case)
    if not content or len(content.strip()) < 10:
        logger.warning("[EXTRACT] File content empty or too short, retrying result object extraction")
        fallback_start = time.time()
        content = extract_content_from_result(result, 'editing')
        fallback_duration = time.time() - fallback_start
        if content and len(content.strip()) > 10:
            extraction_method = "result_object_fallback"
            logger.info(f"[EXTRACT] Fallback extraction succeeded in {fallback_duration:.3f}s, length={len(content)}")
        else:
            logger.error(f"[EXTRACT] Fallback extraction also failed, duration={fallback_duration:.3f}s")
    
    file_extract_duration = time.time() - file_extract_start if 'file_extract_start' in locals() else 0
    extraction_method = extraction_method or "file_based"
    
    logger.info(f"[EXTRACT] Final extraction result: method={extraction_method}, length={len(content) if content else 0}, total_duration={file_extract_duration:.3f}s")
    if content:
        logger.debug(f"[EXTRACT] Content preview (first 300 chars): {content[:300]}...")
    else:
        logger.error("[EXTRACT] No content extracted - extraction failed completely")
    
    return content


async def extract_social_media_content_async(result, topic: str, logger) -> str:
    """Extract social media content from result asynchronously - optimized"""
    logger.debug(f"[EXTRACT_SOCIAL] Starting social media extraction, result type: {type(result)}")
    
    # First try direct extraction from result object
    # Try 'social' first (handles both regular and standalone tasks with flexible matching)
    content = extract_content_from_result(result, 'social')
    
    # If that fails, try 'social_media' (for standalone task)
    if not content or len(content.strip()) < 10:
        logger.debug("[EXTRACT_SOCIAL] 'social' extraction failed, trying 'social_media'")
        content = extract_content_from_result(result, 'social_media')
    
    if content and len(content.strip()) > 10:
        logger.info(f"[EXTRACT_SOCIAL] Successfully extracted social media content from result object, length: {len(content)}")
        logger.debug(f"[EXTRACT_SOCIAL] Content preview: {content[:200]}")
        return content
    else:
        logger.warning(f"[EXTRACT_SOCIAL] Failed to extract from result object, content length: {len(content) if content else 0}, will try file-based extraction")
    
    # Fallback to file-based extraction (removed 1s delay for faster extraction)
    # Try reading the social media output file
    output_file = Path("social_media_output.md")
    for attempt in range(3):  # Reduced from 10 to 3 attempts for faster failure
        if output_file.exists():
            try:
                file_content = output_file.read_text(encoding='utf-8')
                if file_content and len(file_content.strip()) > 10:
                    logger.info(f"Social media file read attempt {attempt + 1}, file length: {len(file_content)}")
                    
                    # First try: look for separator
                    if "---" in file_content:
                        parts = file_content.split("---", 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            logger.info(f"Extracted social media from file after separator, length: {len(content)}")
                            if len(content) > 10:
                                break
                    
                    # Second try: skip metadata lines and get actual content
                    lines = file_content.split('\n')
                    content_lines = []
                    skip_patterns = [
                        '# Social Media',
                        '**Generated on:**',
                        '---',
                        'I now can give a great answer',
                    ]
                    
                    skip_until_content = True
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Skip empty lines at the start
                        if skip_until_content and not line_stripped:
                            continue
                        
                        # Check if this is a skip pattern
                        should_skip = False
                        for pattern in skip_patterns:
                            if pattern.lower() in line_stripped.lower():
                                should_skip = True
                                skip_until_content = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Found content - start collecting
                        skip_until_content = False
                        content_lines.append(line)
                    
                    if content_lines:
                        content = '\n'.join(content_lines).strip()
                        logger.info(f"Extracted social media from file (skipping metadata), length: {len(content)}")
                        if len(content) > 10:
                            break
                    
                    # Fallback: use entire file if it's substantial
                    if len(file_content.strip()) > 50:
                        content = file_content.strip()
                        logger.info(f"Using entire social media file content, length: {len(content)}")
                        break
                        
            except Exception as e:
                logger.warning(f"Error reading social media file (attempt {attempt + 1}): {e}")
        # Removed sleep delay - check immediately for faster failure
        if attempt < 2:  # Only wait between attempts, not after last attempt
            await asyncio.sleep(0.05)  # OPTIMIZATION: Reduced from 0.2s to 0.05s for faster retries (75% reduction)
    
    # Final fallback: extract from result object (try both 'social' and 'social_media')
    if not content or len(content.strip()) < 10:
        logger.info("[EXTRACT_SOCIAL] Social media file content empty, using result object extraction")
        content = extract_content_from_result(result, 'social')
        # If that fails, try 'social_media' (for standalone task)
        if not content or len(content.strip()) < 10:
            logger.debug("[EXTRACT_SOCIAL] 'social' extraction failed, trying 'social_media'")
            content = extract_content_from_result(result, 'social_media')
        
        # If still no content, try extracting from result object directly (for standalone tasks)
        if not content or len(content.strip()) < 10:
            logger.debug("[EXTRACT_SOCIAL] Task-based extraction failed, trying direct result object extraction")
            if hasattr(result, 'tasks_output') and result.tasks_output:
                # Try to get content from the last task (should be social media task for standalone)
                last_task = result.tasks_output[-1]
                if hasattr(last_task, 'raw') and last_task.raw:
                    content = str(last_task.raw)
                elif hasattr(last_task, 'output') and last_task.output:
                    content = str(last_task.output)
                elif hasattr(last_task, 'content') and last_task.content:
                    content = str(last_task.content)
            
            # Final fallback: try result object attributes directly
            if not content or len(content.strip()) < 10:
                if hasattr(result, 'raw') and result.raw:
                    content = str(result.raw)
                elif hasattr(result, 'content') and result.content:
                    content = str(result.content)
                elif hasattr(result, 'output') and result.output:
                    content = str(result.output)
    
    logger.info(f"[EXTRACT_SOCIAL] Final extracted social media content length: {len(content) if content else 0}")
    if content and len(content.strip()) > 10:
        logger.info(f"[EXTRACT_SOCIAL] Social media content preview: {content[:200]}")
    else:
        logger.error(f"[EXTRACT_SOCIAL] Failed to extract social media content - result type: {type(result)}, has tasks_output: {hasattr(result, 'tasks_output')}")
        if hasattr(result, 'tasks_output') and result.tasks_output:
            logger.error(f"[EXTRACT_SOCIAL] tasks_output length: {len(result.tasks_output)}")
            for i, task in enumerate(result.tasks_output):
                logger.error(f"[EXTRACT_SOCIAL] Task {i}: type={type(task)}, has raw={hasattr(task, 'raw')}, has output={hasattr(task, 'output')}, has content={hasattr(task, 'content')}")
    
    return content


async def extract_audio_content_async(result, topic: str, logger) -> str:
    """Extract audio content from result asynchronously - optimized"""
    # First try direct extraction from result object
    content = extract_content_from_result(result, 'audio')
    
    if content and len(content.strip()) > 10:
        logger.info(f"Successfully extracted audio content from result object, length: {len(content)}")
        return content
    
    # Fallback to file-based extraction (removed 1s delay for faster extraction)
    # Try reading the audio output file
    output_file = Path("audio_output.md")
    for attempt in range(3):  # Reduced from 10 to 3 attempts for faster failure
        if output_file.exists():
            try:
                file_content = output_file.read_text(encoding='utf-8')
                if file_content and len(file_content.strip()) > 10:
                    logger.info(f"Audio file read attempt {attempt + 1}, file length: {len(file_content)}")
                    
                    # First try: look for separator
                    if "---" in file_content:
                        parts = file_content.split("---", 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            logger.info(f"Extracted audio from file after separator, length: {len(content)}")
                            if len(content) > 10:
                                break
                    
                    # Second try: skip metadata lines and get actual content
                    lines = file_content.split('\n')
                    content_lines = []
                    skip_patterns = [
                        '# Audio',
                        '**Generated on:**',
                        '---',
                        'I now can give a great answer',
                    ]
                    
                    skip_until_content = True
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Skip empty lines at the start
                        if skip_until_content and not line_stripped:
                            continue
                        
                        # Check if this is a skip pattern
                        should_skip = False
                        for pattern in skip_patterns:
                            if pattern.lower() in line_stripped.lower():
                                should_skip = True
                                skip_until_content = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Found content - start collecting
                        skip_until_content = False
                        content_lines.append(line)
                    
                    if content_lines:
                        content = '\n'.join(content_lines).strip()
                        logger.info(f"Extracted audio from file (skipping metadata), length: {len(content)}")
                        if len(content) > 10:
                            break
                    
                    # Fallback: use entire file if it's substantial
                    if len(file_content.strip()) > 50:
                        content = file_content.strip()
                        logger.info(f"Using entire audio file content, length: {len(content)}")
                        break
                        
            except Exception as e:
                logger.warning(f"Error reading audio file (attempt {attempt + 1}): {e}")
        # Removed sleep delay - check immediately for faster failure
        if attempt < 2:  # Only wait between attempts, not after last attempt
            await asyncio.sleep(0.05)  # OPTIMIZATION: Reduced from 0.2s to 0.05s for faster retries (75% reduction)
    
    # Final fallback: extract from result object
    if not content or len(content.strip()) < 10:
        logger.info("Audio file content empty, using result object extraction")
        content = extract_content_from_result(result, 'audio')
    
    logger.info(f"Final extracted audio content length: {len(content) if content else 0}")
    if content:
        logger.info(f"Audio content preview: {content[:200]}")
    
    return content


async def extract_video_content_async(result, topic: str, logger) -> str:
    """Extract video content from result asynchronously - optimized"""
    # First try direct extraction from result object
    content = extract_content_from_result(result, 'video')
    
    if content and len(content.strip()) > 10:
        logger.info(f"Successfully extracted video content from result object, length: {len(content)}")
        return content
    
    # Fallback to file-based extraction (removed 1s delay for faster extraction)
    # Try reading the video output file
    output_file = Path("video_output.md")
    for attempt in range(3):  # Reduced from 10 to 3 attempts for faster failure
        if output_file.exists():
            try:
                file_content = output_file.read_text(encoding='utf-8')
                if file_content and len(file_content.strip()) > 10:
                    logger.info(f"Video file read attempt {attempt + 1}, file length: {len(file_content)}")
                    
                    # First try: look for separator
                    if "---" in file_content:
                        parts = file_content.split("---", 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            logger.info(f"Extracted video from file after separator, length: {len(content)}")
                            if len(content) > 10:
                                break
                    
                    # Second try: skip metadata lines and get actual content
                    lines = file_content.split('\n')
                    content_lines = []
                    skip_patterns = [
                        '# Video',
                        '**Generated on:**',
                        '---',
                        'I now can give a great answer',
                    ]
                    
                    skip_until_content = True
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Skip empty lines at the start
                        if skip_until_content and not line_stripped:
                            continue
                        
                        # Check if this is a skip pattern
                        should_skip = False
                        for pattern in skip_patterns:
                            if pattern.lower() in line_stripped.lower():
                                should_skip = True
                                skip_until_content = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Found content - start collecting
                        skip_until_content = False
                        content_lines.append(line)
                    
                    if content_lines:
                        content = '\n'.join(content_lines).strip()
                        logger.info(f"Extracted video from file (skipping metadata), length: {len(content)}")
                        if len(content) > 10:
                            break
                    
                    # Fallback: use entire file if it's substantial
                    if len(file_content.strip()) > 50:
                        content = file_content.strip()
                        logger.info(f"Using entire video file content, length: {len(content)}")
                        break
                        
            except Exception as e:
                logger.warning(f"Error reading video file (attempt {attempt + 1}): {e}")
        # Removed sleep delay - check immediately for faster failure
        if attempt < 2:  # Only wait between attempts, not after last attempt
            await asyncio.sleep(0.05)  # OPTIMIZATION: Reduced from 0.2s to 0.05s for faster retries (75% reduction)
    
    # Final fallback: extract from result object
    if not content or len(content.strip()) < 10:
        logger.info("Video file content empty, using result object extraction")
        content = extract_content_from_result(result, 'video')
    
    logger.info(f"Final extracted video content length: {len(content) if content else 0}")
    if content:
        logger.info(f"Video content preview: {content[:200]}")
    
    return content


def clean_content(content: str) -> str:
    """Clean up content by removing common prefixes"""
    if not content:
        return ""
    
    lines = content.split('\n')
    cleaned_lines = []
    skip_prefixes = [
        "your final answer must be",
        "i now can give a great answer",
        "here is the",
    ]
    skip_next = False
    for line in lines:
        line_lower = line.strip().lower()
        if any(line_lower.startswith(prefix) for prefix in skip_prefixes):
            skip_next = True
            continue
        if skip_next and not line.strip():
            skip_next = False
            continue
        skip_next = False
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()


@app.post("/api/generate")
async def generate_content(
    request: TopicRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate content for a given topic using the Content Creation Crew
    Returns a streaming response with progress updates
    
    Backward compatibility: This endpoint internally creates a ContentJob
    and streams its progress. For new integrations, use POST /v1/content/generate
    and GET /v1/content/jobs/{id}/stream instead.
    
    Tier-based access control:
    - Free tier: Blog content only, limited generations
    - Basic tier: Blog + Social media, more generations
    - Pro tier: All content types, unlimited generations
    - Enterprise: All features + priority processing
    """
    from content_creation_crew.streaming_utils import FlushingAsyncGenerator
    from content_creation_crew.services.content_service import ContentService
    
    if not request.topic or not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")
    
    topic = request.topic.strip()
    logger.info(f"Received streaming request for topic: {topic} from user {current_user.id}")
    
    # Initialize PlanPolicy for tier enforcement
    policy = PlanPolicy(db, current_user)
    plan = policy.get_plan()
    logger.info(f"User {current_user.id} is on {plan} plan")
    
    # Determine content types based on plan and request
    requested_content_types = request.content_types or []
    
    # Validate content type access for each requested type
    valid_content_types = []
    for content_type in requested_content_types:
        # Check if plan supports content type
        if not policy.check_content_type_access(content_type):
            logger.warning(f"User {current_user.id} does not have access to {content_type} on {plan} plan")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "content_type_not_available",
                    "message": f"{content_type.capitalize()} content is not available on your current plan ({plan}).",
                    "content_type": content_type,
                    "plan": plan
                }
            )
        
        # Enforce monthly limit (raises HTTPException if exceeded)
        try:
            policy.enforce_monthly_limit(content_type)
            valid_content_types.append(content_type)
        except HTTPException:
            raise  # Re-raise HTTPException from enforce_monthly_limit
    
    # If no content types specified, use plan defaults
    if not valid_content_types:
        tier_config = policy.get_tier_config()
        if tier_config:
            valid_content_types = tier_config.get('content_types', ['blog'])
        else:
            valid_content_types = ['blog']  # Default to blog only
    
    # Enforce limits for default content types
    for content_type in valid_content_types:
        try:
            policy.enforce_monthly_limit(content_type)
        except HTTPException:
            raise  # Re-raise HTTPException from enforce_monthly_limit
    
    # Create job internally for persistence (backward compatibility)
    content_service = ContentService(db, current_user)
    try:
        job = content_service.create_job(
            topic=topic,
            content_types=valid_content_types
        )
        logger.info(f"Created job {job.id} for backward-compatible /api/generate endpoint")
    except HTTPException as e:
        # If job already exists (idempotency), get it
        if e.status_code == 409:
            # Extract job_id from error detail if available
            job_id = e.detail.get('job_id') if isinstance(e.detail, dict) else None
            if job_id:
                job = content_service.get_job(job_id)
                if job and job.status == 'completed':
                    # Job already completed, stream from artifacts
                    logger.info(f"Job {job_id} already completed, streaming from artifacts")
                    # Fall through to streaming logic below
                else:
                    raise e
            else:
                raise e
        else:
            raise e
    
    # Start generation asynchronously (don't wait)
    from content_creation_crew.content_routes import run_generation_async
    asyncio.create_task(
        run_generation_async(job.id, topic, valid_content_types, plan, current_user.id)
    )
    
    # Stream job progress (backward compatible format)
    async def stream_job_progress():
        """Stream job progress in backward-compatible format"""
        # Send initial status
        yield f"data: {json.dumps({'type': 'status', 'message': 'Job created, starting generation...', 'job_id': job.id})}\n\n"
        
        # Poll for job updates and artifacts
        last_status = job.status
        artifacts_received = set()
        
        while True:
            # Refresh job from database
            db.refresh(job)
            
            # Check for status changes
            if job.status != last_status:
                if job.status == 'completed':
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Generation completed'})}\n\n"
                elif job.status == 'failed':
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Generation failed'})}\n\n"
                    break
                last_status = job.status
            
            # Check for new artifacts
            artifacts = db.query(ContentArtifact).filter(
                ContentArtifact.job_id == job.id
            ).all()
            
            for artifact in artifacts:
                if artifact.id not in artifacts_received:
                    artifacts_received.add(artifact.id)
                    # Send artifact in backward-compatible format
                    if artifact.type == 'blog':
                        yield f"data: {json.dumps({'type': 'content', 'chunk': artifact.content_text[:100] if artifact.content_text else ''})}\n\n"
                    elif artifact.type == 'social':
                        yield f"data: {json.dumps({'type': 'status', 'message': 'Social media content ready'})}\n\n"
                    elif artifact.type == 'audio':
                        yield f"data: {json.dumps({'type': 'status', 'message': 'Audio content ready'})}\n\n"
                    elif artifact.type == 'video':
                        yield f"data: {json.dumps({'type': 'status', 'message': 'Video content ready'})}\n\n"
            
            # If completed, send final completion message
            if job.status == 'completed':
                # Get all artifacts
                all_artifacts = db.query(ContentArtifact).filter(
                    ContentArtifact.job_id == job.id
                ).all()
                
                completion_data = {
                    'type': 'complete',
                    'content': '',
                    'social_media_content': '',
                    'audio_content': '',
                    'video_content': '',
                    'topic': topic,
                    'generated_at': job.finished_at.isoformat() if job.finished_at else datetime.now().isoformat(),
                    'job_id': job.id
                }
                
                for artifact in all_artifacts:
                    if artifact.content_text:
                        if artifact.type == 'blog':
                            completion_data['content'] = artifact.content_text
                        elif artifact.type == 'social':
                            completion_data['social_media_content'] = artifact.content_text
                        elif artifact.type == 'audio':
                            completion_data['audio_content'] = artifact.content_text
                        elif artifact.type == 'video':
                            completion_data['video_content'] = artifact.content_text
                
                yield f"data: {json.dumps(completion_data)}\n\n"
                break
            
            # Wait before next poll
            await asyncio.sleep(0.5)
    
    # Wrap the generator with flushing capability
    streaming_generator = FlushingAsyncGenerator(
        stream_job_progress(),
        flush_interval=5
    )
    
    return StreamingResponse(
        streaming_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "X-Content-Type-Options": "nosniff",
        }
    )


if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Log startup information
    logger.info("=" * 50)
    logger.info("Content Creation Crew API - Starting Up")
    logger.info("=" * 50)
    logger.info(f"Environment: {config.ENV}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.getenv('PYTHONPATH', 'NOT SET')}")
    logger.info(f"PORT: {config.PORT}")
    logger.info(f"DATABASE_URL: {'SET (PostgreSQL)' if config.DATABASE_URL.startswith('postgresql') else 'SET (SQLite)' if config.DATABASE_URL.startswith('sqlite') else 'NOT SET'}")
    logger.info(f"OLLAMA_BASE_URL: {config.OLLAMA_BASE_URL}")
    logger.info(f"Build Version: {config.BUILD_VERSION}")
    logger.info(f"Build Commit: {config.BUILD_COMMIT}")
    
    # Configure Python to use unbuffered output for better streaming
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(line_buffering=True)
    
    # Test critical imports with timeout to prevent hanging
    try:
        logger.info("Testing critical imports...")
        import signal
        import threading
        
        import_result = [None]
        import_exception = [None]
        
        def _import_target():
            try:
                import content_creation_crew
                import_result[0] = True
            except Exception as e:
                import_exception[0] = e
        
        import_thread = threading.Thread(target=_import_target, daemon=True)
        import_thread.start()
        import_thread.join(timeout=10.0)  # 10 second timeout for imports
        
        if import_thread.is_alive():
            logger.error("✗ Import timed out after 10 seconds - possible database connection hang")
            logger.error("Check DATABASE_URL in Railway Variables - may be using 'db' hostname")
            sys.exit(1)
        elif import_exception[0]:
            logger.error(f"✗ Failed to import content_creation_crew: {import_exception[0]}", exc_info=True)
            sys.exit(1)
        else:
            logger.info("✓ content_creation_crew imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import content_creation_crew: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info(f"Starting Content Creation Crew API server on port {config.PORT}")
    logger.info(f"Health check endpoint: http://0.0.0.0:{config.PORT}/health")
    logger.info(f"Meta endpoint: http://0.0.0.0:{config.PORT}/meta")
    logger.info("=" * 50)
    
    # Configure uvicorn to disable buffering for streaming
    try:
        # Force unbuffered output for Railway
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Create a simple log config for uvicorn that outputs to stdout
        uvicorn_log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "access": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["access"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
        
        uvicorn.run(
            app,
            host="0.0.0.0",  # Listen on all interfaces (required for Railway)
            port=config.PORT,
            log_config=uvicorn_log_config,  # Use explicit log config for Railway
            access_log=True,
            use_colors=False,  # Disable colors for Railway logs
            loop="asyncio",
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)

