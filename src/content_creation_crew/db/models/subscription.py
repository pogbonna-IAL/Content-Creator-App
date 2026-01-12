"""
Subscription and Usage Counter models
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..base import Base


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enum"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"


class SubscriptionPlan(str, enum.Enum):
    """Subscription plan enum"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PaymentProvider(str, enum.Enum):
    """Payment provider enum"""
    STRIPE = "stripe"
    PAYSTACK = "paystack"
    BANK_TRANSFER = "bank_transfer"


class Subscription(Base):
    """Organization subscription model"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    plan = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default=SubscriptionStatus.ACTIVE.value, index=True)
    provider = Column(String, nullable=True)
    provider_customer_id = Column(String, nullable=True, index=True)
    provider_subscription_id = Column(String, nullable=True, unique=True, index=True)
    current_period_end = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")


class UsageCounter(Base):
    """Usage counter per organization and period"""
    __tablename__ = "usage_counters"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    period_month = Column(String, nullable=False, index=True)  # Format: "YYYY-MM"
    blog_count = Column(Integer, default=0, nullable=False)
    social_count = Column(Integer, default=0, nullable=False)
    audio_count = Column(Integer, default=0, nullable=False)
    video_count = Column(Integer, default=0, nullable=False)
    voiceover_count = Column(Integer, default=0, nullable=False)  # TTS voiceover generations
    video_render_count = Column(Integer, default=0, nullable=False)  # Video rendering generations
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique constraint on org_id + period_month
    __table_args__ = (
        UniqueConstraint("org_id", "period_month", name="uq_usage_counters_org_period"),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="usage_counters")

