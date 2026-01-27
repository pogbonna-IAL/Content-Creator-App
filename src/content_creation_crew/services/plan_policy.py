"""
Plan Policy - Centralized tier enforcement and usage tracking
Wraps subscription_service and tier_middleware for consistent policy enforcement
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from fastapi import HTTPException, status
import logging

from ..database import (
    User,
    Organization,
    Membership,
    Subscription,
    UsageCounter,
    MembershipRole,
    SubscriptionPlan,
    SubscriptionStatus,
)
from .subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class PlanPolicyError(Exception):
    """Base exception for plan policy errors"""
    pass


class UsageLimitExceeded(PlanPolicyError):
    """Raised when usage limit is exceeded"""
    pass


class PlanPolicy:
    """
    Centralized plan policy enforcement
    Handles tier-based limits, usage tracking, and model selection
    """
    
    def __init__(self, db: Session, user: User):
        """
        Initialize PlanPolicy for a user
        
        Args:
            db: Database session
            user: User object
        """
        self.db = db
        self.user = user
        self.subscription_service = SubscriptionService(db)
        self._org_id: Optional[int] = None
        self._subscription: Optional[Subscription] = None
        self._tier_config: Optional[Dict] = None
    
    def _get_user_org_id(self) -> Optional[int]:
        """Get user's organization ID (creates org if needed)"""
        if self._org_id is not None:
            return self._org_id
        
        # Find user's organization membership
        membership = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).first()
        
        if membership:
            self._org_id = membership.org_id
            return self._org_id
        
        # Create organization for user if none exists
        org = Organization(
            name=f"{self.user.email}'s Organization",
            owner_user_id=self.user.id
        )
        self.db.add(org)
        self.db.flush()
        
        # Create membership
        membership = Membership(
            org_id=org.id,
            user_id=self.user.id,
            role=MembershipRole.OWNER.value
        )
        self.db.add(membership)
        
        # Create free tier subscription
        subscription = Subscription(
            org_id=org.id,
            plan=SubscriptionPlan.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_end=datetime.utcnow().replace(day=1) + timedelta(days=32)
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(org)
        
        self._org_id = org.id
        return self._org_id
    
    def _get_subscription(self) -> Optional[Subscription]:
        """Get user's active subscription"""
        if self._subscription is not None:
            return self._subscription
        
        org_id = self._get_user_org_id()
        if not org_id:
            return None
        
        self._subscription = self.db.query(Subscription).filter(
            Subscription.org_id == org_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
        
        return self._subscription
    
    def get_plan(self) -> str:
        """
        Get user's current plan name
        
        Returns:
            Plan name: 'free', 'basic', 'pro', or 'enterprise'
        """
        # Admin users get 'pro' tier for faster generation
        if hasattr(self.user, 'is_admin') and self.user.is_admin:
            logger.info(f"Admin user {self.user.id} ({self.user.email}) assigned 'pro' tier for faster generation")
            return SubscriptionPlan.PRO.value
        
        subscription = self._get_subscription()
        if subscription:
            return subscription.plan
        
        # Default to free if no subscription
        return SubscriptionPlan.FREE.value
    
    def get_tier_config(self) -> Dict:
        """Get tier configuration for current plan"""
        if self._tier_config is not None:
            return self._tier_config
        
        plan = self.get_plan()
        self._tier_config = self.subscription_service.get_tier_config(plan) or {}
        return self._tier_config
    
    def get_model_name(self, content_type: str = None) -> str:
        """
        Get LLM model name for current plan, with optional content type override
        
        Args:
            content_type: Optional content type ('blog', 'social', 'audio', 'video')
                         If provided, checks for user-specific model preference
        
        Returns:
            Model name (e.g., 'gpt-4o-mini')
        """
        # Check for user-specific model preference if content_type is provided
        if content_type:
            from ..db.models.user_model_preference import UserModelPreference
            preference = self.db.query(UserModelPreference).filter(
                UserModelPreference.user_id == self.user.id,
                UserModelPreference.content_type == content_type
            ).first()
            
            if preference:
                logger.info(
                    f"User {self.user.id} has custom model preference for {content_type}: {preference.model_name}"
                )
                return preference.model_name
        
        # Fall back to tier-based model selection
        tier_config = self.get_tier_config()
        return tier_config.get('model', 'gpt-4o-mini')
    
    def get_parallel_limit(self) -> int:
        """
        Get maximum parallel tasks for current plan
        
        Returns:
            Maximum parallel tasks (default: 1)
        """
        tier_config = self.get_tier_config()
        return tier_config.get('max_parallel_tasks', 1)
    
    def _get_current_period(self) -> str:
        """Get current billing period in YYYY-MM format"""
        now = datetime.utcnow()
        return now.strftime("%Y-%m")
    
    def _get_usage_counter(self, period_month: Optional[str] = None) -> Optional[UsageCounter]:
        """Get or create usage counter for current period"""
        org_id = self._get_user_org_id()
        if not org_id:
            return None
        
        if period_month is None:
            period_month = self._get_current_period()
        
        counter = self.db.query(UsageCounter).filter(
            UsageCounter.org_id == org_id,
            UsageCounter.period_month == period_month
        ).first()
        
        if not counter:
            counter = UsageCounter(
                org_id=org_id,
                period_month=period_month,
                blog_count=0,
                social_count=0,
                audio_count=0,
                video_count=0,
                voiceover_count=0,
                video_render_count=0
            )
            self.db.add(counter)
            self.db.flush()
        
        return counter
    
    def get_usage(self, content_type: str, period_month: Optional[str] = None) -> int:
        """
        Get current usage for a content type
        
        Args:
            content_type: 'blog', 'social', 'audio', 'video', 'voiceover_audio', or 'final_video'
            period_month: Optional period in YYYY-MM format (defaults to current month)
        
        Returns:
            Current usage count
        """
        counter = self._get_usage_counter(period_month)
        if not counter:
            return 0
        
        count_map = {
            'blog': counter.blog_count,
            'social': counter.social_count,
            'audio': counter.audio_count,
            'video': counter.video_count,
            'voiceover_audio': counter.voiceover_count,
            'final_video': counter.video_render_count,
        }
        
        return count_map.get(content_type, 0)
    
    def get_limit(self, content_type: str) -> int:
        """
        Get monthly limit for a content type
        
        Args:
            content_type: 'blog', 'social', 'audio', 'video', 'voiceover_audio', or 'final_video'
        
        Returns:
            Monthly limit (-1 for unlimited, 0 if not allowed)
        """
        tier_config = self.get_tier_config()
        limits = tier_config.get('limits', {})
        return limits.get(content_type, 0)
    
    def enforce_monthly_limit(self, content_type: str) -> Tuple[bool, int, int]:
        """
        Enforce monthly usage limit for a content type
        
        Args:
            content_type: 'blog', 'social', 'audio', 'video', 'voiceover_audio', or 'final_video'
        
        Returns:
            Tuple of (allowed, used, limit)
            Raises HTTPException if limit exceeded
        
        Raises:
            HTTPException: If limit is exceeded
        """
        limit = self.get_limit(content_type)
        used = self.get_usage(content_type)
        
        # Check if feature is not allowed (limit is 0 and not -1)
        if limit == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "PLAN_LIMIT_EXCEEDED",
                    "message": f"Your plan does not include {content_type} generation.",
                    "content_type": content_type,
                    "used": used,
                    "limit": limit,
                    "plan": self.get_plan()
                }
            )
        
        # Unlimited plans
        if limit == -1:
            return True, used, -1
        
        # Check if limit exceeded
        if used >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "PLAN_LIMIT_EXCEEDED",
                    "message": f"You have reached your {content_type} generation limit ({limit} per month).",
                    "content_type": content_type,
                    "used": used,
                    "limit": limit,
                    "plan": self.get_plan()
                }
            )
        
        return True, used, limit
    
    def increment_usage(self, content_type: str) -> None:
        """
        Increment usage counter for a content type
        
        Args:
            content_type: 'blog', 'social', 'audio', 'video', 'voiceover_audio', or 'final_video'
        """
        counter = self._get_usage_counter()
        if not counter:
            logger.warning(f"Could not get usage counter for user {self.user.id}")
            return
        
        # Increment appropriate counter
        if content_type == 'blog':
            counter.blog_count += 1
        elif content_type == 'social':
            counter.social_count += 1
        elif content_type == 'audio':
            counter.audio_count += 1
        elif content_type == 'video':
            counter.video_count += 1
        elif content_type == 'voiceover_audio':
            counter.voiceover_count += 1
        elif content_type == 'final_video':
            counter.video_render_count += 1
        else:
            logger.warning(f"Unknown content type: {content_type}")
            return
        
        counter.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Get the count value for logging
        count_attr_map = {
            'blog': 'blog_count',
            'social': 'social_count',
            'audio': 'audio_count',
            'video': 'video_count',
            'voiceover_audio': 'voiceover_count',
            'final_video': 'video_render_count',
        }
        count_attr = count_attr_map.get(content_type, 'unknown')
        count_value = getattr(counter, count_attr, 0)
        logger.info(f"Incremented {content_type} usage for org {counter.org_id}: {count_value}")
    
    def get_usage_stats(self) -> Dict[str, Dict]:
        """
        Get usage statistics for all content types
        
        Returns:
            Dictionary mapping content types to usage stats
        """
        stats = {}
        content_types = ['blog', 'social', 'audio', 'video', 'voiceover_audio', 'final_video']
        
        for content_type in content_types:
            used = self.get_usage(content_type)
            limit = self.get_limit(content_type)
            remaining = limit - used if limit != -1 else -1
            
            stats[content_type] = {
                'used': used,
                'limit': limit,
                'remaining': remaining,
                'unlimited': limit == -1
            }
        
        return stats
    
    def check_content_type_access(self, content_type: str) -> bool:
        """Check if user's plan supports a content type"""
        tier_config = self.get_tier_config()
        content_types = tier_config.get('content_types', [])
        return content_type in content_types
    
    def check_feature_access(self, feature: str) -> bool:
        """Check if user's plan includes a feature"""
        tier_config = self.get_tier_config()
        features = tier_config.get('features', [])
        return feature in features
    
    def can_generate(self, media_type: str) -> bool:
        """
        Check if user can generate a specific media type
        
        Args:
            media_type: 'voiceover_audio' or 'final_video'
        
        Returns:
            True if generation is allowed, False otherwise
        """
        limit = self.get_limit(media_type)
        # -1 means unlimited, > 0 means limited but allowed, 0 means not allowed
        return limit != 0
    
    def enforce_media_generation_limit(self, media_type: str) -> Tuple[bool, int, int]:
        """
        Enforce monthly limit for media generation (voiceover_audio or final_video)
        
        Args:
            media_type: 'voiceover_audio' or 'final_video'
        
        Returns:
            Tuple of (allowed, used, limit)
            Raises HTTPException if limit exceeded
        
        Raises:
            HTTPException: If limit is exceeded or not allowed
        """
        return self.enforce_monthly_limit(media_type)

