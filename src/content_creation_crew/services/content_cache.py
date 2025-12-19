"""
Content caching service for faster content generation
"""
import hashlib
import json
import time
from typing import Optional, Dict
from datetime import datetime, timedelta


class ContentCache:
    """In-memory cache for generated content"""
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize content cache
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 1 hour)
        """
        self.cache: Dict[str, Dict] = {}
        self.default_ttl = default_ttl
    
    def get_cache_key(self, topic: str, content_types: list = None) -> str:
        """
        Generate cache key from topic and content types
        
        Args:
            topic: Content topic
            content_types: List of content types requested
            
        Returns:
            MD5 hash of normalized topic and content types
        """
        # Normalize topic (lowercase, strip whitespace)
        normalized_topic = topic.lower().strip()
        
        # Sort content types for consistent hashing
        normalized_types = sorted(content_types or ['blog'])
        
        # Create cache key from topic and content types
        cache_string = f"{normalized_topic}:{':'.join(normalized_types)}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def get(self, topic: str, content_types: list = None) -> Optional[Dict]:
        """
        Get cached content for topic and content types
        
        Args:
            topic: Content topic
            content_types: List of content types requested
            
        Returns:
            Cached content dict with 'content', 'social_media_content', etc.
            or None if not found or expired
        """
        key = self.get_cache_key(topic, content_types)
        
        if key not in self.cache:
            return None
        
        cached_item = self.cache[key]
        
        # Check if expired
        if time.time() > cached_item['expires_at']:
            # Remove expired entry
            del self.cache[key]
            return None
        
        # Return cached content (without expiration metadata)
        return {
            'content': cached_item.get('content', ''),
            'social_media_content': cached_item.get('social_media_content', ''),
            'audio_content': cached_item.get('audio_content', ''),
            'video_content': cached_item.get('video_content', ''),
            'topic': cached_item.get('topic', topic),
            'generated_at': cached_item.get('generated_at', ''),
            'cached': True
        }
    
    def set(self, topic: str, content_data: Dict, ttl: int = None):
        """
        Cache content for topic
        
        Args:
            topic: Content topic
            content_data: Dict with 'content', 'social_media_content', etc.
            ttl: Time-to-live in seconds (uses default if None)
        """
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
        
        key = self.get_cache_key(topic, content_types)
        
        # Calculate expiration time
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        
        # Store in cache
        self.cache[key] = {
            'content': content_data.get('content', ''),
            'social_media_content': content_data.get('social_media_content', ''),
            'audio_content': content_data.get('audio_content', ''),
            'video_content': content_data.get('video_content', ''),
            'topic': topic,
            'generated_at': content_data.get('generated_at', datetime.now().isoformat()),
            'expires_at': expires_at,
            'ttl': ttl
        }
    
    def clear(self, topic: str = None, content_types: list = None):
        """
        Clear cache entry for specific topic/content types
        
        Args:
            topic: Topic to clear (clears all if None)
            content_types: Content types to clear (clears all if None)
        """
        if topic is None:
            self.cache.clear()
        else:
            key = self.get_cache_key(topic, content_types)
            if key in self.cache:
                del self.cache[key]
    
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
_cache_instance: Optional[ContentCache] = None


def get_cache() -> ContentCache:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ContentCache()
    return _cache_instance

