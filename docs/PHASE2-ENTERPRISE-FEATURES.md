# Phase 2: Enterprise Billing Features
## Implementation Guide

**Date:** 2026-01-14  
**Status:** 🚧 Database Models Complete - Services In Progress  
**Version:** 2.0.0

---

## Overview

This document outlines the implementation of 7 enterprise-grade billing features that extend the core billing system with advanced capabilities for mid-market and enterprise customers.

### Features Implemented

| Feature | Status | Complexity | Est. Hours |
|---------|--------|------------|------------|
| 1. Proration Logic | 🟢 Models Ready | Medium | 24h |
| 2. Usage-Based Billing | 🟢 Models Ready | High | 40h |
| 3. Credit Notes | 🟢 Models Ready | Medium | 16h |
| 4. Multi-Currency | 🟢 Models Ready | Medium | 24h |
| 5. Payment Plans | 🟢 Models Ready | High | 32h |
| 6. Smart Retry Timing | 🟢 Models Ready | High | 40h |
| 7. Chargeback Handling | 🟢 Models Ready | Medium | 24h |
| **TOTAL** | | | **200h** |

---

## Feature 1: Proration Logic

### Overview

Automatically calculate credits and charges when customers upgrade/downgrade mid-cycle.

### How It Works

```
Scenario: Upgrade from Basic ($9.99/mo) to Pro ($29.99/mo) on Day 15 of 30

1. Calculate unused time on Basic:
   - Days used: 15
   - Days remaining: 15
   - Credit: $9.99 × (15/30) = $4.995

2. Calculate prorated charge for Pro:
   - Days remaining: 15
   - Charge: $29.99 × (15/30) = $14.995

3. Net amount:
   - Net charge: $14.995 - $4.995 = $10.00

Result: Customer pays $10.00 today for the upgrade
```

### Database Model

```python
class ProrationEvent:
    id: int
    subscription_id: int
    old_plan: str
    new_plan: str
    change_type: str  # upgrade, downgrade, lateral
    
    # Calculation
    days_in_period: int  # 30
    days_used: int  # 15
    days_remaining: int  # 15
    
    credit_amount: Decimal  # $4.995
    charge_amount: Decimal  # $14.995
    net_amount: Decimal  # $10.00
    
    status: str  # pending, applied, cancelled
```

### API Endpoints

```http
POST /v1/subscriptions/{id}/change-plan
Content-Type: application/json

{
  "new_plan": "pro",
  "effective_date": "immediate"  # or specific date
}

Response:
{
  "proration": {
    "old_plan": "basic",
    "new_plan": "pro",
    "credit_amount": 4.995,
    "charge_amount": 14.995,
    "net_amount": 10.00,
    "effective_date": "2026-01-15"
  },
  "next_invoice": {
    "amount": 10.00,
    "due_now": true
  }
}
```

### Implementation Steps

1. Create `ProrationService`
   - Calculate unused time
   - Calculate proration amounts
   - Generate adjustment invoice
   - Update subscription

2. Add API endpoint
   - Validate plan change
   - Preview proration
   - Confirm and apply

3. Integration
   - Wire to subscription service
   - Update invoice generation
   - Add webhook events

---

## Feature 2: Usage-Based Billing

### Overview

Charge customers based on actual usage (API calls, storage, compute time).

### Meter Types

1. **Counter** - Accumulating count (API calls)
2. **Gauge** - Current value (storage GB)
3. **Histogram** - Distribution (request latency)

### How It Works

```python
# Track usage
usage_service.record_usage(
    organization_id=1,
    meter_name="api_calls",
    value=1,
    metadata={"endpoint": "/v1/content/generate"}
)

# At end of billing period:
# - Total: 15,000 API calls
# - Included: 10,000 (free with Pro plan)
# - Overage: 5,000
# - Price: $0.01 per call
# - Charge: 5,000 × $0.01 = $50.00
```

### Database Models

