"""
Tier management API routes
Note: Subscription management components removed for future implementation
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from .database import User, get_db
# Subscription components removed for future implementation
# from .database import UserSubscription, SubscriptionTier
from .auth import get_current_user
from .services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


# Subscription management models removed for future implementation
# These will be added when subscription management is integrated with pricing

# class SubscriptionResponse(BaseModel):
#     """Response model for subscription information"""
#     tier: str
#     display_name: str
#     status: str
#     current_period_start: Optional[str]
#     current_period_end: Optional[str]
#     cancel_at_period_end: bool
#     usage: Dict[str, Dict]
#     limits: Dict[str, int]
#     features: List[str]


# class UsageStatsResponse(BaseModel):
#     """Response model for usage statistics"""
#     usage: Dict[str, Dict]
#     tier: str
#     limits: Dict[str, int]


class TierInfoResponse(BaseModel):
    """Response model for tier information"""
    name: str
    display_name: str
    # Pricing fields removed for future implementation
    # price_monthly: int
    # price_yearly: int
    features: List[str]
    limits: Dict[str, int]
    content_types: List[str]
    model: str
    max_parallel_tasks: int


# Subscription management endpoints removed for future implementation
# These will be added when subscription management is integrated with pricing

# @router.get("/current", response_model=SubscriptionResponse)
# async def get_current_subscription(...):
#     """Get user's current subscription details"""
#     pass


# @router.get("/usage", response_model=UsageStatsResponse)
# async def get_usage_stats(...):
#     """Get usage statistics for current billing period"""
#     pass


@router.get("/tiers", response_model=List[TierInfoResponse])
async def get_available_tiers(
    db: Session = Depends(get_db)
):
    """
    Get all available subscription tiers and their features
    """
    subscription_service = SubscriptionService(db)
    
    tiers = []
    # Access tier configs through the service's internal method
    # Note: This accesses a protected method, but it's the cleanest way to get all tiers
    tier_configs = subscription_service._load_tier_config() if hasattr(subscription_service, '_load_tier_config') else {}
    
    # Fallback: load directly if method not accessible
    if not tier_configs:
        import yaml
        from pathlib import Path
        try:
            config_path = Path(__file__).parent.parent / "config" / "tiers.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    tier_configs = config.get('tiers', {})
        except Exception:
            tier_configs = {}
    
    for tier_name, tier_config in tier_configs.items():
        tiers.append(TierInfoResponse(
            name=tier_name,
            display_name=tier_config.get('display_name', tier_name.capitalize()),
            # Pricing removed for future implementation
            # price_monthly=tier_config.get('price_monthly', 0),
            # price_yearly=tier_config.get('price_yearly', 0),
            features=tier_config.get('features', []),
            limits=tier_config.get('limits', {}),
            content_types=tier_config.get('content_types', []),
            model=tier_config.get('model', ''),
            max_parallel_tasks=tier_config.get('max_parallel_tasks', 1)
        ))
    
    return tiers


@router.get("/tiers/{tier_name}", response_model=TierInfoResponse)
async def get_tier_info(
    tier_name: str,
    db: Session = Depends(get_db)
):
    """
    Get information about a specific subscription tier
    """
    subscription_service = SubscriptionService(db)
    tier_config = subscription_service.get_tier_config(tier_name)
    
    if not tier_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tier '{tier_name}' not found"
        )
    
    return TierInfoResponse(
        name=tier_name,
        display_name=tier_config.get('display_name', tier_name.capitalize()),
        # Pricing removed for future implementation
        # price_monthly=tier_config.get('price_monthly', 0),
        # price_yearly=tier_config.get('price_yearly', 0),
        features=tier_config.get('features', []),
        limits=tier_config.get('limits', {}),
        content_types=tier_config.get('content_types', []),
        model=tier_config.get('model', ''),
        max_parallel_tasks=tier_config.get('max_parallel_tasks', 1)
    )


# Subscription and pricing management endpoints removed for future implementation
# These will be added when subscription management and payment processing are integrated

# class UpgradeRequest(BaseModel):
#     """Request model for subscription upgrade"""
#     tier_name: str
#     billing_period: str = "monthly"  # "monthly" or "yearly"


# @router.post("/upgrade")
# async def upgrade_subscription(...):
#     """Upgrade user subscription to a higher tier"""
#     pass


# @router.post("/cancel")
# async def cancel_subscription(...):
#     """Cancel user's subscription"""
#     pass

