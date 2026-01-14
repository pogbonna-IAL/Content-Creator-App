"""
Error Handler Middleware
Sanitizes error responses to prevent information leakage (M3)
"""
import logging
import traceback
import re
from typing import Optional, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError, DatabaseError
from pydantic import ValidationError

from ..exceptions import ErrorResponse
from ..logging_config import get_request_id

logger = logging.getLogger(__name__)


class ErrorSanitizer:
    """
    Sanitizes error responses to prevent information leakage
    
    Features:
    - Removes file paths from error messages
    - Hides SQL statements and connection strings
    - Sanitizes stack traces
    - Preserves request_id for debugging
    """
    
    # Patterns to redact from error messages
    PATH_PATTERN = re.compile(r'(?:[A-Z]:\\|/)[^\s\'"<>|]+')  # File paths
    SQL_PATTERN = re.compile(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|GRANT|REVOKE)\s+.*', re.IGNORECASE)
    CONNECTION_PATTERN = re.compile(r'(postgresql|mysql|mongodb)://[^\s\'"<>]+')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    @classmethod
    def sanitize_message(cls, message: str) -> str:
        """
        Sanitize error message to remove sensitive information
        
        Args:
            message: Original error message
        
        Returns:
            Sanitized message safe for API response
        """
        if not message:
            return "An error occurred"
        
        # Remove file paths
        message = cls.PATH_PATTERN.sub('[REDACTED_PATH]', message)
        
        # Remove SQL statements
        message = cls.SQL_PATTERN.sub('SQL statement [REDACTED]', message)
        
        # Remove connection strings
        message = cls.CONNECTION_PATTERN.sub('[REDACTED_CONNECTION]', message)
        
        # Remove emails (additional safety)
        message = cls.EMAIL_PATTERN.sub('[REDACTED_EMAIL]', message)
        
        # Limit message length (prevent verbose error dumps)
        if len(message) > 500:
            message = message[:500] + "... [truncated]"
        
        return message
    
    @classmethod
    def sanitize_details(cls, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize details dict to remove sensitive information
        
        Args:
            details: Original details dict
        
        Returns:
            Sanitized details safe for API response
        """
        if not details:
            return {}
        
        sanitized = {}
        
        for key, value in details.items():
            # Skip potentially sensitive keys
            if key.lower() in ['password', 'token', 'secret', 'api_key', 'connection_string']:
                continue
            
            # Sanitize string values
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_message(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_details(value)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = [
                    cls.sanitize_message(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                # Numbers, booleans, None - safe to include
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def is_safe_error(cls, error: Exception) -> bool:
        """
        Check if error is safe to expose details
        
        Args:
            error: Exception instance
        
        Returns:
            True if error details are safe to expose
        """
        # Validation errors are generally safe (field-level)
        if isinstance(error, (RequestValidationError, ValidationError)):
            return True
        
        # HTTP exceptions with explicit status codes are usually safe
        if isinstance(error, StarletteHTTPException) and error.status_code < 500:
            return True
        
        # Everything else should be sanitized
        return False


async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database errors with sanitization
    
    Prevents leakage of:
    - SQL statements
    - Connection strings
    - Database schema information
    - Internal file paths
    """
    request_id = get_request_id()
    
    # Log full error details for debugging
    logger.error(
        f"Database error (request_id: {request_id}): {type(exc).__name__}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Determine specific error type for better user feedback
    if isinstance(exc, IntegrityError):
        # Constraint violations (e.g., duplicate key)
        error_message = "Database constraint violation. The operation could not be completed."
        error_code = "DATABASE_CONSTRAINT_ERROR"
    elif isinstance(exc, OperationalError):
        # Connection issues, timeouts
        error_message = "Database connection error. Please try again later."
        error_code = "DATABASE_CONNECTION_ERROR"
    else:
        # Generic database error
        error_message = "A database error occurred. Please try again later."
        error_code = "DATABASE_ERROR"
    
    error_response = ErrorResponse.create(
        message=error_message,
        code=error_code,
        status_code=500,
        request_id=request_id,
        details={
            "error_type": type(exc).__name__
            # NO SQL statements, connection strings, or internal details
        }
    )
    
    return JSONResponse(
        content=error_response.dict(),
        status_code=500
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle validation errors with safe field-level information
    
    Includes:
    - Field names that failed validation
    - Safe validation error messages
    
    Excludes:
    - Full request payload
    - Internal validation logic
    """
    request_id = get_request_id()
    
    # Log validation error for debugging
    logger.warning(
        f"Validation error (request_id: {request_id}): {exc.errors()}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Extract safe field-level errors
    safe_errors = []
    for error in exc.errors():
        # Get field location (e.g., ['body', 'email'])
        loc = error.get('loc', [])
        field = '.'.join(str(l) for l in loc if l != 'body')
        
        # Get safe error message (sanitize if needed)
        msg = error.get('msg', 'Validation error')
        msg = ErrorSanitizer.sanitize_message(msg)
        
        safe_errors.append({
            "field": field,
            "message": msg,
            "type": error.get('type', 'value_error')
        })
    
    error_response = ErrorResponse.create(
        message="Request validation failed. Please check your input.",
        code="VALIDATION_ERROR",
        status_code=422,
        request_id=request_id,
        details={
            "errors": safe_errors
        }
    )
    
    return JSONResponse(
        content=error_response.dict(),
        status_code=422
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with sanitization
    
    For 4xx errors: Include specific message (usually safe)
    For 5xx errors: Generic message only
    """
    request_id = get_request_id()
    
    # Log error with appropriate level
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code} error (request_id: {request_id}): {exc.detail}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
    else:
        logger.warning(
            f"HTTP {exc.status_code} error (request_id: {request_id}): {exc.detail}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
    
    # For 5xx errors, sanitize message
    if exc.status_code >= 500:
        message = "Internal server error. Please try again later."
        code = "INTERNAL_ERROR"
    else:
        # 4xx errors: sanitize but keep informative
        message = ErrorSanitizer.sanitize_message(str(exc.detail))
        code = f"HTTP_{exc.status_code}"
    
    error_response = ErrorResponse.create(
        message=message,
        code=code,
        status_code=exc.status_code,
        request_id=request_id
    )
    
    return JSONResponse(
        content=error_response.dict(),
        status_code=exc.status_code
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all uncaught exceptions with full sanitization
    
    This is the last line of defense - catches everything else
    """
    request_id = get_request_id()
    
    # Log full exception details for debugging
    logger.error(
        f"Unhandled exception (request_id: {request_id}): {type(exc).__name__}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
    )
    
    # Generic safe message for user
    error_response = ErrorResponse.create(
        message="An unexpected error occurred. Please try again later.",
        code="INTERNAL_ERROR",
        status_code=500,
        request_id=request_id,
        details={
            "error_type": type(exc).__name__
            # NO exception message, stack trace, or internal details
        }
    )
    
    return JSONResponse(
        content=error_response.dict(),
        status_code=500
    )


def get_safe_exception_info(exc: Exception) -> Dict[str, Any]:
    """
    Extract safe information from exception for logging
    
    Args:
        exc: Exception instance
    
    Returns:
        Dict with safe information for logging (PII already redacted by logging filter)
    """
    return {
        "type": type(exc).__name__,
        "message": str(exc),  # PII will be redacted by logging filter
        "traceback": traceback.format_exc()  # Full trace for logs only
    }


def should_include_details(status_code: int, error_code: str) -> bool:
    """
    Determine if error details should be included in response
    
    Args:
        status_code: HTTP status code
        error_code: Application error code
    
    Returns:
        True if details are safe to include
    """
    # Never include details for 5xx errors
    if status_code >= 500:
        return False
    
    # Include details for client errors (4xx) but only safe ones
    if status_code >= 400:
        safe_codes = [
            "VALIDATION_ERROR",
            "AUTHENTICATION_REQUIRED",
            "PERMISSION_DENIED",
            "NOT_FOUND",
            "REQUEST_TOO_LARGE",
            "RATE_LIMITED",
            "PLAN_LIMIT_EXCEEDED"
        ]
        return error_code in safe_codes
    
    return False

