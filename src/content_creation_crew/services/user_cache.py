"""
User data caching service for faster authentication and tier checks
"""
import time
from typing import Optional, Dict
from datetime import datetime, timedelta


class UserCache:
    """In-memory cache for user data to reduce database queries"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        """
        Initialize user cache
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.cache: Dict[int, Dict] = {}
        self.default_ttl = default_ttl
    
    def get(self, user_id: int) -> Optional[Dict]:
        """
        Get cached user data
        
        Args:
            user_id: User ID
            
        Returns:
            Cached user data dict or None if not found/expired
        """
        if user_id not in self.cache:
            return None
        
        cached_item = self.cache[user_id]
        
        # Check if expired
        if time.time() > cached_item['expires_at']:
            # Remove expired entry
            del self.cache[user_id]
            return None
        
        return cached_item['data']
    
    def set(self, user_id: int, data: Dict, ttl: int = None):
        """
        Cache user data
        
        Args:
            user_id: User ID
            data: User data dict (tier, subscription info, etc.)
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        
        self.cache[user_id] = {
            'data': data,
            'expires_at': expires_at,
            'cached_at': time.time()
        }
    
    def invalidate(self, user_id: int):
        """
        Invalidate cached user data
        
        Args:
            user_id: User ID
        """
        if user_id in self.cache:
            del self.cache[user_id]
    
    def clear(self):
        """Clear all cached user data"""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Remove all expired entries from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.cache.items()
            if current_time > value['expires_at']
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        self.cleanup_expired()
        return {
            'total_entries': len(self.cache),
            'default_ttl': self.default_ttl
        }


# Global cache instance
_cache_instance: Optional[UserCache] = None


def get_user_cache() -> UserCache:
    """
    Get global user cache instance
    
    Returns Redis-backed cache if Redis is available, otherwise in-memory cache
    """
    global _cache_instance
    if _cache_instance is None:
        # Try Redis first, fall back to in-memory
        try:
            from .redis_cache import RedisUserCache
            redis_cache = RedisUserCache()
            if redis_cache.use_redis:
                _cache_instance = redis_cache
            else:
                _cache_instance = UserCache()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize Redis user cache: {e}, using in-memory cache")
            _cache_instance = UserCache()
    return _cache_instance

