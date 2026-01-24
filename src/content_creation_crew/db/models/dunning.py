"""
Dunning models for failed payment recovery
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import enum

from ..base import Base


class PaymentAttemptStatus(str, enum.Enum):
    """Payment attempt status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DunningStatus(str, enum.Enum):
    """Dunning process status"""
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    CANCELLED = "cancelled"
    EXHAUSTED = "exhausted"


class PaymentAttempt(Base):
    """
    Payment attempt tracking for dunning
    
    Tracks each attempt to charge a customer's payment method,
    including automatic retries and manual retries.
    """
    __tablename__ = "payment_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    dunning_process_id = Column(Integer, ForeignKey("dunning_processes.id"), nullable=True, index=True)
    
    # Payment details
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Status
    status = Column(String(20), default=PaymentAttemptStatus.PENDING.value, nullable=False, index=True)
    
    # Attempt info
    attempt_number = Column(Integer, default=1, nullable=False)
    is_automatic = Column(Boolean, default=True)  # Auto vs manual retry
    
    # Provider info
    provider = Column(String(20), nullable=False)  # stripe, paystack
    provider_payment_intent_id = Column(String(100), nullable=True, index=True)
    provider_charge_id = Column(String(100), nullable=True)
    
    # Failure details
    failure_code = Column(String(50), nullable=True)
    failure_message = Column(String(500), nullable=True)
    failure_reason = Column(String(100), nullable=True)  # card_declined, insufficient_funds, etc.
    
    # Retry scheduling
    next_retry_at = Column(DateTime, nullable=True, index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timestamps
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    succeeded_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", backref="payment_attempts")
    dunning_process = relationship("DunningProcess", back_populates="payment_attempts")
    
    # Indexes
    __table_args__ = (
        Index("idx_payment_attempts_subscription_status", "subscription_id", "status"),
        Index("idx_payment_attempts_next_retry", "next_retry_at", "status"),
    )
    
    def __repr__(self):
        return f"<PaymentAttempt(id={self.id}, subscription_id={self.subscription_id}, status={self.status}, amount={self.amount})>"


class DunningProcess(Base):
    """
    Dunning process for recovering failed payments
    
    Manages the entire recovery process including:
    - Multiple payment retry attempts
    - Email notification sequence
    - Grace periods
    - Final cancellation
    """
    __tablename__ = "dunning_processes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Process status
    status = Column(String(20), default=DunningStatus.ACTIVE.value, nullable=False, index=True)
    
    # Financial details
    amount_due = Column(Numeric(12, 2), nullable=False)
    amount_recovered = Column(Numeric(12, 2), default=0.00)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Process tracking
    total_attempts = Column(Integer, default=0)
    total_emails_sent = Column(Integer, default=0)
    current_stage = Column(String(50), default="initial")  # initial, warning_1, urgent, final_notice
    
    # Scheduling
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    next_action_at = Column(DateTime, nullable=True, index=True)
    grace_period_ends_at = Column(DateTime, nullable=True)
    will_cancel_at = Column(DateTime, nullable=True)
    
    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(String(200), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", backref="dunning_processes")
    organization = relationship("Organization", backref="dunning_processes")
    payment_attempts = relationship("PaymentAttempt", back_populates="dunning_process", order_by="PaymentAttempt.created_at")
    notifications = relationship("DunningNotification", back_populates="dunning_process", order_by="DunningNotification.created_at")
    
    # Indexes
    __table_args__ = (
        Index("idx_dunning_processes_subscription_status", "subscription_id", "status"),
        Index("idx_dunning_processes_next_action", "next_action_at", "status"),
    )
    
    def __repr__(self):
        return f"<DunningProcess(id={self.id}, subscription_id={self.subscription_id}, status={self.status}, stage={self.current_stage})>"


class DunningNotification(Base):
    """
    Dunning notification tracking
    
    Tracks all emails sent during the dunning process to prevent
    duplicate notifications and maintain audit trail.
    """
    __tablename__ = "dunning_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    dunning_process_id = Column(Integer, ForeignKey("dunning_processes.id"), nullable=False, index=True)
    
    # Notification details
    notification_type = Column(String(50), nullable=False)  # warning_1, warning_2, urgent, final_notice
    sent_to = Column(String(255), nullable=False)
    subject = Column(String(200), nullable=False)
    
    # Delivery tracking
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered = Column(Boolean, nullable=True)
    opened = Column(Boolean, nullable=True)
    clicked = Column(Boolean, nullable=True)
    
    # Provider tracking
    email_provider = Column(String(50), nullable=True)
    provider_message_id = Column(String(200), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    dunning_process = relationship("DunningProcess", back_populates="notifications")
    
    def __repr__(self):
        return f"<DunningNotification(id={self.id}, type={self.notification_type}, sent_to={self.sent_to})>"


class Refund(Base):
    """
    Refund tracking
    
    Tracks all refunds issued to customers, including:
    - Full and partial refunds
    - Refund reasons
    - Provider refund IDs
    - Refund status
    """
    __tablename__ = "refunds"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Refund details
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Refund type
    refund_type = Column(String(20), default="full")  # full, partial, prorated
    
    # Reason
    reason = Column(String(50), nullable=False)  # customer_request, duplicate, fraud, other
    reason_details = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, processing, succeeded, failed, cancelled
    
    # Provider info
    provider = Column(String(20), nullable=False)  # stripe, paystack
    provider_refund_id = Column(String(100), nullable=True, unique=True, index=True)
    provider_charge_id = Column(String(100), nullable=True)
    
    # Policy validation
    is_within_refund_window = Column(Boolean, default=True)
    refund_window_days = Column(Integer, nullable=True)  # How many days allowed
    days_since_payment = Column(Integer, nullable=True)  # Actual days since payment
    
    # Failure details
    failure_reason = Column(String(200), nullable=True)
    
    # Timestamps
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Requester
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", backref="refunds")
    invoice = relationship("Invoice", backref="refunds")
    organization = relationship("Organization", backref="refunds")
    
    # Indexes
    __table_args__ = (
        Index("idx_refunds_org_status", "organization_id", "status"),
        Index("idx_refunds_subscription", "subscription_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<Refund(id={self.id}, amount={self.amount}, status={self.status}, reason={self.reason})>"
    
    @property
    def is_successful(self) -> bool:
        """Check if refund was successful"""
        return self.status == "succeeded"

