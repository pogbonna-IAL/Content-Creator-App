# Billing & Invoicing Gaps Analysis

**Date:** 2026-01-14  
**Status:** Review Complete  
**Priority:** High

---

## Executive Summary

The current billing system has a solid foundation with Stripe and Paystack integration, webhook handling, and basic subscription management. However, there are **15 critical gaps** that need to be addressed before production deployment, particularly around invoicing, tax compliance, dunning management, and refund handling.

---

## ✅ What's Currently Implemented

### Payment Processing
- ✅ Stripe integration
- ✅ Paystack integration  
- ✅ Bank transfer support
- ✅ Webhook handling with signature verification
- ✅ Replay attack protection (duplicate event detection)
- ✅ Subscription creation and cancellation
- ✅ Payment status tracking (active, past_due, cancelled, expired)
- ✅ Billing event audit trail (`billing_events` table)
- ✅ Organization-based subscriptions
- ✅ CSRF protection on billing endpoints

### Data Models
- ✅ `Subscription` table (org_id, plan, status, provider, dates)
- ✅ `BillingEvent` table (audit trail with JSONB payloads)
- ✅ Subscription status tracking
- ✅ Payment provider tracking

### API Endpoints
- ✅ `POST /v1/billing/upgrade` - Create/upgrade subscription
- ✅ `POST /v1/billing/bank-transfer` - Bank transfer requests
- ✅ `GET /v1/billing/subscription` - Get current subscription
- ✅ `POST /v1/billing/cancel` - Cancel subscription
- ✅ `POST /v1/billing/webhooks/stripe` - Stripe webhook handler
- ✅ `POST /v1/billing/webhooks/paystack` - Paystack webhook handler

---

## ❌ Critical Gaps (Must Have for Production)

### 1. **Invoice Generation & Storage** ⚠️ **CRITICAL**

**Status:** ❌ Not Implemented

**What's Missing:**
- No invoice generation when subscription is created
- No PDF invoice generation
- No invoice table in database
- No invoice number sequence/tracking
- No invoice download endpoint
- No invoice email delivery

**Business Impact:**
- **Legal risk:** Many jurisdictions require invoices by law
- **Customer frustration:** Users can't access receipts
- **Accounting issues:** No proper financial records
- **Tax compliance:** Can't provide required documentation

**Required:**
```python
# Database model needed
class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, unique=True, nullable=False)  # INV-2026-0001
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    
    # Invoice details
    amount = Column(Numeric(10, 2), nullable=False)  # Subtotal
    tax = Column(Numeric(10, 2), default=0.00)  # Tax amount
    total = Column(Numeric(10, 2), nullable=False)  # Total = amount + tax
    currency = Column(String(3), default="USD")
    
    # Status
    status = Column(String, default="draft")  # draft, issued, paid, void
    
    # Dates
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_at = Column(DateTime)
    
    # Files
    pdf_url = Column(String)  # S3 URL to PDF invoice
    
    # Provider references
    provider_invoice_id = Column(String)  # Stripe/Paystack invoice ID
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

**Required Endpoints:**
```python
@router.get("/invoices")
async def list_invoices(...)  # List all invoices for organization

@router.get("/invoices/{invoice_id}")
async def get_invoice(...)  # Get invoice details

@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(...)  # Download PDF

