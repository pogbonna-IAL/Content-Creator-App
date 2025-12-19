"""
Subscription Service - Manages user subscriptions and tier access
"""
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import yaml
from pathlib import Path
# Subscription components removed for future implementation
# from ..database import User, UserSubscription, SubscriptionTier, UsageTracking
from ..database import User
from .user_cache import get_user_cache


class SubscriptionService:
    """Service for managing subscriptions and tier access"""
    
    def __init__(self, db: Session):
        self.db = db
        self._tier_config = None
    
    def _load_tier_config(self) -> Dict:
        """Load tier configuration from YAML file"""
        if self._tier_config is None:
            config_path = Path(__file__).parent.parent / "config" / "tiers.yaml"
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self._tier_config = config.get('tiers', {})
        return self._tier_config
    
    def get_tier_config(self, tier_name: str) -> Optional[Dict]:
        """Get configuration for a specific tier"""
        config = self._load_tier_config()
        return config.get(tier_name)
    
    def get_user_tier(self, user_id: int) -> str:
        """
        Get user's current tier.
        Currently defaults to 'free' for all users.
        Subscription management removed for future implementation.
        Uses caching to reduce lookups.
        """
        # Check cache first (Database Optimization - Quick Win)
        user_cache = get_user_cache()
        cached_data = user_cache.get(user_id)
        if cached_data and 'tier' in cached_data:
            return cached_data['tier']
        
        # Default to 'free' tier for all users (no subscription management)
        # When subscription management is added, this will query UserSubscription table
        tier = 'free'
        
        # Cache the result
        user_cache.set(user_id, {'tier': tier})
        
        return tier
    
    # Subscription management method removed for future implementation
    # def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
    #     """Get user's active subscription object"""
    #     pass
    
    def check_feature_access(self, user_id: int, feature: str) -> bool:
        """Check if user has access to a specific feature"""
        tier = self.get_user_tier(user_id)
        tier_config = self.get_tier_config(tier)
        
        if not tier_config:
            return False
        
        features = tier_config.get('features', [])
        return feature in features
    
    def check_content_type_access(self, user_id: int, content_type: str) -> bool:
        """Check if user's tier supports a content type"""
        tier = self.get_user_tier(user_id)
        tier_config = self.get_tier_config(tier)
        
        if not tier_config:
            return False
        
        content_types = tier_config.get('content_types', [])
        return content_type in content_types
    
    def check_usage_limit(self, user_id: int, content_type: str) -> tuple[bool, int]:
        """
        Check if user has remaining usage for content type.
        Returns (has_remaining, remaining_count)
        Note: Usage tracking removed for future implementation - currently returns unlimited
        """
        tier = self.get_user_tier(user_id)
        tier_config = self.get_tier_config(tier)
        
        if not tier_config:
            return False, 0
        
        limits = tier_config.get('limits', {})
        limit = limits.get(content_type, 0)
        
        # -1 means unlimited
        if limit == -1:
            return True, -1
        
        # Usage tracking removed for future implementation
        # For now, return unlimited access (usage tracking will be added with subscription management)
        # When implemented, this will query UsageTracking table for current period usage
        return True, limit if limit > 0 else -1
    
    def record_usage(self, user_id: int, content_type: str):
        """
        Record content generation usage.
        Note: Usage tracking removed for future implementation - currently no-op
        """
        # Usage tracking removed for future implementation
        # When subscription management is added, this will record usage in UsageTracking table
        # For now, this is a no-op since we're not tracking usage
        pass
    
    def get_usage_stats(self, user_id: int) -> Dict[str, Dict]:
        """
        Get usage statistics for all content types.
        Note: Usage tracking removed for future implementation - returns limits only
        """
        tier = self.get_user_tier(user_id)
        tier_config = self.get_tier_config(tier)
        
        if not tier_config:
            return {}
        
        limits = tier_config.get('limits', {})
        stats = {}
        
        for content_type in ['blog', 'social', 'audio', 'video']:
            limit = limits.get(content_type, 0)
            # Usage tracking removed - return limits only
            stats[content_type] = {
                'limit': limit,
                'used': 0,  # Usage tracking not implemented
                'remaining': limit if limit > 0 else -1,
                'unlimited': limit == -1
            }
        
        return stats
    
    def get_tier_limits(self, tier_name: str) -> Dict:
        """Get limits for a specific tier"""
        tier_config = self.get_tier_config(tier_name)
        if not tier_config:
            return {}
        return tier_config.get('limits', {})

