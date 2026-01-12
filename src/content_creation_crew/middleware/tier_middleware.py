"""
Middleware for tier-based access control and feature gating
Uses PlanPolicy internally for consistent enforcement
"""
from functools import wraps
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Callable
from ..database import User
from ..services.plan_policy import PlanPolicy


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
            
            policy = PlanPolicy(db, current_user)
            user_plan = policy.get_plan()
            
            if user_plan not in allowed_tiers:
                tier_names = ', '.join(allowed_tiers)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires {tier_names} plan. Your current plan: {user_plan}"
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
            
            policy = PlanPolicy(db, current_user)
            
            # Check if plan supports content type
            if not policy.check_content_type_access(content_type):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Your subscription plan does not include {content_type} content generation."
                )
            
            # Enforce monthly limit (raises HTTPException if exceeded)
            try:
                policy.enforce_monthly_limit(content_type)
            except HTTPException:
                raise  # Re-raise HTTPException from enforce_monthly_limit
            
            # Note: Usage is incremented after successful generation, not before
            # This prevents counting failed generations against limits
            
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
            
            policy = PlanPolicy(db, current_user)
            
            if not policy.check_feature_access(feature):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires a higher subscription plan."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