```python
class UsageMeter:
    id: int
    organization_id: int
    meter_name: str  # api_calls, storage_gb, video_minutes
    meter_type: str  # counter, gauge, histogram
    
    # Current period
    period_value: Decimal  # 15,000
    included_units: Decimal  # 10,000
    unit_price: Decimal  # $0.01
    overage_price: Decimal  # $0.01
    
    period_start: datetime
    period_end: datetime

class UsageEvent:
    id: int
    meter_id: int
    event_type: str  # increment, decrement, set
    value: Decimal
    resource_id: str  # content_job_123
    event_time: datetime
```

### API Endpoints

```http
# Record usage
POST /v1/usage/record
{
  "meter": "api_calls",
  "value": 1,
  "resource_id": "content_job_123"
}

# Get current usage
GET /v1/usage/meters/{meter_name}
Response:
{
  "meter_name": "api_calls",
  "current_value": 15000,
  "included_units": 10000,
  "overage_units": 5000,
  "estimated_charge": 50.00,
  "period_end": "2026-02-01"
}

# Get usage history
GET /v1/usage/events?meter=api_calls&start=2026-01-01&end=2026-01-31
```

### Billing Integration

At end of billing period:
1. Calculate overages for all meters
2. Generate usage invoice line items
3. Add to subscription invoice
4. Reset meters for new period

---

## Feature 3: Credit Notes

### Overview

Issue credit memos for refunds, adjustments, and goodwill credits.

### Use Cases

- **Refunds**: Customer returns product
- **Adjustments**: Billing error correction
- **Proration**: Mid-cycle plan changes
- **Goodwill**: Service outage compensation

### How It Works

```
Customer paid: $100 invoice
Issue credit note: $30 (partial refund)
Options:
  1. Apply to next invoice (balance: $70 credit)
  2. Refund to payment method
  3. Issue as account credit
```

### Database Model

```python
class CreditNote:
    id: int
    credit_note_number: str  # CN-2026-0001
    organization_id: int
    invoice_id: int  # Original invoice
    refund_id: int  # If from refund
    
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    
    credit_type: str  # refund, adjustment, proration, goodwill
    reason: str
    status: str  # draft, issued, void
    
    line_items: JSONB
    pdf_url: str
```

### API Endpoints

```http
POST /v1/credit-notes/
{
  "invoice_id": 123,
  "amount": 30.00,
  "credit_type": "adjustment",
  "reason": "Billing error - prorated refund",
  "line_items": [{
    "description": "Pro Plan Credit",
    "amount": 30.00
  }]
}

GET /v1/credit-notes/{id}/pdf
# Downloads PDF credit note
```

---

## Feature 4: Multi-Currency Support

### Overview

Full support for EUR, GBP, NGN, USD with automatic conversion.

### Features

- Real-time exchange rates (daily updates)
- Display prices in customer's currency
- Charge in customer's currency
- Settlement in base currency (USD)
- Historical rate tracking

### Database Model

```python
class ExchangeRate:
    id: int
    from_currency: str  # USD
    to_currency: str  # EUR
    rate: Decimal  # 0.92
    source: str  # openexchangerates.org
    effective_date: datetime
```

### Supported Currencies

| Currency | Code | Symbol | Example Plan Price |
|----------|------|--------|-------------------|
| US Dollar | USD | $ | $29.99 |
| Euro | EUR | € | €27.59 (at 0.92 rate) |
| British Pound | GBP | £ | £23.69 (at 0.79 rate) |
| Nigerian Naira | NGN | ₦ | ₦46,485 (at 1,550 rate) |

### API Endpoints

```http
# Get current rates
GET /v1/currencies/rates
Response:
{
  "base_currency": "USD",
  "rates": {
    "EUR": 0.92,
    "GBP": 0.79,
    "NGN": 1550.00
  },
  "updated_at": "2026-01-14T00:00:00Z"
}

# Convert amount
GET /v1/currencies/convert?from=USD&to=EUR&amount=29.99
Response:
{
  "from_currency": "USD",
  "to_currency": "EUR",
  "from_amount": 29.99,
  "to_amount": 27.59,
  "rate": 0.92
}

# Create invoice in specific currency
POST /v1/invoices/
{
  "currency": "EUR",
  "line_items": [...]
}
```

### Exchange Rate Provider

```python
class ExchangeRateService:
    def get_rate(from_currency: str, to_currency: str) -> Decimal:
        """Get current exchange rate"""
        
    def update_rates() -> Dict[str, Decimal]:
        """Update all rates from provider (daily job)"""
        
    def convert(amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """Convert amount between currencies"""
```

