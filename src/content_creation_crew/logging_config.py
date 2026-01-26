"""
Structured logging configuration with request ID and environment labels
"""
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def get_request_id() -> Optional[str]:
    """Get current request ID from context"""
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to each request"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Set in context
        request_id_var.set(request_id)
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class StructuredFormatter(logging.Formatter):
    """Custom formatter that includes request ID and environment"""
    
    def __init__(self, env: str = "dev", fmt: str = None, datefmt: str = None):
        self.env = env
        # Default format if not provided
        if fmt is None:
            fmt = "%(asctime)s [%(env)s] [%(request_id)s] %(levelname)-8s %(name)s: %(message)s"
        if datefmt is None:
            datefmt = "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt=fmt, datefmt=datefmt)
    
    def format(self, record: logging.LogRecord) -> str:
        # Add request ID if available
        request_id = get_request_id()
        if request_id:
            record.request_id = request_id
        else:
            record.request_id = "-"
        
        # Add environment
        record.env = self.env
        
        # Format message
        return super().format(record)


def setup_logging(env: str = "dev", log_level: str = "INFO"):
    """
    Set up structured logging with request ID and environment labels
    
    Args:
        env: Environment name (dev, staging, prod)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter with environment
    # Format: timestamp [ENV] [REQUEST_ID] level logger message
    format_string = "%(asctime)s [%(env)s] [%(request_id)s] %(levelname)-8s %(name)s: %(message)s"
    formatter = StructuredFormatter(env=env, fmt=format_string, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler with immediate flushing
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    
    # Force immediate flushing for Railway
    if hasattr(console_handler.stream, 'reconfigure'):
        try:
            console_handler.stream.reconfigure(line_buffering=True)
        except Exception:
            pass
    
    # Add handler
    root_logger.addHandler(console_handler)
    
    # Set levels for third-party loggers (but allow INFO for uvicorn)
    logging.getLogger("uvicorn").setLevel(logging.INFO)  # Changed from WARNING for Railway visibility
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)  # Changed from WARNING for Railway visibility
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Force flush after setup
    sys.stdout.flush()
    sys.stderr.flush()
    
    return root_logger

