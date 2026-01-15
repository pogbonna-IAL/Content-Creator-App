"""
Invoice models for billing system
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, date
from decimal import Decimal
import enum

from ..base import Base


class InvoiceStatus(str, enum.Enum):
    """Invoice status enum"""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"
    REFUNDED = "refunded"


class Invoice(Base):
    """
    Invoice model for billing transactions
    
    Stores invoice details, line items, tax calculations, and payment information.
    Compliant with international invoicing standards.
    """
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Invoice identification
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)  # INV-2026-0001
    
    # Relationships
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    
    # Amounts (all in minor currency units - cents)
    subtotal = Column(Numeric(12, 2), nullable=False)  # Before tax
    tax_amount = Column(Numeric(12, 2), default=0.00, nullable=False)  # Total tax
    total = Column(Numeric(12, 2), nullable=False)  # subtotal + tax_amount
    amount_paid = Column(Numeric(12, 2), default=0.00)  # Amount paid so far
    amount_due = Column(Numeric(12, 2), nullable=False)  # Remaining balance
    
    # Currency
    currency = Column(String(3), default="USD", nullable=False)  # ISO 4217
    
    # Status
    status = Column(String(20), default=InvoiceStatus.DRAFT.value, nullable=False, index=True)
    
    # Dates
    invoice_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    paid_at = Column(DateTime, nullable=True)
    void_at = Column(DateTime, nullable=True)
    
    # Tax details (JSONB for flexibility)
    tax_details = Column(JSONB, nullable=True)  # {"rate": 0.20, "type": "VAT", "jurisdiction": "UK", ...}
    
    # Line items (JSONB array)
    line_items = Column(JSONB, nullable=False)  # [{"description": "Pro Plan", "quantity": 1, "unit_price": 29.99, ...}]
    
    # Customer details (snapshot at time of invoice)
    customer_details = Column(JSONB, nullable=False)  # {"name": "...", "email": "...", "address": {...}}
    
    # PDF storage
    pdf_url = Column(String(500), nullable=True)  # URL to stored PDF
    pdf_generated_at = Column(DateTime, nullable=True)
    
    # Provider references
    provider = Column(String(20), nullable=True)  # stripe, paystack, bank_transfer
    provider_invoice_id = Column(String(100), nullable=True, index=True)  # External invoice ID
    provider_payment_intent_id = Column(String(100), nullable=True)  # Payment intent ID
    
    # Notes and metadata
    notes = Column(String(1000), nullable=True)  # Internal notes
    memo = Column(String(500), nullable=True)  # Customer-visible memo
    extra_metadata = Column(JSONB, nullable=True)  # Additional data (renamed from 'metadata' - reserved in SQLAlchemy)
    
    # Email tracking
    emailed_to = Column(String(255), nullable=True)  # Email address invoice was sent to
    emailed_at = Column(DateTime, nullable=True)  # Last email sent time
    email_count = Column(Integer, default=0)  # Number of times emailed
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who created invoice
    
    # Relationships
    organization = relationship("Organization", backref="invoices")
    subscription = relationship("Subscription", backref="invoices")
    
    # Indexes
    __table_args__ = (
        Index("idx_invoices_org_date", "organization_id", "invoice_date"),
        Index("idx_invoices_status_date", "status", "invoice_date"),
        Index("idx_invoices_due_date", "due_date", "status"),
    )
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, number={self.invoice_number}, total={self.total}, status={self.status})>"
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid"""
        return self.status == InvoiceStatus.PAID.value
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue"""
        if self.status == InvoiceStatus.PAID.value:
            return False
        return date.today() > self.due_date
    
    def to_dict(self) -> dict:
        """Convert invoice to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "organization_id": self.organization_id,
            "subscription_id": self.subscription_id,
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "total": float(self.total),
            "amount_paid": float(self.amount_paid),
            "amount_due": float(self.amount_due),
            "currency": self.currency,
            "status": self.status,
            "invoice_date": self.invoice_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "tax_details": self.tax_details,
            "line_items": self.line_items,
            "customer_details": self.customer_details,
            "pdf_url": self.pdf_url,
            "is_paid": self.is_paid,
            "is_overdue": self.is_overdue,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BillingAddress(Base):
    """
    Billing address and customer information for invoices and tax calculation
    """
    __tablename__ = "billing_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True, index=True)
    
    # Company/Contact information
    company_name = Column(String(200), nullable=True)
    contact_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    
    # Address
    address_line1 = Column(String(200), nullable=False)
    address_line2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=False)
    state_province = Column(String(100), nullable=True)  # State/Province/County
    postal_code = Column(String(20), nullable=False)
    country_code = Column(String(2), nullable=False, index=True)  # ISO 3166-1 alpha-2
    
    # Tax information
    tax_id = Column(String(50), nullable=True)  # VAT/GST/EIN number
    tax_id_type = Column(String(20), nullable=True)  # vat, gst, ein, etc.
    tax_id_verified = Column(Boolean, default=False)
    customer_type = Column(String(20), default="individual")  # individual, business
    
    # Tax exemption
    tax_exempt = Column(Boolean, default=False)
    tax_exempt_reason = Column(String(200), nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    organization = relationship("Organization", backref="billing_address")
    
    def __repr__(self):
        return f"<BillingAddress(org_id={self.organization_id}, country={self.country_code})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "company_name": self.company_name,
            "contact_name": self.contact_name,
            "email": self.email,
            "phone": self.phone,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state_province": self.state_province,
            "postal_code": self.postal_code,
            "country_code": self.country_code,
            "tax_id": self.tax_id,
            "tax_id_type": self.tax_id_type,
            "tax_id_verified": self.tax_id_verified,
            "customer_type": self.customer_type,
            "tax_exempt": self.tax_exempt,
        }
    
    def get_full_address(self) -> str:
        """Get formatted full address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country_code,
        ]
        return ", ".join([p for p in parts if p])

