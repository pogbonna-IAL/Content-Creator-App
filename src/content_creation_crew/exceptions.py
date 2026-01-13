"""
Custom exception handlers with request ID support
Standardized error response format: { code, message, details?, request_id }
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Optional, Dict, Any

from .logging_config import get_request_id

logger = logging.getLogger(__name__)


class ErrorResponse:
    """
    Standard error response format
    
    Schema: { code, message, details?, request_id }
    """
    
    @staticmethod
    def create(
        message: str,
        code: str,
        status_code: int,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        use_legacy_format: bool = False
    ) -> dict:
        """
        Create standardized error response
        
        Args:
            message: Human-readable error message
            code: Error code (e.g., "VALIDATION_ERROR", "AUTH_ERROR", "PLAN_LIMIT_EXCEEDED")
            status_code: HTTP status code
            request_id: Request ID from context (auto-fetched if None)
            details: Optional additional error details
            use_legacy_format: If True, use legacy format for backward compatibility
        
        Returns:
            Dictionary with error details
        """
        # Get request_id if not provided
        if request_id is None:
            request_id = get_request_id()
        
        if use_legacy_format:
            # Legacy format for /api endpoints (backward compatibility)
            response = {
                "detail": message,
                "status_code": status_code,
            }
            if request_id:
                response["request_id"] = request_id
            if code:
                response["error_code"] = code
            if details:
                response.update(details)
        else:
            # Standardized format for /v1 endpoints
            response = {
                "code": code,
                "message": message,
                "status_code": status_code,
            }
            
            if request_id:
                response["request_id"] = request_id
            
            if details:
                response["details"] = details
        
        return response


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with request ID"""
    request_id = get_request_id()
    
    # Determine error code based on status code
    error_code_map = {
        400: "BAD_REQUEST",
        401: "AUTH_ERROR",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    # Parse detail to extract error information
    detail = exc.detail
    error_message = str(detail) if detail else f"HTTP {exc.status_code} error"
    error_details = None
    
    # Check if detail is a dict (plan limit errors, etc.)
    if isinstance(detail, dict):
        # Extract message and details from dict
        error_message = detail.get("message", str(detail))
        error_code_from_detail = detail.get("error", error_code)
        
        # Check for plan limit error
        if error_code_from_detail == "PLAN_LIMIT_EXCEEDED":
            error_code = "PLAN_LIMIT_EXCEEDED"
            error_details = {
                "content_type": detail.get("content_type"),
                "used": detail.get("used"),
                "limit": detail.get("limit"),
                "plan": detail.get("plan")
            }
        # Check for content blocked error
        elif error_code_from_detail == "CONTENT_BLOCKED" or detail.get("code") == "CONTENT_BLOCKED":
            error_code = "CONTENT_BLOCKED"
            error_details = {
                "reason_code": detail.get("reason_code"),
                **{k: v for k, v in detail.get("details", {}).items()}
            }
        else:
            # Use error code from detail if available
            error_code = error_code_from_detail
            # Include other fields as details
            error_details = {k: v for k, v in detail.items() if k not in ["error", "message", "code"]}
    else:
        # Check if this is a plan limit error (from string detail)
        detail_str = str(detail) if detail else ""
        if "PLAN_LIMIT_EXCEEDED" in detail_str or "plan limit" in detail_str.lower():
            error_code = "PLAN_LIMIT_EXCEEDED"
        
        # Check if this is an auth error
        if exc.status_code == 401:
            error_code = "AUTH_ERROR"
    
    # Determine if legacy format needed (for /api endpoints)
    use_legacy_format = request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v1/")
    
    error_response = ErrorResponse.create(
        message=error_message,
        code=error_code,
        status_code=exc.status_code,
        request_id=request_id,
        details=error_details,
        use_legacy_format=use_legacy_format
    )
    
    logger.warning(
        f"HTTP {exc.status_code}: {detail}",
        extra={"request_id": request_id, "path": request.url.path}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation exceptions with request ID"""
    request_id = get_request_id()
    
    errors = exc.errors()
    error_messages = [f"{err['loc']}: {err['msg']}" for err in errors]
    detail = "; ".join(error_messages)
    
    # Determine if legacy format needed (for /api endpoints)
    use_legacy_format = request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v1/")
    
    error_response = ErrorResponse.create(
        message=f"Validation error: {detail}",
        code="VALIDATION_ERROR",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request_id=request_id,
        details={"errors": errors},
        use_legacy_format=use_legacy_format
    )
    
    logger.warning(
        f"Validation error: {detail}",
        extra={"request_id": request_id, "path": request.url.path, "errors": errors}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions with request ID"""
    request_id = get_request_id()
    
    # Determine if legacy format needed (for /api endpoints)
    use_legacy_format = request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v1/")
    
    # Don't expose internal error details in production
    from .config import config
    error_message = "Internal server error"
    error_details = None
    
    if config.ENV == "dev":
        error_message = f"Internal server error: {str(exc)}"
        error_details = {"exception_type": type(exc).__name__}
    
    error_response = ErrorResponse.create(
        message=error_message,
        code="INTERNAL_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
        details=error_details,
        use_legacy_format=use_legacy_format
    )
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={"request_id": request_id, "path": request.url.path}
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )

