"""
Security middleware for request size limits and CSRF protection
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Maximum request body size (10MB for generation endpoints)
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size"""
    
    def __init__(self, app, max_size: int = MAX_REQUEST_SIZE):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content-length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    logger.warning(
                        f"Request size limit exceeded: {size} bytes (max: {self.max_size})",
                        extra={"request_id": request.headers.get("X-Request-ID", "unknown")}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request body too large. Maximum size: {self.max_size / 1024 / 1024:.1f}MB"
                    )
            except ValueError:
                # Invalid content-length, let it through (will be caught by body reading)
                pass
        
        # Process request
        response = await call_next(request)
        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing operations"""
    
    # Safe methods that don't require CSRF protection
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    
    # Endpoints that don't require CSRF protection (webhooks, public APIs)
    EXCLUDED_PATHS = {
        "/api/auth/login",
        "/api/auth/signup",
        "/api/auth/logout",
        "/webhooks/",
        "/health",
        "/meta",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF check for safe methods
        if request.method in self.SAFE_METHODS:
            return await call_next(request)
        
        # Skip CSRF check for excluded paths
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)
        
        # For state-changing operations, check Origin/Referer header
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        
        # Get allowed origins from config
        from ..config import config
        allowed_origins = config.CORS_ORIGINS
        
        # Extract origin from referer if origin header is missing
        if not origin and referer:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass
        
        # Check if origin matches allowed origins
        if origin:
            # Normalize origins for comparison
            origin_normalized = origin.rstrip("/")
            allowed_normalized = [o.rstrip("/") for o in allowed_origins]
            
            if origin_normalized not in allowed_normalized:
                logger.warning(
                    f"CSRF check failed: origin {origin} not in allowed origins",
                    extra={"request_id": request.headers.get("X-Request-ID", "unknown")}
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF validation failed"
                )
        
        return await call_next(request)

