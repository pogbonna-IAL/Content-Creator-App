"""
Cache Invalidation Service (M6)
Centralized cache invalidation for user data, plans, and content
"""
import logging
import hashlib
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheInvalidationService:
    """
    Centralized cache invalidation service
    
    Manages invalidation of:
    - User cache (user:{user_id})
    - Organization/plan cache (org:{org_id}:plan)
    - Content cache (content:{hash})
    
    Ensures data consistency across the application by invalidating
    stale cached data when underlying data changes.
    """
    
    def __init__(self):
        """Initialize cache invalidation service"""
        self.user_cache = None
        self.content_cache = None
        self._init_caches()
    
    def _init_caches(self):
        """Initialize cache instances lazily"""
        try:
            from .user_cache import get_user_cache
            from .content_cache import get_cache
            
            self.user_cache = get_user_cache()
            self.content_cache = get_cache()
        except Exception as e:
            logger.warning(f"Failed to initialize caches: {e}")
    
    # ========================================================================
    # User Cache Invalidation
    # ========================================================================
    
    def invalidate_user(self, user_id: int, reason: str = "update") -> bool:
        """
        Invalidate user cache
        
        Triggers:
        - Profile updates
        - Password changes
        - Email verification status changes
        - GDPR delete requested/completed
        
        Args:
            user_id: User ID
            reason: Reason for invalidation (for logging)
        
        Returns:
            True if invalidated, False if cache not available
        """
        try:
            if self.user_cache is None:
                self._init_caches()
            
            if self.user_cache:
                self.user_cache.invalidate(user_id)
                logger.info(f"Invalidated user cache for user_id={user_id}, reason={reason}")
                return True
            else:
                logger.warning(f"User cache not available for invalidation: user_id={user_id}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to invalidate user cache for user_id={user_id}: {e}")
            return False
    
    def invalidate_user_on_profile_update(self, user_id: int) -> bool:
        """
        Invalidate user cache on profile update
        
        Args:
            user_id: User ID
        
        Returns:
            True if invalidated
        """
        return self.invalidate_user(user_id, reason="profile_update")
    
    def invalidate_user_on_password_change(self, user_id: int) -> bool:
        """
        Invalidate user cache on password change
        
        Args:
            user_id: User ID
        
        Returns:
            True if invalidated
        """
        return self.invalidate_user(user_id, reason="password_change")
    
    def invalidate_user_on_email_verification(self, user_id: int) -> bool:
        """
        Invalidate user cache on email verification status change
        
        Args:
            user_id: User ID
        
        Returns:
            True if invalidated
        """
        return self.invalidate_user(user_id, reason="email_verification")
    
    def invalidate_user_on_gdpr_delete(self, user_id: int) -> bool:
        """
        Invalidate user cache on GDPR deletion request/completion
        
        Args:
            user_id: User ID
        
        Returns:
            True if invalidated
        """
        return self.invalidate_user(user_id, reason="gdpr_delete")
    
    # ========================================================================
    # Organization/Plan Cache Invalidation
    # ========================================================================
    
    def invalidate_org_plan(self, org_id: int, reason: str = "update") -> bool:
        """
        Invalidate organization/plan cache
        
        Triggers:
        - Subscription changed by webhook
        - Bank transfer confirmed
        - Plan upgraded/downgraded
        
        Args:
            org_id: Organization ID
            reason: Reason for invalidation (for logging)
        
        Returns:
            True if invalidated
        """
        try:
            # For now, we don't have a separate org cache
            # but we log the invalidation for future implementation
            logger.info(f"Invalidated org/plan cache for org_id={org_id}, reason={reason}")
            
            # If org has members, invalidate their user caches too
            # since their subscription/tier info is cached
            try:
                from ..db.engine import SessionLocal
                from ..db.models.organization import OrganizationMember
                
                db = SessionLocal()
                try:
                    members = db.query(OrganizationMember).filter(
                        OrganizationMember.organization_id == org_id
                    ).all()
                    
                    for member in members:
                        self.invalidate_user(
                            member.user_id,
                            reason=f"org_plan_change_{reason}"
                        )
                    
                    logger.info(f"Invalidated {len(members)} user caches for org_id={org_id}")
                
                finally:
                    db.close()
            
            except Exception as e:
                logger.error(f"Failed to invalidate member caches for org_id={org_id}: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to invalidate org/plan cache for org_id={org_id}: {e}")
            return False
    
    def invalidate_org_on_subscription_change(self, org_id: int) -> bool:
        """
        Invalidate org/plan cache on subscription change (webhook)
        
        Args:
            org_id: Organization ID
        
        Returns:
            True if invalidated
        """
        return self.invalidate_org_plan(org_id, reason="subscription_webhook")
    
    def invalidate_org_on_bank_transfer(self, org_id: int) -> bool:
        """
        Invalidate org/plan cache on bank transfer confirmation
        
        Args:
            org_id: Organization ID
        
        Returns:
            True if invalidated
        """
        return self.invalidate_org_plan(org_id, reason="bank_transfer_confirmed")
    
    def invalidate_org_on_plan_change(self, org_id: int) -> bool:
        """
        Invalidate org/plan cache on plan upgrade/downgrade
        
        Args:
            org_id: Organization ID
        
        Returns:
            True if invalidated
        """
        return self.invalidate_org_plan(org_id, reason="plan_change")
    
    # ========================================================================
    # Content Cache Invalidation
    # ========================================================================
    
    def invalidate_content_by_topic(
        self,
        topic: str,
        content_types: Optional[List[str]] = None,
        reason: str = "update"
    ) -> bool:
        """
        Invalidate content cache for specific topic
        
        Args:
            topic: Content topic
            content_types: List of content types (optional)
            reason: Reason for invalidation
        
        Returns:
            True if invalidated
        """
        try:
            if self.content_cache is None:
                self._init_caches()
            
            if self.content_cache:
                # Invalidate by topic and content types
                if hasattr(self.content_cache, 'invalidate_topic'):
                    self.content_cache.invalidate_topic(topic, content_types)
                    logger.info(f"Invalidated content cache for topic='{topic}', reason={reason}")
                    return True
                else:
                    logger.warning("Content cache does not support topic invalidation")
                    return False
            else:
                logger.warning(f"Content cache not available for invalidation: topic='{topic}'")
                return False
        
        except Exception as e:
            logger.error(f"Failed to invalidate content cache for topic='{topic}': {e}")
            return False
    
    def invalidate_all_content(self, reason: str = "moderation_rules_changed") -> bool:
        """
        Invalidate ALL content cache (emergency use only)
        
        Triggers:
        - Moderation rules changed
        - Prompt version changed globally
        - Critical bug fix in content generation
        
        Args:
            reason: Reason for invalidation
        
        Returns:
            True if invalidated
        """
        try:
            if self.content_cache is None:
                self._init_caches()
            
            if self.content_cache:
                self.content_cache.clear()
                logger.warning(f"CLEARED ALL CONTENT CACHE - reason={reason}")
                return True
            else:
                logger.warning("Content cache not available for clearing")
                return False
        
        except Exception as e:
            logger.error(f"Failed to clear all content cache: {e}")
            return False
    
    def get_content_cache_key(
        self,
        topic: str,
        content_types: Optional[List[str]] = None,
        prompt_version: Optional[str] = None,
        model: Optional[str] = None,
        moderation_version: Optional[str] = None
    ) -> str:
        """
        Generate content cache key with moderation version
        
        Cache key format: content:{hash(topic, types, model, prompt_version, moderation_version)}
        
        Args:
            topic: Content topic
            content_types: List of content types
            prompt_version: Prompt version (default from schemas)
            model: LLM model name
            moderation_version: Moderation rules version (NEW - M6)
        
        Returns:
            Cache key string
        """
        from ..schemas import PROMPT_VERSION
        from ..config import config
        
        # Normalize inputs
        normalized_topic = topic.lower().strip()
        normalized_types = sorted(content_types or ['blog'])
        prompt_version = prompt_version or PROMPT_VERSION
        model = model or ""
        
        # Get moderation version from config or default
        # This allows cache invalidation when moderation rules change
        moderation_version = moderation_version or getattr(config, 'MODERATION_VERSION', '1.0.0')
        
        # Create cache string with moderation version
        cache_string = (
            f"{normalized_topic}:"
            f"{':'.join(normalized_types)}:"
            f"{prompt_version}:"
            f"{model}:"
            f"{moderation_version}"
        )
        
        # Return hash
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()
        return f"content:{cache_hash}"
    
    # ========================================================================
    # Batch Invalidation
    # ========================================================================
    
    def invalidate_multiple_users(self, user_ids: List[int], reason: str = "batch_update") -> int:
        """
        Invalidate multiple user caches in batch
        
        Args:
            user_ids: List of user IDs
            reason: Reason for invalidation
        
        Returns:
            Number of successfully invalidated caches
        """
        count = 0
        for user_id in user_ids:
            if self.invalidate_user(user_id, reason=reason):
                count += 1
        
        logger.info(f"Batch invalidated {count}/{len(user_ids)} user caches, reason={reason}")
        return count
    
    def invalidate_org_and_members(self, org_id: int, reason: str = "org_update") -> bool:
        """
        Invalidate organization and all member user caches
        
        Args:
            org_id: Organization ID
            reason: Reason for invalidation
        
        Returns:
            True if successful
        """
        return self.invalidate_org_plan(org_id, reason=reason)
    
    # ========================================================================
    # Statistics and Monitoring
    # ========================================================================
    
    def get_invalidation_stats(self) -> dict:
        """
        Get cache invalidation statistics
        
        Returns:
            Dict with cache stats
        """
        stats = {
            "user_cache_available": self.user_cache is not None,
            "content_cache_available": self.content_cache is not None,
        }
        
        # Get user cache stats
        if self.user_cache and hasattr(self.user_cache, 'get_stats'):
            stats["user_cache"] = self.user_cache.get_stats()
        
        # Get content cache stats
        if self.content_cache and hasattr(self.content_cache, 'get_stats'):
            stats["content_cache"] = self.content_cache.get_stats()
        
        return stats


# Global cache invalidation service instance
_invalidation_service: Optional[CacheInvalidationService] = None


def get_cache_invalidation_service() -> CacheInvalidationService:
    """
    Get global cache invalidation service instance
    
    Returns:
        CacheInvalidationService singleton
    """
    global _invalidation_service
    
    if _invalidation_service is None:
        _invalidation_service = CacheInvalidationService()
    
    return _invalidation_service

