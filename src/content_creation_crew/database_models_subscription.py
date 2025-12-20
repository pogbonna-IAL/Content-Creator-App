"""
Additional database models for subscription and tiered pricing
Add these to database.py when implementing tiered pricing
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class SubscriptionTier(Base):
    """Subscription tier definitions"""
    __tablename__ = "subscription_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)  # 'free', 'basic', 'pro', 'enterprise'
    display_name = Column(String, nullable=False)
    price_monthly = Column(Integer, default=0)  # Price in cents
    price_yearly = Column(Integer, default=0)  # Price in cents
    features = Column(JSON)  # List of feature strings
    limits = Column(JSON)  # Dict of content type limits
    content_types = Column(JSON)  # List of available content types
    model = Column(String)  # LLM model to use
    max_parallel_tasks = Column(Integer, default=1)
    priority_processing = Column(Boolean, default=False)
    api_access = Column(Boolean, default=False)
    api_rate_limit = Column(Integer, nullable=True)  # Requests per day, null = unlimited
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="tier")


class UserSubscription(Base):
    """User subscription records"""
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier_id = Column(Integer, ForeignKey("subscription_tiers.id"), nullable=False)
    status = Column(String, nullable=False, default='active')  # 'active', 'cancelled', 'expired', 'past_due'
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False, index=True)
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)
    stripe_subscription_id = Column(String, nullable=True, unique=True, index=True)  # For payment integration
    stripe_customer_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    tier = relationship("SubscriptionTier", back_populates="subscriptions")
    usage_records = relationship("UsageTracking", back_populates="subscription")


class UsageTracking(Base):
    """Track content generation usage per billing period"""
    __tablename__ = "usage_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True)
    content_type = Column(String, nullable=False)  # 'blog', 'social', 'audio', 'video'
    generation_count = Column(Integer, default=0)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    subscription = relationship("UserSubscription", back_populates="usage_records")
    
    # Composite index for efficient queries
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )



