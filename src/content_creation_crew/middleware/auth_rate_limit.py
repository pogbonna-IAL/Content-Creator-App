"""
Authentication-Specific Rate Limiting
Stricter limits for authentication endpoints to prevent brute force attacks
"""
import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import time

logger = logging.getLogger(__name__)


class AuthRateLimiter:
    """
    Rate limiter specifically for authentication endpoints
    
    Implements stricter limits than general API rate limiting to prevent:
    - Brute force login attacks
    - Account enumeration
    - Registration spam
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize auth rate limiter
        
        Args:
            redis_client: Redis client for distributed rate limiting (optional)
        """
        self.redis = redis_client
        if self.redis is None:
            # Try to get Redis client
            try:
                from ..services.redis_cache import get_redis_client
                self.redis = get_redis_client()
            except ImportError:
                logger.warning("Redis not available, auth rate limiting will use in-memory fallback")
                self._in_memory_limits = {}
    
    def _get_identifier(self, request: Request) -> str:
        """
        Get rate limit identifier (IP address + endpoint)
        
        Args:
            request: FastAPI request
        
        Returns:
            Identifier string
        """
        # Use X-Forwarded-For if behind proxy, otherwise client host
        ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
        endpoint = request.url.path
        return f"{ip}:{endpoint}"
    
    async def check_rate_limit(
        self,
        request: Request,
        max_attempts: int = 5,
        window_seconds: int = 900  # 15 minutes
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit
        
        Args:
            request: FastAPI request
            max_attempts: Maximum attempts within window
            window_seconds: Time window in seconds
        
        Returns:
            Tuple of (allowed: bool, retry_after: Optional[int])
        """
        identifier = self._get_identifier(request)
        key = f"auth_rate_limit:{identifier}"
        
        try:
            if self.redis:
                # Use Redis
                current = self.redis.get(key)
                
                if current is None:
                    # First attempt
                    self.redis.setex(key, window_seconds, "1")
                    return True, None
                
                attempts = int(current)
                
                if attempts >= max_attempts:
                    # Rate limit exceeded
                    ttl = self.redis.ttl(key)
                    retry_after = max(ttl, 60)  # At least 60 seconds
                    logger.warning(f"Auth rate limit exceeded for {identifier} ({attempts}/{max_attempts})")
                    return False, retry_after
                
                # Increment attempts
                self.redis.incr(key)
                return True, None
                
            else:
                # In-memory fallback
                now = time.time()
                
                if identifier not in self._in_memory_limits:
                    self._in_memory_limits[identifier] = {
                        "attempts": 1,
                        "window_start": now
                    }
                    return True, None
                
                limit_data = self._in_memory_limits[identifier]
                window_start = limit_data["window_start"]
                
                # Check if window expired
                if now - window_start > window_seconds:
                    # Reset window
                    self._in_memory_limits[identifier] = {
                        "attempts": 1,
                        "window_start": now
                    }
                    return True, None
                
                # Check attempts
                attempts = limit_data["attempts"]
                
                if attempts >= max_attempts:
                    # Rate limit exceeded
                    retry_after = int(window_seconds - (now - window_start))
                    logger.warning(f"Auth rate limit exceeded for {identifier} ({attempts}/{max_attempts})")
                    return False, retry_after
                
                # Increment attempts
                limit_data["attempts"] += 1
                return True, None
                
        except Exception as e:
            logger.error(f"Error checking auth rate limit: {e}")
            # Fail open - allow request if rate limit check fails
            return True, None
    
    async def __call__(self, request: Request):
        """
        Middleware call - check rate limit
        
        Args:
            request: FastAPI request
        
        Raises:
            HTTPException: If rate limit exceeded
        """
        allowed, retry_after = await self.check_rate_limit(request)
        
        if not allowed:
            # Return standardized error response
            from ..exceptions import ErrorResponse
            from ..logging_config import get_request_id
            
            error_response = ErrorResponse.create(
                message=f"Too many authentication attempts. Please try again in {retry_after} seconds.",
                code="AUTH_RATE_LIMITED",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                request_id=get_request_id(),
                details={
                    "retry_after": retry_after,
                    "limit": 5,  # Hardcoded for now, could be configurable
                    "window_seconds": 900
                }
            )
            
            # Track auth rate limit metric
            try:
                from ..services.metrics import increment_counter
                increment_counter("auth_rate_limited_total", labels={"endpoint": request.url.path})
            except ImportError:
                pass
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_response,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": "5",
                    "X-RateLimit-Window": "900"
                }
            )


# Singleton instance
_auth_rate_limiter: Optional[AuthRateLimiter] = None


def get_auth_rate_limiter() -> AuthRateLimiter:
    """
    Get or create auth rate limiter singleton
    
    Returns:
        AuthRateLimiter instance
    """
    global _auth_rate_limiter
    
    if _auth_rate_limiter is None:
        _auth_rate_limiter = AuthRateLimiter()
    
    return _auth_rate_limiter

