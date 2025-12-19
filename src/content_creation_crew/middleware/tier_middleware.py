"""
Middleware for tier-based access control and feature gating
"""
from functools import wraps
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Callable
from ..database import User
from ..services.subscription_service import SubscriptionService


def require_tier(*allowed_tiers: str):
    """
    Decorator to require specific subscription tier(s)
    
    Usage:
        @require_tier('pro', 'enterprise')
        async def premium_feature(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user and db from kwargs
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not current_user or not isinstance(current_user, User):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session not available"
                )
            
            subscription_service = SubscriptionService(db)
            user_tier = subscription_service.get_user_tier(current_user.id)
            
            if user_tier not in allowed_tiers:
                tier_names = ', '.join(allowed_tiers)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires {tier_names} tier. Your current tier: {user_tier}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_content_type_access(content_type: str):
    """
    Decorator to check if user can access specific content type
    
    Usage:
        @check_content_type_access('video')
        async def generate_video(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            subscription_service = SubscriptionService(db)
            
            # Check if tier supports content type
            if not subscription_service.check_content_type_access(current_user.id, content_type):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Your subscription tier does not include {content_type} content generation."
                )
            
            # Check usage limits
            has_remaining, remaining = subscription_service.check_usage_limit(
                current_user.id, content_type
            )
            
            if not has_remaining:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You've reached your {content_type} generation limit for this period. "
                           f"Please wait for the next billing period."
                )
            
            # Record usage before generation
            subscription_service.record_usage(current_user.id, content_type)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_feature_access(feature: str):
    """
    Decorator to check if user has access to a specific feature
    
    Usage:
        @check_feature_access('api_access')
        async def api_endpoint(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            subscription_service = SubscriptionService(db)
            
            if not subscription_service.check_feature_access(current_user.id, feature):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires a higher subscription tier."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

