"""
Rate limiting middleware using Redis token bucket algorithm
Falls back to in-memory rate limiting if Redis not available
"""
import time
import logging
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.redis_cache import get_redis_client
from ..config import config

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm
    
    Rate limits are applied per user/organization based on their subscription tier
    """
    
    def __init__(self, app, redis_client=None):
        """
        Initialize rate limit middleware
        
        Args:
            app: FastAPI application
            redis_client: Optional Redis client (auto-created if not provided)
        """
        super().__init__(app)
        self.redis_client = redis_client or get_redis_client()
        self.use_redis = self.redis_client is not None
        
        # In-memory fallback for rate limiting
        self.memory_buckets: dict = {}
        
        # Rate limits per tier (requests per minute)
        # Can be overridden by RATE_LIMIT_RPM env var (applies to all tiers)
        base_rpm = config.RATE_LIMIT_RPM
        self.tier_limits = {
            'free': max(10, base_rpm // 6),      # Default: 10 requests per minute (or base_rpm/6)
            'basic': max(30, base_rpm // 2),     # Default: 30 requests per minute (or base_rpm/2)
            'pro': max(100, base_rpm),           # Default: 100 requests per minute (or base_rpm)
            'enterprise': max(500, base_rpm * 5)  # Default: 500 requests per minute (or base_rpm*5)
        }
        
        # Generation-specific rate limit (for /v1/content/generate endpoint)
        self.generate_rpm = config.RATE_LIMIT_GENERATE_RPM
        
        # SSE connection limit per user
        self.sse_connection_limit = config.RATE_LIMIT_SSE_CONNECTIONS
        
        # Token bucket configuration
        self.bucket_size_multiplier = 2  # Bucket can hold 2x the rate limit
        self.refill_rate = 60  # Refill every 60 seconds
    
    def _get_rate_limit_key(self, identifier: str) -> str:
        """Generate Redis key for rate limit bucket"""
        return f"ratelimit:{identifier}"
    
    def _get_memory_bucket(self, identifier: str, limit: int) -> Tuple[int, float]:
        """
        Get in-memory token bucket state
        
        Returns:
            Tuple of (tokens, last_refill_time)
        """
        if identifier not in self.memory_buckets:
            bucket_size = limit * self.bucket_size_multiplier
            self.memory_buckets[identifier] = {
                'tokens': bucket_size,
                'last_refill': time.time(),
                'limit': limit
            }
        
        bucket = self.memory_buckets[identifier]
        return bucket['tokens'], bucket['last_refill']
    
    def _refill_memory_bucket(self, identifier: str, limit: int) -> int:
        """Refill in-memory token bucket and return current tokens"""
        bucket = self.memory_buckets.get(identifier)
        if not bucket:
            bucket_size = limit * self.bucket_size_multiplier
            self.memory_buckets[identifier] = {
                'tokens': bucket_size,
                'last_refill': time.time(),
                'limit': limit
            }
            return bucket_size
        
        current_time = time.time()
        time_passed = current_time - bucket['last_refill']
        
        # Refill tokens based on time passed
        if time_passed >= self.refill_rate:
            # Full refill
            bucket_size = limit * self.bucket_size_multiplier
            bucket['tokens'] = bucket_size
            bucket['last_refill'] = current_time
        else:
            # Partial refill
            tokens_to_add = int((time_passed / self.refill_rate) * limit)
            bucket['tokens'] = min(
                bucket['tokens'] + tokens_to_add,
                limit * self.bucket_size_multiplier
            )
            bucket['last_refill'] = current_time
        
        return bucket['tokens']
    
    def _consume_memory_token(self, identifier: str, limit: int) -> bool:
        """Consume a token from in-memory bucket"""
        tokens = self._refill_memory_bucket(identifier, limit)
        
        if tokens > 0:
            self.memory_buckets[identifier]['tokens'] -= 1
            return True
        return False
    
    def _check_redis_rate_limit(self, identifier: str, limit: int) -> Tuple[bool, int, int]:
        """
        Check rate limit using Redis token bucket
        
        Returns:
            Tuple of (allowed, remaining_tokens, reset_after_seconds)
        """
        if not self.use_redis:
            return self._check_memory_rate_limit(identifier, limit)
        
        try:
            key = self._get_rate_limit_key(identifier)
            bucket_size = limit * self.bucket_size_multiplier
            
            # Use Redis Lua script for atomic token bucket operations
            lua_script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local bucket_size = tonumber(ARGV[2])
            local refill_rate = tonumber(ARGV[3])
            local now = tonumber(ARGV[4])
            
            local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
            local tokens = tonumber(bucket[1]) or bucket_size
            local last_refill = tonumber(bucket[2]) or now
            
            -- Refill tokens
            local time_passed = now - last_refill
            if time_passed >= refill_rate then
                tokens = bucket_size
                last_refill = now
            else
                local tokens_to_add = math.floor((time_passed / refill_rate) * limit)
                tokens = math.min(tokens + tokens_to_add, bucket_size)
                last_refill = now
            end
            
            -- Consume token if available
            local allowed = 0
            if tokens > 0 then
                tokens = tokens - 1
                allowed = 1
            end
            
            -- Update bucket
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
            redis.call('EXPIRE', key, refill_rate * 2)
            
            -- Calculate reset time
            local reset_after = refill_rate - (now - last_refill)
            if reset_after < 0 then
                reset_after = 0
            end
            
            return {allowed, tokens, reset_after}
            """
            
            current_time = int(time.time())
            result = self.redis_client.eval(
                lua_script,
                1,
                key,
                limit,
                bucket_size,
                self.refill_rate,
                current_time
            )
            
            allowed = bool(result[0])
            remaining = int(result[1])
            reset_after = int(result[2])
            
            return allowed, remaining, reset_after
            
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}, falling back to in-memory")
            return self._check_memory_rate_limit(identifier, limit)
    
    def _check_memory_rate_limit(self, identifier: str, limit: int) -> Tuple[bool, int, int]:
        """
        Check rate limit using in-memory token bucket
        
        Returns:
            Tuple of (allowed, remaining_tokens, reset_after_seconds)
        """
        tokens = self._refill_memory_bucket(identifier, limit)
        allowed = self._consume_memory_token(identifier, limit)
        
        bucket = self.memory_buckets[identifier]
        reset_after = max(0, self.refill_rate - (time.time() - bucket['last_refill']))
        
        return allowed, bucket['tokens'], int(reset_after)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and apply rate limiting
        """
        # Skip rate limiting for health checks, metrics, and static files
        if request.url.path in ['/health', '/meta', '/', '/metrics', '/v1/metrics']:
            return await call_next(request)
        
        # Check for SSE connection limit (for /v1/content/jobs/{id}/stream)
        if '/stream' in request.url.path:
            # SSE connection limit check would go here
            # For now, we'll use the same rate limiting as regular requests
            pass
        
        # Get user identifier (user_id or org_id)
        identifier = None
        limit = self.tier_limits['free']  # Default to free tier limit
        
        # Check if this is a generation endpoint (use stricter limit)
        is_generation_endpoint = request.url.path in [
            '/v1/content/generate',
            '/api/generate',
            '/api/generate/stream'
        ]
        
        # Try to get user from request state (set by auth middleware)
        # Note: Auth middleware may not have run yet, so we check after response
        user = None
        identifier = None
        
        # Check if user is authenticated (from auth dependency)
        # This is a best-effort check - rate limiting happens before auth in middleware order
        if hasattr(request.state, 'user') and request.state.user:
            user = request.state.user
            identifier = f"user:{user.id}"
            
            # Get user's tier/plan for rate limit (unless generation endpoint)
            if not is_generation_endpoint:
                try:
                    from ..database import get_db
                    from ..services.plan_policy import PlanPolicy
                    db_gen = get_db()
                    db = next(db_gen)
                    try:
                        policy = PlanPolicy(db, user)
                        plan = policy.get_plan()
                        limit = self.tier_limits.get(plan, self.tier_limits['free'])
                    finally:
                        db.close()
                except Exception as e:
                    logger.debug(f"Failed to get user plan for rate limiting: {e}, using free tier limit")
                    limit = self.tier_limits['free']
        
        # Generation endpoints always use generation-specific limit (regardless of tier)
        if is_generation_endpoint:
            limit = self.generate_rpm
        
        # Fallback to IP-based rate limiting if no user
        if not identifier:
            identifier = f"ip:{request.client.host}"
            limit = self.tier_limits['free']
        
        # Check rate limit
        allowed, remaining, reset_after = self._check_redis_rate_limit(identifier, limit)
        
        # Add rate limit headers
        response = await call_next(request) if allowed else None
        
        if not allowed:
            # Track rate limit metric
            try:
                from ..services.metrics import increment_counter
                increment_counter("rate_limited_total", labels={"route": request.url.path, "method": request.method})
            except ImportError:
                pass
            
            # Use ErrorResponse format with RATE_LIMITED error code
            from ..exceptions import ErrorResponse
            from ..logging_config import get_request_id
            
            request_id = get_request_id()
            
            # Determine if legacy format needed (for /api endpoints)
            use_legacy_format = request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v1/")
            
            error_response = ErrorResponse.create(
                message=f"Rate limit exceeded. Limit: {limit} requests per minute.",
                code="RATE_LIMITED",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                request_id=request_id,
                details={
                    "limit": limit,
                    "reset_after_seconds": reset_after,
                    "retry_after": reset_after
                },
                use_legacy_format=use_legacy_format
            )
            
            # For legacy format, add fields at top level
            if use_legacy_format:
                error_response["limit"] = limit
                error_response["reset_after_seconds"] = reset_after
                error_response["retry_after"] = reset_after
            
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error_response,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset-After": str(reset_after),
                    "Retry-After": str(reset_after)
                }
            )
        else:
            # Add rate limit headers to successful responses
            if response is None:
                response = await call_next(request)
            
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset-After"] = str(reset_after)
        
        return response