@router.post("/invoices/{invoice_id}/send")
async def send_invoice_email(...)  # Email invoice to customer
```

**Required Services:**
- `InvoiceGenerator` - Generate PDF invoices
- `InvoiceNumberGenerator` - Generate unique invoice numbers
- `InvoiceEmailService` - Send invoices via email

---

### 2. **Tax Calculation & Compliance** ⚠️ **CRITICAL**

**Status:** ❌ Not Implemented

**What's Missing:**
- No tax calculation
- No VAT/GST support
- No tax exemption handling
- No tax ID validation (VAT numbers)
- No reverse charge mechanism (EU B2B)
- No tax jurisdiction detection

**Business Impact:**
- **Legal risk:** Tax evasion liability
- **Regulatory issues:** Non-compliance with VAT/GST laws
- **Customer complaints:** Incorrect tax amounts
- **Financial risk:** Unpaid tax liabilities

**Required:**
```python
class TaxCalculator:
    """Calculate taxes based on customer location and tax rules"""
    
    def calculate_tax(
        self,
        amount: Decimal,
        country_code: str,
        state_code: Optional[str],
        customer_type: str,  # business, individual
        tax_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate tax for a transaction
        
        Returns:
            {
                "subtotal": Decimal,
                "tax_rate": Decimal,  # e.g., 0.20 for 20%
                "tax_amount": Decimal,
                "total": Decimal,
                "tax_name": str,  # e.g., "VAT", "GST", "Sales Tax"
                "reverse_charge": bool  # True for EU B2B
            }
        """
```

**Tax Rules Needed:**
- US sales tax by state
- EU VAT (20-27% depending on country)
- UK VAT (20%)
- Canada GST/HST/PST
- Australia GST (10%)
- India GST (18%)
- Reverse charge mechanism for EU B2B

**Database additions:**
```python
# Add to Organization model
tax_id = Column(String)  # VAT/GST number
tax_id_verified = Column(Boolean, default=False)
country_code = Column(String(2))  # ISO country code
state_code = Column(String(3))  # US state, CA province
customer_type = Column(String)  # business, individual
tax_exempt = Column(Boolean, default=False)
```

---

### 3. **Dunning Management (Failed Payment Handling)** ⚠️ **HIGH**

**Status:** ❌ Not Implemented

**What's Missing:**
- No automatic retry logic for failed payments
- No dunning email sequence
- No grace period before cancellation
- No payment recovery tracking
- No alternative payment method prompts

**Business Impact:**
- **Revenue loss:** Failed payments not recovered
- **Customer churn:** Immediate cancellations frustrate customers
- **Poor UX:** No warning before service interruption

**Required:**
```python
class DunningService:
    """Manage failed payment recovery"""
    
    RETRY_SCHEDULE = [
        {"days": 3, "action": "retry_payment"},
        {"days": 7, "action": "send_email_1"},
        {"days": 10, "action": "retry_payment"},
        {"days": 14, "action": "send_email_2"},
        {"days": 21, "action": "retry_payment"},
        {"days": 25, "action": "send_final_notice"},
        {"days": 30, "action": "cancel_subscription"}
    ]
    
    def handle_failed_payment(
        self,
        subscription_id: int,
        payment_amount: Decimal,
        failure_reason: str
    ):
        """Start dunning process for failed payment"""
    
    def retry_payment(self, subscription_id: int):
        """Attempt to charge customer again"""
    
    def send_dunning_email(
        self,
        subscription_id: int,
        email_type: str  # warning, urgent, final_notice
    ):
        """Send dunning email to customer"""
```

**Database model needed:**
```python
class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    amount = Column(Numeric(10, 2))
    currency = Column(String(3))
    status = Column(String)  # pending, succeeded, failed
    failure_reason = Column(String)
    provider_payment_id = Column(String)
    attempted_at = Column(DateTime)
    next_retry_at = Column(DateTime)
    retry_count = Column(Integer, default=0)
```

---

### 4. **Refund Management** ⚠️ **HIGH**

**Status:** ❌ Not Implemented

**What's Missing:**
- No refund endpoint
- No refund processing logic
- No partial refund support
- No refund tracking
- No refund policy enforcement (14-day window)

**Business Impact:**
- **Customer service burden:** Manual refund processing
- **Compliance risk:** Terms of service promise 14-day refunds
- **Poor UX:** No self-service refund option

**Required:**
```python
@router.post("/refunds")
async def create_refund(
    request: RefundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process refund request
    
    Business rules:
    - Within 14 days: full refund
    - After 14 days: no refund (except as required by law)
    - Annual subscriptions: pro-rated refund if mid-term cancellation
    """

class RefundService:
    def can_refund(
        self,
        subscription: Subscription,
        refund_amount: Optional[Decimal] = None
    ) -> Tuple[bool, str]:
        """Check if refund is allowed"""
    
    def process_refund(
        self,
        subscription_id: int,
        amount: Optional[Decimal] = None,  # None = full refund
        reason: str
    ) -> Refund:
        """Process refund via payment provider"""
```

**Database model:**
```python
class Refund(Base):
    __tablename__ = "refunds"
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    amount = Column(Numeric(10, 2))
    reason = Column(String)
    status = Column(String)  # pending, succeeded, failed
    provider_refund_id = Column(String)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### 5. **Billing Address & Customer Information** ⚠️ **MEDIUM**

**Status:** ❌ Not Implemented

**What's Missing:**
- No billing address storage
- No customer name/company name
- No phone number
- Required for invoices and tax compliance

**Business Impact:**
- **Invoice deficiency:** Invoices lack required information
- **Tax compliance:** Can't determine correct tax jurisdiction
- **Payment issues:** Payment provider may reject transactions

**Required:**
```python
# Add to Organization model or create separate BillingProfile
class BillingProfile(Base):
    __tablename__ = "billing_profiles"
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    
    # Contact info
    company_name = Column(String)
    contact_name = Column(String)
    email = Column(String)
    phone = Column(String)
    
    # Billing address
    address_line1 = Column(String)
    address_line2 = Column(String)
    city = Column(String)
    state_province = Column(String)
    postal_code = Column(String)
    country_code = Column(String(2))
    
    # Tax info
    tax_id = Column(String)  # VAT/GST number
    tax_id_type = Column(String)  # vat, gst, ein
```

---

### 6. **Payment Method Management** ⚠️ **MEDIUM**

**Status:** ❌ Not Implemented

**What's Missing:**
- No list of saved payment methods
- No add/remove payment methods
- No set default payment method
- No payment method update flow

**Required:**
```python
@router.get("/payment-methods")
async def list_payment_methods(...)

@router.post("/payment-methods")
async def add_payment_method(...)

@router.delete("/payment-methods/{method_id}")
async def remove_payment_method(...)

@router.post("/payment-methods/{method_id}/set-default")
async def set_default_payment_method(...)
```

---

### 7. **Usage-Based Billing** ⚠️ **MEDIUM**

**Status:** ⚠️ Partially Implemented (usage tracking exists but not billed)

**What's Missing:**
- No metered billing
- No overage charges
- No usage-based invoice line items
- Usage tracking exists but not monetized

**Required for Future:**
```python
class UsageBilling:
    """Calculate overage charges for usage-based features"""
    
    def calculate_overage(
        self,
        organization_id: int,
        billing_period: Tuple[datetime, datetime]
    ) -> Dict[str, Decimal]:
        """Calculate overage charges"""
```

---

### 8. **Proration Logic** ⚠️ **MEDIUM**

**Status:** ❌ Not Implemented

**What's Missing:**
- No mid-cycle upgrade/downgrade handling
- No pro-rated charges/credits
- No preview of pro-rated amounts before change

**Business Impact:**
- **Revenue loss:** Can't charge for mid-cycle upgrades
- **Customer confusion:** Unexpected billing amounts

---

### 9. **Billing History & Statements** ⚠️ **LOW**

**Status:** ❌ Not Implemented

**What's Missing:**
- No payment history view
- No billing statement generation
- No transaction list

**Required:**
```python
@router.get("/billing/history")
async def get_billing_history(...)  # List all payments

@router.get("/billing/statements")
async def list_statements(...)  # Monthly/annual statements
```

---

### 10. **Credit/Promo Codes** ⚠️ **LOW**

**Status:** ❌ Not Implemented

**What's Missing:**
- No coupon/promo code support
- No trial periods
- No credit balance

---

### 11. **Multi-Currency Support** ⚠️ **LOW**

**Status:** ⚠️ Hardcoded to USD

**What's Missing:**
- Only USD supported
- No currency conversion
- No regional pricing

---

### 12. **Subscription Pausing** ⚠️ **LOW**

**Status:** ❌ Not Implemented

**What's Missing:**
- No ability to pause subscription
- No vacation mode

---

### 13. **Team/Seat-Based Billing** ⚠️ **LOW**

**Status:** ❌ Not Implemented

**What's Missing:**
- No per-seat pricing
- No team member billing

---

### 14. **Billing Notifications** ⚠️ **MEDIUM**

**Status:** ⚠️ Partially Implemented (no emails sent)

**What's Missing:**
- No upcoming renewal notifications
- No payment success emails
- No payment failure notifications
- No receipt emails

**Required:**
```python
class BillingNotificationService:
    def send_payment_success_email(...)
    def send_payment_failure_email(...)
    def send_renewal_reminder(...)  # 7 days before renewal
    def send_invoice_email(...)
    def send_refund_confirmation(...)
```

---

### 15. **GDPR Compliance for Billing Data** ⚠️ **HIGH**

**Status:** ⚠️ Partially Implemented

**What's Implemented:**
- ✅ Billing events anonymized on GDPR deletion
- ✅ Billing events exported in GDPR export

**What's Missing:**
- ❌ No automatic deletion of payment methods on GDPR delete
- ❌ No deletion of billing profiles/addresses
- ❌ No provider cleanup (Stripe/Paystack customer deletion)

**Required:**
```python
# In GDPRDeletionService
def _delete_payment_provider_data(self):
    """Delete customer from Stripe/Paystack"""
    if self.user.stripe_customer_id:
        stripe.Customer.delete(self.user.stripe_customer_id)
```

---

## Priority Implementation Plan

### Phase 1: Critical (Before Production) - **2 weeks**

1. **Invoice Generation** (3 days)
   - Database migration
   - Invoice model
   - PDF generation (use ReportLab or WeasyPrint)
   - Invoice numbering
   - Download endpoint

2. **Tax Calculation** (4 days)
   - Basic tax calculator
   - US sales tax integration (TaxJar or Avalara)
   - EU VAT support
   - Tax ID validation
   - Database schema updates

3. **Dunning Management** (3 days)
   - Payment attempt tracking
   - Retry logic
   - Email notifications
   - Grace period handling

4. **Refund Management** (2 days)
   - Refund endpoint
   - Provider integration
   - Policy enforcement

5. **Billing Notifications** (2 days)
   - Email templates
   - Notification service
   - Event triggers

### Phase 2: High Priority - **1 week**

6. **Billing Address** (1 day)
   - Database model
   - Collection endpoints
   - Invoice integration

7. **Payment Method Management** (2 days)
   - List/add/remove endpoints
   - Provider integration

8. **GDPR Compliance** (2 days)
   - Payment provider cleanup
   - Billing profile deletion

### Phase 3: Medium Priority - **1 week**

9. **Proration Logic** (3 days)
10. **Billing History** (2 days)
11. **Usage-Based Billing** (2 days)

### Phase 4: Future Enhancements

12. Multi-currency
13. Credit codes
14. Subscription pausing
15. Team billing

---

## Recommended Tools & Services

### Tax Calculation
- **TaxJar** - $99/month - US sales tax automation
- **Avalara** - Enterprise - Global tax compliance
- **Quaderno** - $49/month - VAT/GST compliance
- **Stripe Tax** - Automatic (built into Stripe)

### Invoice Generation
- **ReportLab** - Python PDF library (free)
- **WeasyPrint** - HTML to PDF (free)
- **DocRaptor** - Cloud HTML to PDF ($15/month)

### Dunning Management
- **Stripe Billing** - Built-in dunning (free)
- **Churnbuster** - $300/month - Advanced dunning
- **Custom Implementation** - Using APScheduler

---

## Compliance Checklist

### Legal Requirements
- [ ] Invoice generation (required in EU, recommended globally)
- [ ] Tax calculation and collection
- [ ] Refund policy enforcement
- [ ] GDPR right to deletion (billing data)
- [ ] Data retention policy for financial records (7 years)

### Payment Provider Requirements
- [ ] Webhook signature verification ✅ (implemented)
- [ ] Idempotency keys
- [ ] Dispute handling
- [ ] 3D Secure (SCA) for EU

### Accounting Requirements
- [ ] Double-entry bookkeeping
- [ ] Audit trail ✅ (billing_events table)
- [ ] Financial reports
- [ ] Revenue recognition

---

## Testing Requirements

### Manual Testing Needed
- [ ] Subscription upgrade flow
- [ ] Subscription cancellation
- [ ] Failed payment handling
- [ ] Refund processing
- [ ] Invoice generation
- [ ] Tax calculation for various regions
- [ ] Webhook replay protection

### Automated Testing Needed
- [ ] Stripe webhook parsing
- [ ] Paystack webhook parsing
- [ ] Tax calculation logic
- [ ] Refund eligibility rules
- [ ] Invoice number generation
- [ ] Dunning schedule

---

## Cost Estimate

### Development Time
- **Phase 1 (Critical):** 80 hours = $8,000 - $16,000
- **Phase 2 (High):** 40 hours = $4,000 - $8,000
- **Phase 3 (Medium):** 40 hours = $4,000 - $8,000
- **Total:** 160 hours = $16,000 - $32,000

### Third-Party Services (Annual)
- Tax calculation: $1,200 - $5,000/year
- PDF generation: $0 - $180/year
- Dunning (if using service): $0 - $3,600/year

---

## Risks

### High Risk
1. **Tax non-compliance** - Could result in fines and legal issues
2. **No invoices** - Unprofessional, illegal in some regions
3. **Failed payment recovery** - Direct revenue impact

### Medium Risk
4. **No refunds** - Customer service burden, poor UX
5. **GDPR gaps** - Regulatory fines (up to 4% of revenue)

### Low Risk
6. **Missing features** - Can be added post-launch

---

## Recommendations

### Immediate Actions (Before Production)
1. ✅ Implement invoice generation (**3 days**)
2. ✅ Implement basic tax calculation (**4 days**)
3. ✅ Add dunning management (**3 days**)
4. ✅ Add refund handling (**2 days**)
5. ✅ Add billing notifications (**2 days**)

### Quick Wins
- Use Stripe Tax for automatic tax calculation
- Use Stripe's built-in invoicing
- Leverage Stripe's dunning features

### Alternative Approach
**Use Stripe Billing completely** instead of building custom:
- ✅ Invoices handled automatically
- ✅ Tax calculation built-in
- ✅ Dunning automated
- ✅ Refunds via dashboard
- ❌ Less control
- ❌ Vendor lock-in

---

## Conclusion

The current billing system has **good foundations** but is **not production-ready** due to critical gaps in:
1. Invoice generation
2. Tax compliance
3. Failed payment recovery
4. Refund handling

**Estimated time to production-ready:** 2-3 weeks of focused development

**Recommended path:** Implement Phase 1 (Critical) immediately, then evaluate using Stripe Billing for some features vs. custom implementation.

---

**Status:** Ready for stakeholder review  
**Next Steps:** Prioritize and schedule Phase 1 implementation

