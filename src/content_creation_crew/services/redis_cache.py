"""
Redis cache implementations with in-memory fallback
Provides Redis-backed caching for content and user data
"""
import json
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import redis, but don't fail if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - using in-memory cache fallback")


def get_redis_client() -> Optional[Any]:
    """
    Get Redis client if available and configured
    
    Returns:
        Redis client instance or None if Redis not available
    """
    if not REDIS_AVAILABLE:
        return None
    
    from ..config import config
    
    if not config.REDIS_URL:
        return None
    
    try:
        # Parse Redis URL
        import urllib.parse
        parsed = urllib.parse.urlparse(config.REDIS_URL)
        
        client = redis.Redis(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            password=parsed.password,
            db=int(parsed.path.lstrip('/')) if parsed.path else 0,
            decode_responses=True,  # Automatically decode responses to strings
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30
        )
        
        # Test connection
        client.ping()
        logger.info(f"Redis connection established: {config.REDIS_URL}")
        return client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
        return None


class RedisContentCache:
    """
    Redis-backed content cache with in-memory fallback
    
    Implements the same interface as ContentCache but uses Redis for storage
    """
    
    def __init__(self, default_ttl: int = 3600, redis_client: Optional[Any] = None):
        """
        Initialize Redis content cache
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 1 hour)
            redis_client: Optional Redis client (auto-created if not provided)
        """
        self.default_ttl = default_ttl
        self.redis_client = redis_client or get_redis_client()
        self.use_redis = self.redis_client is not None
        
        # Fallback to in-memory cache
        if not self.use_redis:
            from .content_cache import ContentCache
            self.fallback_cache = ContentCache(default_ttl=default_ttl)
            logger.info("Using in-memory content cache (Redis not available)")
        else:
            self.fallback_cache = None
            logger.info("Using Redis content cache")
    
    def get_cache_key(self, topic: str, content_types: list = None, prompt_version: str = None, model: str = None, moderation_version: str = None) -> str:
        """Generate cache key (same logic as ContentCache) with moderation version (M6)"""
        from ..schemas import PROMPT_VERSION
        from ..config import config
        
        normalized_topic = topic.lower().strip()
        normalized_types = sorted(content_types or ['blog'])
        prompt_version = prompt_version or PROMPT_VERSION
        model = model or ""
        
        # Add moderation_version to cache key (M6)
        moderation_version = moderation_version or config.MODERATION_VERSION
        
        cache_string = f"{normalized_topic}:{':'.join(normalized_types)}:{prompt_version}:{model}:{moderation_version}"
        import hashlib
        return f"content:{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    def get(self, topic: str, content_types: list = None, prompt_version: str = None, model: str = None) -> Optional[Dict]:
        """Get cached content"""
        if not self.use_redis:
            return self.fallback_cache.get(topic, content_types, prompt_version, model)
        
        try:
            key = self.get_cache_key(topic, content_types, prompt_version, model)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning(f"Redis get failed: {e}, falling back to in-memory")
            if self.fallback_cache:
                return self.fallback_cache.get(topic, content_types, prompt_version, model)
            return None
    
    def set(self, topic: str, content_data: Dict, ttl: int = None, prompt_version: str = None, model: str = None):
        """Cache content"""
        if not self.use_redis:
            return self.fallback_cache.set(topic, content_data, ttl, prompt_version, model)
        
        try:
            key = self.get_cache_key(topic, content_types=None, prompt_version=prompt_version, model=model)
            # Determine content types from content_data
            content_types = []
            if content_data.get('social_media_content'):
                content_types.append('social')
            if content_data.get('audio_content'):
                content_types.append('audio')
            if content_data.get('video_content'):
                content_types.append('video')
            if not content_types:
                content_types = ['blog']
            
            key = self.get_cache_key(topic, content_types, prompt_version, model)
            ttl = ttl or self.default_ttl
            
            # Store in Redis with TTL
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(content_data, default=str)
            )
        except Exception as e:
            logger.warning(f"Redis set failed: {e}, falling back to in-memory")
            if self.fallback_cache:
                self.fallback_cache.set(topic, content_data, ttl, prompt_version, model)
    
    def clear(self, topic: str = None, content_types: list = None, prompt_version: str = None, model: str = None):
        """Clear cache entry"""
        if not self.use_redis:
            return self.fallback_cache.clear(topic, content_types, prompt_version, model)
        
        try:
            if topic is None:
                # Clear all content cache keys
                keys = self.redis_client.keys("content:*")
                if keys:
                    self.redis_client.delete(*keys)
            else:
                key = self.get_cache_key(topic, content_types, prompt_version, model)
                self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}, falling back to in-memory")
            if self.fallback_cache:
                self.fallback_cache.clear(topic, content_types, prompt_version, model)
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.use_redis:
            return self.fallback_cache.get_stats() if self.fallback_cache else {}
        
        try:
            keys = self.redis_client.keys("content:*")
            return {
                'total_entries': len(keys),
                'default_ttl': self.default_ttl,
                'backend': 'redis'
            }
        except Exception as e:
            logger.warning(f"Redis stats failed: {e}")
            return {
                'total_entries': 0,
                'default_ttl': self.default_ttl,
                'backend': 'redis (error)'
            }


