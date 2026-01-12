"""
Billing event model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..base import Base


class BillingEventType(str, enum.Enum):
    """Billing event type enum"""
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    INVOICE_CREATED = "invoice_created"
    INVOICE_PAID = "invoice_paid"


class BillingEvent(Base):
    """Billing event model for audit trail"""
    __tablename__ = "billing_events"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # 'stripe', 'paystack'
    event_type = Column(String, nullable=False, index=True)
    provider_event_id = Column(String, nullable=False, unique=True, index=True)  # Unique ID from provider
    payload_json = Column(JSONB, nullable=False)  # Full event payload (PostgreSQL JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="billing_events")
    
    # Unique constraint on provider_event_id (already enforced by unique index)
    __table_args__ = (
        UniqueConstraint("provider_event_id", name="uq_billing_events_provider_event_id"),
    )