### Scheduled Job

```python
# Update rates daily at midnight UTC
scheduler.add_job(
    func=update_exchange_rates,
    trigger=CronTrigger(hour=0, minute=0),
    id='exchange_rate_update'
)
```

---

## Feature 5: Payment Plans

### Overview

Allow customers to split large payments into installments.

### Use Cases

- **Annual subscriptions**: $299/year → $25.83/month × 12
- **Large invoices**: $1,000 → $250/week × 4
- **Upgrade costs**: $500 → $125/month × 4

### How It Works

```
Total: $1,200
Plan: 6 monthly installments
Amount per installment: $200

Schedule:
  Jan 15: $200 (due now)
  Feb 15: $200
  Mar 15: $200
  Apr 15: $200
  May 15: $200
  Jun 15: $200 (final)
```

### Database Models

```python
class PaymentPlan:
    id: int
    organization_id: int
    invoice_id: int
    
    total_amount: Decimal  # $1,200
    number_of_installments: int  # 6
    installment_amount: Decimal  # $200
    installment_frequency: str  # monthly
    
    amount_paid: Decimal  # $400 (2 paid)
    installments_paid: int  # 2
    installments_remaining: int  # 4
    
    status: str  # active, completed, defaulted
    next_payment_date: datetime

class PaymentInstallment:
    id: int
    payment_plan_id: int
    installment_number: int  # 1, 2, 3...
    amount: Decimal
    due_date: datetime
    status: str  # pending, paid, failed
    paid_at: datetime
```

### API Endpoints

```http
# Create payment plan
POST /v1/payment-plans/
{
  "invoice_id": 123,
  "number_of_installments": 6,
  "frequency": "monthly",
  "first_payment_date": "2026-01-15"
}

# Get payment plan
GET /v1/payment-plans/{id}
Response:
{
  "id": 456,
  "total_amount": 1200.00,
  "installments": 6,
  "installment_amount": 200.00,
  "amount_paid": 400.00,
  "installments_paid": 2,
  "next_payment_date": "2026-03-15",
  "status": "active",
  "schedule": [
    {"number": 1, "amount": 200, "due": "2026-01-15", "status": "paid"},
    {"number": 2, "amount": 200, "due": "2026-02-15", "status": "paid"},
    {"number": 3, "amount": 200, "due": "2026-03-15", "status": "pending"},
    ...
  ]
}
```

### Scheduled Job

```python
# Process due installments daily
scheduler.add_job(
    func=process_payment_plan_installments,
    trigger=CronTrigger(hour=2, minute=0),
    id='payment_plan_processing'
)
```

---

## Feature 6: Smart Retry Timing (AI-Powered)

### Overview

Use machine learning to predict optimal times to retry failed payments.

### How It Works

```python
# Traditional approach: Fixed schedule (Day 3, 7, 14)
# Success rate: 40-50%

# AI approach: Analyze patterns
features = {
    "day_of_week": "Monday",
    "time_of_day": "14:00",
    "failure_reason": "insufficient_funds",
    "customer_timezone": "EST",
    "payment_history": "3 previous failures",
    "account_age_days": 120,
    "last_successful_payment": "15 days ago"
}

prediction = ml_model.predict(features)
# Output: 78% success probability at 2026-01-16 15:00 EST

# Schedule retry at optimal time
```

### ML Model Features

**Input Features:**
- Day of week
- Time of day
- Customer timezone
- Failure reason
- Payment history
- Account age
- Last successful payment
- Subscription plan
- Customer industry

**Output:**
- Success probability (0-1)
- Recommended retry time
- Confidence score

### Database Model

```python
class DunningRetryPrediction:
    id: int
    dunning_process_id: int
    
    predicted_success_probability: Decimal  # 0.78
    recommended_retry_time: datetime
    confidence_score: Decimal  # 0.85
    
    features: JSONB  # Input features
    model_version: str  # "v1.2.3"
    
    # Actual outcome (for retraining)
    actual_success: bool
    actual_retry_time: datetime
```

### API Endpoints

