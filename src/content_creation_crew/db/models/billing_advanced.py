"""
Advanced billing models for enterprise features

Includes:
- Proration tracking
- Usage metering
- Credit notes
- Payment plans
- Chargebacks
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import enum

from ..base import Base


class ProrationEvent(Base):
    """
    Tracks proration events for mid-cycle plan changes
    
    When a customer upgrades/downgrades mid-cycle, we need to:
    1. Calculate unused time on old plan
    2. Calculate credit amount
    3. Apply credit to new plan
    4. Generate prorated invoice
    """
    __tablename__ = "proration_events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    
    # Plan change details
    old_plan = Column(String(50), nullable=False)
    new_plan = Column(String(50), nullable=False)
    change_type = Column(String(20), nullable=False)  # upgrade, downgrade, lateral
    
    # Proration calculation
    old_plan_price = Column(Numeric(12, 2), nullable=False)
    new_plan_price = Column(Numeric(12, 2), nullable=False)
    days_in_period = Column(Integer, nullable=False)  # Total days in billing period
    days_used = Column(Integer, nullable=False)  # Days used on old plan
    days_remaining = Column(Integer, nullable=False)  # Days remaining
    
    # Amounts
    credit_amount = Column(Numeric(12, 2), default=0.00)  # Credit from old plan
    charge_amount = Column(Numeric(12, 2), default=0.00)  # Charge for new plan (prorated)
    net_amount = Column(Numeric(12, 2), nullable=False)  # Net amount to charge/credit
    
    currency = Column(String(3), default="USD", nullable=False)
    
    # Dates
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    change_date = Column(DateTime, nullable=False)
    
    # Status
    status = Column(String(20), default="pending")  # pending, applied, cancelled
    applied_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", backref="proration_events")
    organization = relationship("Organization", backref="proration_events")
    invoice = relationship("Invoice", backref="proration_events")
    
    __table_args__ = (
        Index("idx_proration_subscription", "subscription_id", "created_at"),
        Index("idx_proration_org_status", "organization_id", "status"),
    )


class UsageMeter(Base):
    """
    Tracks usage metrics for metered billing
    
    Examples:
    - API calls
    - Storage GB
    - Video minutes rendered
    - TTS characters
    """
    __tablename__ = "usage_meters"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    
    # Meter details
    meter_name = Column(String(100), nullable=False, index=True)  # api_calls, storage_gb, video_minutes
    meter_type = Column(String(20), nullable=False)  # counter, gauge, histogram
    
    # Usage tracking
    current_value = Column(Numeric(12, 4), default=0.0000, nullable=False)
    period_value = Column(Numeric(12, 4), default=0.0000, nullable=False)  # Usage in current billing period
    lifetime_value = Column(Numeric(12, 4), default=0.0000, nullable=False)
    
    # Pricing
    unit_price = Column(Numeric(12, 4), nullable=True)  # Price per unit
    included_units = Column(Numeric(12, 2), default=0.00)  # Free tier included
    overage_price = Column(Numeric(12, 4), nullable=True)  # Price for overage
    
    # Period tracking
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    last_reset_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    organization = relationship("Organization", backref="usage_meters")
    subscription = relationship("Subscription", backref="usage_meters")
    events = relationship("UsageEvent", back_populates="meter", order_by="UsageEvent.created_at")
    
    __table_args__ = (
        Index("idx_usage_meter_org_name", "organization_id", "meter_name"),
        Index("idx_usage_meter_period", "period_start", "period_end"),
    )


class UsageEvent(Base):
    """
    Individual usage events for audit trail
    """
    __tablename__ = "usage_events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    meter_id = Column(Integer, ForeignKey("usage_meters.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # increment, decrement, set
    value = Column(Numeric(12, 4), nullable=False)
    previous_value = Column(Numeric(12, 4), nullable=True)
    new_value = Column(Numeric(12, 4), nullable=True)
    
    # Context
    resource_id = Column(String(100), nullable=True)  # e.g., content_job_id
    resource_type = Column(String(50), nullable=True)  # e.g., video, tts, api_call
    
    # Timestamps
    event_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    meter = relationship("UsageMeter", back_populates="events")
    organization = relationship("Organization")
    
    __table_args__ = (
        Index("idx_usage_event_meter_time", "meter_id", "event_time"),
    )


class CreditNote(Base):
    """
    Credit notes for refunds and adjustments
    
    A credit note is like a negative invoice - it credits money back to the customer.
    """
    __tablename__ = "credit_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Credit note number (e.g., CN-2026-0001)
    credit_note_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Relationships
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    refund_id = Column(Integer, ForeignKey("refunds.id"), nullable=True, index=True)
    
    # Amounts
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0.00)
    total = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Type and reason
    credit_type = Column(String(20), nullable=False)  # refund, adjustment, proration, goodwill
    reason = Column(String(50), nullable=False)
    reason_details = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default="draft", nullable=False)  # draft, issued, void
    
    # Dates
    credit_note_date = Column(DateTime, nullable=False)
    void_at = Column(DateTime, nullable=True)
    
    # Line items (JSONB)
    line_items = Column(JSONB, nullable=False)
    
    # PDF
    pdf_url = Column(String(500), nullable=True)
    pdf_generated_at = Column(DateTime, nullable=True)
    
    # Customer details snapshot
    customer_details = Column(JSONB, nullable=False)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    organization = relationship("Organization", backref="credit_notes")
    invoice = relationship("Invoice", backref="credit_notes")
    refund = relationship("Refund", backref="credit_notes")
    
    __table_args__ = (
        Index("idx_credit_note_org_date", "organization_id", "credit_note_date"),
    )


class PaymentPlan(Base):
    """
    Payment plans for installment payments
    
    Allows customers to split large payments into installments.
    """
    __tablename__ = "payment_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    
    # Plan details
    total_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Installments
    number_of_installments = Column(Integer, nullable=False)
    installment_amount = Column(Numeric(12, 2), nullable=False)
    installment_frequency = Column(String(20), nullable=False)  # weekly, biweekly, monthly
    
    # Tracking
    amount_paid = Column(Numeric(12, 2), default=0.00)
    installments_paid = Column(Integer, default=0)
    installments_remaining = Column(Integer, nullable=False)
    
    # Status
    status = Column(String(20), default="active", nullable=False)  # active, completed, defaulted, cancelled
    
    # Dates
    start_date = Column(DateTime, nullable=False)
    next_payment_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    defaulted_at = Column(DateTime, nullable=True)
    
    # Terms
    late_fee_amount = Column(Numeric(12, 2), default=0.00)
    grace_period_days = Column(Integer, default=3)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    organization = relationship("Organization", backref="payment_plans")
    invoice = relationship("Invoice", backref="payment_plans")
    installments = relationship("PaymentInstallment", back_populates="payment_plan", order_by="PaymentInstallment.installment_number")
    
    __table_args__ = (
        Index("idx_payment_plan_org_status", "organization_id", "status"),
        Index("idx_payment_plan_next_payment", "next_payment_date", "status"),
    )


class PaymentInstallment(Base):
    """Individual installment within a payment plan"""
    __tablename__ = "payment_installments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    payment_plan_id = Column(Integer, ForeignKey("payment_plans.id"), nullable=False, index=True)
    
    # Installment details
    installment_number = Column(Integer, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Status
    status = Column(String(20), default="pending", nullable=False)  # pending, paid, failed, skipped
    
    # Dates
    due_date = Column(DateTime, nullable=False, index=True)
    paid_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Payment details
    provider_payment_intent_id = Column(String(100), nullable=True)
    failure_reason = Column(String(200), nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    payment_plan = relationship("PaymentPlan", back_populates="installments")


class Chargeback(Base):
    """
    Chargeback disputes from payment providers
    
    When a customer disputes a charge with their bank.
    """
    __tablename__ = "chargebacks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    
    # Chargeback details
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Provider details
    provider = Column(String(20), nullable=False)  # stripe, paystack
    provider_chargeback_id = Column(String(100), unique=True, nullable=False, index=True)
    provider_charge_id = Column(String(100), nullable=True)
    provider_payment_intent_id = Column(String(100), nullable=True)
    
    # Reason
    reason = Column(String(50), nullable=False)  # fraudulent, duplicate, unrecognized, other
    reason_details = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)
    # pending, won, lost, accepted, withdrawn
    
    # Dates
    chargeback_date = Column(DateTime, nullable=False)
    respond_by_date = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Evidence
    evidence_submitted = Column(Boolean, default=False)
    evidence_submitted_at = Column(DateTime, nullable=True)
    evidence_details = Column(JSONB, nullable=True)
    
    # Outcome
    outcome = Column(String(20), nullable=True)  # won, lost
    outcome_reason = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    organization = relationship("Organization", backref="chargebacks")
    subscription = relationship("Subscription", backref="chargebacks")
    invoice = relationship("Invoice", backref="chargebacks")
    
    __table_args__ = (
        Index("idx_chargeback_org_status", "organization_id", "status"),
        Index("idx_chargeback_respond_by", "respond_by_date", "status"),
    )


class ExchangeRate(Base):
    """
    Currency exchange rates for multi-currency support
    
    Cached exchange rates updated daily.
    """
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Currency pair
    from_currency = Column(String(3), nullable=False, index=True)
    to_currency = Column(String(3), nullable=False, index=True)
    
    # Rate
    rate = Column(Numeric(12, 6), nullable=False)
    
    # Source
    source = Column(String(50), nullable=False)  # openexchangerates, ecb, manual
    
    # Validity
    effective_date = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_exchange_rate_pair_date", "from_currency", "to_currency", "effective_date"),
    )


class DunningRetryPrediction(Base):
    """
    ML predictions for optimal retry timing
    
    Uses historical data to predict best retry times.
    """
    __tablename__ = "dunning_retry_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    dunning_process_id = Column(Integer, ForeignKey("dunning_processes.id"), nullable=False, index=True)
    
    # Prediction
    predicted_success_probability = Column(Numeric(5, 4), nullable=False)  # 0.0000 to 1.0000
    recommended_retry_time = Column(DateTime, nullable=False)
    confidence_score = Column(Numeric(5, 4), nullable=False)
    
    # Features used
    features = Column(JSONB, nullable=True)  # Model input features
    
    # Model details
    model_version = Column(String(50), nullable=False)
    prediction_made_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Actual outcome (for model training)
    actual_success = Column(Boolean, nullable=True)
    actual_retry_time = Column(DateTime, nullable=True)
    
    # Metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    extra_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    dunning_process = relationship("DunningProcess")

