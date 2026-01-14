"""
Request Size Limit Middleware
Enforces global request body size limits to prevent abuse and memory pressure
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.datastructures import Headers
from typing import Callable

from ..exceptions import ErrorResponse
from ..logging_config import get_request_id

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce request body size limits
    
    Features:
    - Configurable size limits for different content types
    - Fast rejection before reading entire body
    - Excludes GET/HEAD/OPTIONS methods (no body)
    - Returns standardized error response
    
    Usage:
        app.add_middleware(
            RequestSizeLimitMiddleware,
            max_request_bytes=2_000_000,  # 2MB
            max_upload_bytes=10_000_000   # 10MB for file uploads
        )
    """
    
    def __init__(
        self,
        app,
        max_request_bytes: int = 2_000_000,  # 2MB default
        max_upload_bytes: int = 10_000_000,  # 10MB for uploads
    ):
        super().__init__(app)
        self.max_request_bytes = max_request_bytes
        self.max_upload_bytes = max_upload_bytes
        
        logger.info(
            f"✓ Request size limits: "
            f"max_request={self.max_request_bytes / 1_000_000:.1f}MB, "
            f"max_upload={self.max_upload_bytes / 1_000_000:.1f}MB"
        )
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Check request size before processing"""
        
        # Skip methods without request body
        if request.method in ["GET", "HEAD", "OPTIONS", "DELETE"]:
            return await call_next(request)
        
        # Get Content-Length header
        content_length = request.headers.get("content-length")
        
        if content_length is None:
            # No Content-Length header - proceed but may fail later if too large
            # Some clients don't send Content-Length for chunked encoding
            return await call_next(request)
        
        try:
            content_length_int = int(content_length)
        except ValueError:
            # Invalid Content-Length header
            error_response = ErrorResponse.create(
                message="Invalid Content-Length header",
                code="INVALID_CONTENT_LENGTH",
                status_code=400,
                request_id=get_request_id()
            )
            return JSONResponse(
                content=error_response.dict(),
                status_code=400
            )
        
        # Determine size limit based on content type
        content_type = request.headers.get("content-type", "").lower()
        
        # Check if this is a file upload endpoint
        is_upload = (
            "multipart/form-data" in content_type or
            "/upload" in request.url.path or
            "/artifacts" in request.url.path
        )
        
        max_size = self.max_upload_bytes if is_upload else self.max_request_bytes
        
        # Check if request exceeds limit
        if content_length_int > max_size:
            size_mb = content_length_int / 1_000_000
            limit_mb = max_size / 1_000_000
            
            logger.warning(
                f"Request size limit exceeded: {size_mb:.2f}MB > {limit_mb:.2f}MB "
                f"(path: {request.url.path}, method: {request.method})"
            )
            
            error_response = ErrorResponse.create(
                message=f"Request body too large. Maximum allowed size is {limit_mb:.1f}MB, but received {size_mb:.2f}MB.",
                code="REQUEST_TOO_LARGE",
                status_code=413,
                request_id=get_request_id(),
                details={
                    "max_size_bytes": max_size,
                    "max_size_mb": limit_mb,
                    "received_bytes": content_length_int,
                    "received_mb": round(size_mb, 2)
                }
            )
            
            # Return 413 Payload Too Large
            return JSONResponse(
                content=error_response.dict(),
                status_code=413,
                headers={
                    "Retry-After": "60",  # Suggest retry after 60 seconds
                    "X-RateLimit-Limit": str(max_size),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Request is within size limit, proceed
        return await call_next(request)


class StreamingRequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Alternative middleware that reads request body in chunks
    
    More accurate but slightly slower for detecting oversized requests.
    Use this if you need to handle chunked transfer encoding without Content-Length.
    
    Note: This is more resource-intensive as it needs to read the body.
    """
    
    def __init__(
        self,
        app,
        max_request_bytes: int = 2_000_000,
        chunk_size: int = 64 * 1024  # 64KB chunks
    ):
        super().__init__(app)
        self.max_request_bytes = max_request_bytes
        self.chunk_size = chunk_size
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Read request body in chunks to enforce size limit"""
        
        # Skip methods without request body
        if request.method in ["GET", "HEAD", "OPTIONS", "DELETE"]:
            return await call_next(request)
        
        # Try Content-Length header first (fast path)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_request_bytes:
                    error_response = ErrorResponse.create(
                        message=f"Request body too large. Maximum allowed size is {self.max_request_bytes / 1_000_000:.1f}MB.",
                        code="REQUEST_TOO_LARGE",
                        status_code=413,
                        request_id=get_request_id()
                    )
                    return JSONResponse(content=error_response.dict(), status_code=413)
            except ValueError:
                pass
        
        # If no Content-Length or need to verify, read in chunks
        # This ensures we catch oversized chunked requests
        total_size = 0
        chunks = []
        
        try:
            async for chunk in request.stream():
                total_size += len(chunk)
                
                if total_size > self.max_request_bytes:
                    logger.warning(f"Streaming request exceeded size limit: {total_size} > {self.max_request_bytes}")
                    
                    error_response = ErrorResponse.create(
                        message=f"Request body too large. Maximum allowed size is {self.max_request_bytes / 1_000_000:.1f}MB.",
                        code="REQUEST_TOO_LARGE",
                        status_code=413,
                        request_id=get_request_id()
                    )
                    return JSONResponse(content=error_response.dict(), status_code=413)
                
                chunks.append(chunk)
        
        except Exception as e:
            logger.error(f"Error reading request body: {e}")
            error_response = ErrorResponse.create(
                message="Failed to read request body",
                code="REQUEST_READ_ERROR",
                status_code=400,
                request_id=get_request_id()
            )
            return JSONResponse(content=error_response.dict(), status_code=400)
        
        # Reconstruct request with collected chunks
        # Note: This approach is more complex and not recommended for production
        # The Content-Length check is sufficient for most cases
        
        return await call_next(request)


def get_human_readable_size(bytes_size: int) -> str:
    """
    Convert bytes to human-readable size
    
    Args:
        bytes_size: Size in bytes
    
    Returns:
        Human-readable string (e.g., "1.5MB")
    """
    if bytes_size < 1024:
        return f"{bytes_size}B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f}KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f}MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.1f}GB"

