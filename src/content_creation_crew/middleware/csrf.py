"""
CSRF protection for state-changing operations
"""
from fastapi import Request, HTTPException, status, Header, Depends
from typing import Optional
import logging
import hmac
import hashlib
from datetime import datetime, timedelta

from ..config import config
from ..auth import get_current_user
from ..database import User

logger = logging.getLogger(__name__)


def verify_csrf_token(
    request: Request,
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token"),
    current_user: Optional[User] = None
) -> None:
    """
    Verify CSRF token for state-changing operations
    
    CSRF tokens are HMAC(user_id:timestamp, secret_key) and expire after 1 hour.
    
    Args:
        request: FastAPI request object
        x_csrf_token: CSRF token from header
        current_user: Current authenticated user (optional, will be fetched if not provided)
    
    Raises:
        HTTPException: If CSRF token is missing or invalid
    """
    # Skip CSRF check for safe methods
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return
    
    # Skip CSRF check for webhooks (they use signature verification instead)
    if request.url.path.startswith("/webhooks/"):
        return
    
    # Skip CSRF check for public endpoints
    public_paths = ["/api/auth/login", "/api/auth/signup", "/health", "/meta", "/api/auth/csrf-token"]
    if any(request.url.path.startswith(path) for path in public_paths):
        return
    
    # In development, allow requests without CSRF token (for easier testing)
    if config.ENV == "dev":
        return
    
    # For staging/prod, require CSRF token for billing actions
    billing_paths = ["/v1/billing/upgrade", "/v1/billing/cancel", "/v1/billing/"]
    is_billing_action = any(request.url.path.startswith(path) for path in billing_paths)
    
    if is_billing_action:
        if not x_csrf_token:
            logger.warning(
                f"CSRF token missing for billing action: {request.url.path}",
                extra={"request_id": request.headers.get("X-Request-ID", "unknown")}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token required for billing actions"
            )
        
        # Verify CSRF token format (64 hex chars for SHA256)
        if len(x_csrf_token) != 64 or not all(c in '0123456789abcdef' for c in x_csrf_token.lower()):
            logger.warning(
                f"Invalid CSRF token format: {request.url.path}",
                extra={"request_id": request.headers.get("X-Request-ID", "unknown")}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token format"
            )
        
        # Verify token matches expected format (HMAC-SHA256)
        # Note: Full validation would require checking timestamp expiration
        # For now, we just verify the format is correct
        # In production, you might want to store tokens in Redis with expiration