```http
# Get prediction for dunning process
GET /v1/dunning/{id}/predict-retry
Response:
{
  "dunning_process_id": 123,
  "prediction": {
    "success_probability": 0.78,
    "recommended_time": "2026-01-16T15:00:00Z",
    "confidence": 0.85,
    "reason": "Customer historically pays on Tuesdays after 2pm"
  },
  "alternatives": [
    {"time": "2026-01-17T10:00:00Z", "probability": 0.72},
    {"time": "2026-01-16T09:00:00Z", "probability": 0.65}
  ]
}
```

### Model Training

```python
# Collect training data from historical dunning attempts
# Features: customer attributes, timing, payment history
# Labels: success/failure

# Retrain monthly
scheduler.add_job(
    func=retrain_retry_prediction_model,
    trigger=CronTrigger(day=1, hour=0),  # 1st of month
    id='ml_model_retrain'
)
```

### Expected Improvement

- **Current (Fixed Schedule):** 40-50% recovery rate
- **With AI Optimization:** 55-65% recovery rate
- **Revenue Impact:** +15-25% recovered revenue

---

## Feature 7: Chargeback Handling

### Overview

Manage disputes when customers contest charges with their bank.

### Chargeback Lifecycle

```
1. CHARGEBACK RECEIVED (from provider webhook)
   └─> Status: "pending"
   └─> Action: Alert team, gather evidence
   
2. SUBMIT EVIDENCE (within 7-14 days)
   └─> Upload: receipts, logs, TOS acceptance
   └─> Status: "evidence_submitted"
   
3. BANK REVIEW (2-4 weeks)
   └─> Provider investigates
   
4. OUTCOME
   ├─> WON: Funds returned, no action needed
   └─> LOST: Funds kept by customer, assess next steps
```

### Database Model

```python
class Chargeback:
    id: int
    organization_id: int
    invoice_id: int
    
    amount: Decimal
    currency: str
    
    provider: str  # stripe, paystack
    provider_chargeback_id: str
    
    reason: str  # fraudulent, duplicate, unrecognized
    status: str  # pending, won, lost, accepted
    
    chargeback_date: datetime
    respond_by_date: datetime  # Deadline to submit evidence
    resolved_at: datetime
    
    evidence_submitted: bool
    evidence_details: JSONB
    
    outcome: str  # won, lost
```

### API Endpoints

```http
# List chargebacks
GET /v1/chargebacks/?status=pending

# Get chargeback details
GET /v1/chargebacks/{id}

# Submit evidence
POST /v1/chargebacks/{id}/evidence
{
  "description": "Customer accessed service on 2026-01-10",
  "documents": [
    {"type": "access_log", "url": "https://..."},
    {"type": "tos_acceptance", "url": "https://..."},
    {"type": "invoice", "url": "https://..."}
  ],
  "customer_communication": [
    {"date": "2026-01-05", "message": "Initial support request"},
    {"date": "2026-01-12", "message": "Issue resolved"}
  ]
}

# Accept chargeback (don't fight it)
POST /v1/chargebacks/{id}/accept
{
  "reason": "Customer has valid dispute"
}
```

### Webhook Integration

```python
# Stripe webhook
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    event = stripe.Webhook.construct_event(...)
    
    if event.type == "charge.dispute.created":
        chargeback_service.create_from_webhook(event.data)
        
        # Alert team
        alert_service.send_alert(
            type="chargeback_received",
            severity="high",
            data=event.data
        )
```

### Prevention Strategies

1. **3D Secure**: Reduce fraud chargebacks
2. **Clear Billing Descriptor**: Reduce "unrecognized" disputes
3. **Excellent Support**: Resolve before escalation
4. **Clear TOS**: Document service usage
5. **Fraud Detection**: Block suspicious transactions

### Metrics

```prometheus
# Total chargebacks
chargebacks_total{status="pending"}
chargebacks_total{status="won"}
chargebacks_total{status="lost"}

# Win rate
chargeback_win_rate

# Response time
chargeback_response_time_hours
```

---

## Database Migration

### Create All Tables

```bash
# Create migration
alembic revision --autogenerate -m "add phase 2 enterprise features"

# Apply migration
alembic upgrade head
```

