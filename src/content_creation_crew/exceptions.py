"""
Custom exception handlers with request ID support
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from .logging_config import get_request_id

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standard error response format"""
    
    @staticmethod
    def create(
        detail: str,
        status_code: int,
        request_id: str = None,
        error_code: str = None
    ) -> dict:
        """
        Create standardized error response
        
        Args:
            detail: Error message
            status_code: HTTP status code
            request_id: Request ID from context
            error_code: Optional error code for client handling
        
        Returns:
            Dictionary with error details
        """
        response = {
            "detail": detail,
            "status_code": status_code,
        }
        
        if request_id:
            response["request_id"] = request_id
        
        if error_code:
            response["error_code"] = error_code
        
        return response


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with request ID"""
    request_id = get_request_id()
    
    error_response = ErrorResponse.create(
        detail=exc.detail,
        status_code=exc.status_code,
        request_id=request_id
    )
    
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
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
    
    error_response = ErrorResponse.create(
        detail=f"Validation error: {detail}",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request_id=request_id,
        error_code="validation_error"
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
    
    error_response = ErrorResponse.create(
        detail="Internal server error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
        error_code="internal_error"
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