class RedisUserCache:
    """
    Redis-backed user cache with in-memory fallback
    
    Implements the same interface as UserCache but uses Redis for storage
    """
    
    def __init__(self, default_ttl: int = 300, redis_client: Optional[Any] = None):
        """
        Initialize Redis user cache
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
            redis_client: Optional Redis client (auto-created if not provided)
        """
        self.default_ttl = default_ttl
        self.redis_client = redis_client or get_redis_client()
        self.use_redis = self.redis_client is not None
        
        # Fallback to in-memory cache
        if not self.use_redis:
            from .user_cache import UserCache
            self.fallback_cache = UserCache(default_ttl=default_ttl)
            logger.info("Using in-memory user cache (Redis not available)")
        else:
            self.fallback_cache = None
            logger.info("Using Redis user cache")
    
    def _get_key(self, user_id: int) -> str:
        """Generate Redis key for user"""
        return f"user:{user_id}"
    
    def get(self, user_id: int) -> Optional[Dict]:
        """Get cached user data"""
        if not self.use_redis:
            return self.fallback_cache.get(user_id)
        
        try:
            key = self._get_key(user_id)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning(f"Redis get failed: {e}, falling back to in-memory")
            if self.fallback_cache:
                return self.fallback_cache.get(user_id)
            return None
    
    def set(self, user_id: int, data: Dict, ttl: int = None):
        """Cache user data"""
        if not self.use_redis:
            return self.fallback_cache.set(user_id, data, ttl)
        
        try:
            key = self._get_key(user_id)
            ttl = ttl or self.default_ttl
            
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning(f"Redis set failed: {e}, falling back to in-memory")
            if self.fallback_cache:
                self.fallback_cache.set(user_id, data, ttl)
    
    def invalidate(self, user_id: int):
        """Invalidate cached user data"""
        if not self.use_redis:
            return self.fallback_cache.invalidate(user_id)
        
        try:
            key = self._get_key(user_id)
            self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis invalidate failed: {e}, falling back to in-memory")
            if self.fallback_cache:
                self.fallback_cache.invalidate(user_id)
    
    def clear(self):
        """Clear all cached user data"""
        if not self.use_redis:
            return self.fallback_cache.clear()
        
        try:
            keys = self.redis_client.keys("user:*")
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}, falling back to in-memory")
            if self.fallback_cache:
                self.fallback_cache.clear()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.use_redis:
            return self.fallback_cache.get_stats() if self.fallback_cache else {}
        
        try:
            keys = self.redis_client.keys("user:*")
            return {
                'total_entries': len(keys),
                'default_ttl': self.default_ttl,
                'backend': 'redis'
            }
        except Exception as e:
            logger.warning(f"Redis stats failed: {e}")
            return {
                'total_entries': 0,
                'default_ttl': self.default_ttl,
                'backend': 'redis (error)'
            }