### Migration File Structure

```python
def upgrade():
    # Create proration_events table
    op.create_table('proration_events', ...)
    
    # Create usage_meters table
    op.create_table('usage_meters', ...)
    
    # Create usage_events table
    op.create_table('usage_events', ...)
    
    # Create credit_notes table
    op.create_table('credit_notes', ...)
    
    # Create payment_plans table
    op.create_table('payment_plans', ...)
    
    # Create payment_installments table
    op.create_table('payment_installments', ...)
    
    # Create chargebacks table
    op.create_table('chargebacks', ...)
    
    # Create exchange_rates table
    op.create_table('exchange_rates', ...)
    
    # Create dunning_retry_predictions table
    op.create_table('dunning_retry_predictions', ...)
```

---

## Configuration

### Environment Variables

```bash
# Proration
PRORATION_ENABLED=true
PRORATION_IMMEDIATE_CHARGE=true

# Usage Billing
USAGE_BILLING_ENABLED=true
USAGE_METER_PRECISION=4  # Decimal places

# Credit Notes
CREDIT_NOTE_AUTO_GENERATE=true

# Multi-Currency
BASE_CURRENCY=USD
SUPPORTED_CURRENCIES=USD,EUR,GBP,NGN
EXCHANGE_RATE_PROVIDER=openexchangerates
EXCHANGE_RATE_API_KEY=your_api_key

# Payment Plans
PAYMENT_PLANS_ENABLED=true
PAYMENT_PLAN_MIN_AMOUNT=500.00
PAYMENT_PLAN_MAX_INSTALLMENTS=12

# Smart Retry
ML_RETRY_PREDICTION_ENABLED=true
ML_MODEL_VERSION=v1.0.0

# Chargebacks
CHARGEBACK_AUTO_ALERT=true
CHARGEBACK_ALERT_EMAIL=billing-team@contentcrew.ai
```

---

## Deployment Strategy

### Phase 2A: Core Features (Week 1-2)
- ✅ Database models
- 🔄 Proration service
- 🔄 Credit notes service
- 🔄 Multi-currency service

### Phase 2B: Advanced Features (Week 3-4)
- 🔄 Usage billing service
- 🔄 Payment plans service
- 🔄 Chargeback handling

### Phase 2C: AI Features (Week 5-6)
- 🔄 ML model development
- 🔄 Smart retry integration
- 🔄 Model training pipeline

### Phase 2D: Testing & Polish (Week 7-8)
- 🔄 Integration tests
- 🔄 Load testing
- 🔄 Documentation
- 🔄 Deployment

---

## Estimated Timeline

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Proration & Credit Notes | Services + API |
| 2 | Multi-Currency | Exchange rates + conversion |
| 3 | Usage Billing | Metering + billing integration |
| 4 | Payment Plans | Service + scheduled processing |
| 5 | Chargeback Handling | Webhook + evidence submission |
| 6 | Smart Retry (ML) | Model + prediction API |
| 7 | Testing | Integration tests |
| 8 | Documentation & Deploy | Production deployment |

**Total: 8 weeks (200 hours)**

---

## Success Metrics

### Business Impact

- **Revenue Recovery:** +15-25% from smart retry
- **Customer Retention:** +10-15% from flexible payment options
- **Operational Efficiency:** -50% manual billing tasks
- **Market Expansion:** Support 4 currencies

### Technical Metrics

- **API Uptime:** 99.9%
- **Proration Accuracy:** 100%
- **Usage Metering Latency:** <100ms
- **ML Model Accuracy:** >70%
- **Chargeback Response Time:** <24 hours

---

## Next Steps

1. **Review & Approve** - Stakeholder approval for scope
2. **Prioritize** - Which features are most critical?
3. **Staffing** - Assign developers to features
4. **Timeline** - Confirm 8-week timeline or adjust
5. **Begin Development** - Start with Phase 2A

---

## Support

For questions about Phase 2 implementation:
- **Technical Lead:** [Your Name]
- **Email:** engineering@contentcrew.ai
- **Slack:** #billing-phase2

---

**Status:** 🚧 Database Models Complete - Ready for Service Development  
**Next Milestone:** Complete Proration Service (Week 1)


