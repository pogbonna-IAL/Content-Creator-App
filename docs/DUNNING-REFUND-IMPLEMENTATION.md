## 🎉 **Implementation Complete: Dunning & Refund Management**

**Date:** 2026-01-14  
**Status:** ✅ Production-Ready  
**Version:** 1.0.0

---

## Overview

Successfully implemented comprehensive dunning and refund management systems to recover failed payments and process customer refunds with full policy enforcement.

### Key Achievements

✅ **Dunning Management** - Automatic failed payment recovery with intelligent retry logic  
✅ **Refund Management** - Policy-based refund processing with provider integration  
✅ **Revenue Recovery** - Up to 21 days to recover failed payments  
✅ **Customer Retention** - Progressive communication before cancellation  
✅ **Compliance** - 14-day refund policy enforcement  

---

## Feature 3: Dunning Management

### Intelligent Retry Schedule

```
Day 0:  💔 Payment fails → Start dunning process
Day 3:  🔄 1st retry + "Payment Failed - Warning" email
Day 7:  🔄 2nd retry + "URGENT: Service at Risk" email
Day 14: 🔄 3rd retry + "FINAL NOTICE" email
Day 21: ❌ Cancel subscription + "Subscription Cancelled" email
```

### Features

**Automatic Payment Retries:**
- Smart retry timing (3, 7, 14 days)
- Off-session charging via Stripe/Paystack
- Tracks all retry attempts with success/failure
- Configurable max retries (default: 3)

**Progressive Email Notifications:**
- Initial failure notice
- Warning email (Day 3)
- Urgent notice (Day 7)  
- Final notice (Day 14)
- Cancellation confirmation (Day 21)

**Grace Period:**
- 21-day window before cancellation
- Service continues during recovery attempts
- Customer can update payment method anytime

**Complete Audit Trail:**
- All payment attempts logged
- Email delivery tracking
- Status changes recorded
- Metadata for analytics

### Database Models

#### `DunningProcess`
Manages the entire recovery workflow for a failed payment.

```python
class DunningProcess:
    id: int
    subscription_id: int
    organization_id: int
    status: str  # active, grace_period, recovering, recovered, cancelled, exhausted
    amount_due: Decimal
    amount_recovered: Decimal
    currency: str
    total_attempts: int
    total_emails_sent: int
    current_stage: str  # initial, warning_1, urgent, final_notice, cancellation
    started_at: datetime
    next_action_at: datetime  # When next action is due
    grace_period_ends_at: datetime
    will_cancel_at: datetime
    resolved_at: datetime
    cancelled_at: datetime
    cancellation_reason: str
```

#### `PaymentAttempt`
Tracks each individual payment retry attempt.

```python
class PaymentAttempt:
    id: int
    subscription_id: int
    dunning_process_id: int
    amount: Decimal
    currency: str
    status: str  # pending, processing, succeeded, failed, cancelled
    attempt_number: int
    is_automatic: bool
    provider: str  # stripe, paystack
    provider_payment_intent_id: str
    failure_code: str
    failure_message: str
    failure_reason: str  # card_declined, insufficient_funds, etc.
    next_retry_at: datetime
    retry_count: int
    attempted_at: datetime
    succeeded_at: datetime
    failed_at: datetime
```

#### `DunningNotification`
Tracks all email notifications sent during dunning.

```python
class DunningNotification:
    id: int
    dunning_process_id: int
    notification_type: str  # warning_1, urgent, final_notice
    sent_to: str
    subject: str
    sent_at: datetime
    delivered: bool
    opened: bool
    clicked: bool
```

### Usage Examples

#### Start Dunning Process (Automatic)

```python
from content_creation_crew.services.dunning_service import get_dunning_service

# Called automatically when payment fails via webhook
dunning = dunning_service.start_dunning_process(
    subscription_id=123,
    failed_payment_amount=Decimal("29.99"),
    currency="USD",
    failure_reason="card_declined",
    provider="stripe",
    provider_payment_intent_id="pi_xxxxx"
)
# Creates dunning process and schedules first retry for Day 3
```

#### Process Dunning Actions (Scheduled Job)

```python
# Runs hourly via APScheduler
stats = dunning_service.process_dunning_actions()

# Returns:
# {
#     "processed": 5,
#     "retries_attempted": 3,
#     "retries_succeeded": 1,
#     "retries_failed": 2,
#     "emails_sent": 2,
#     "subscriptions_cancelled": 0
# }
```

#### Cancel Dunning (Manual)

```python
# If customer updates payment method manually
dunning_service.cancel_dunning_process(
    process_id=123,
    reason="customer_updated_payment_method"
)
```

### Scheduled Job

Dunning processing runs **hourly** via APScheduler:

```python
# In scheduled_jobs.py
scheduler.add_job(
    func=run_dunning_processing_job,
    trigger=CronTrigger(minute=0),  # Every hour
    id='dunning_processing',
    name='Process dunning actions'
)
```

### Email Templates

All emails are sent via `EmailProvider` with professional formatting:

- **Initial Failure:** "We were unable to process your payment..."
- **Warning (Day 3):** "Payment Failed - First Reminder"
- **Urgent (Day 7):** "URGENT: Payment Failed - Service at Risk"
- **Final Notice (Day 14):** "FINAL NOTICE: Payment Required"
- **Cancellation (Day 21):** "Subscription Cancelled Due to Payment Failure"

### Metrics Tracked

```python
dunning_processing_runs_total
dunning_retries_total
dunning_retries_succeeded_total
dunning_emails_sent_total
dunning_cancellations_total
dunning_processing_errors_total
```

---

## Feature 4: Refund Management

### Refund Policy

```
0-14 days:    ✅ Full refund allowed
15-30 days:   ⚖️ Prorated refund (annual plans only)
30+ days:     ❌ No refund
```

### Prorated Refund Calculation

For annual subscriptions cancelled between 15-30 days:

```python
# Example: $299.99 annual plan, used 30 days
days_in_year = 365
days_used = 30
days_remaining = 365 - 30 = 335

refund_amount = $299.99 × (335/365) = $274.65

# Customer gets $274.65 back (91.6% of payment)
```

### Features

**Policy Enforcement:**
- Automatic validation of refund eligibility
- Time-based policy rules
- Plan-specific logic (monthly vs annual)
- Custom refund windows supported

**Provider Integration:**
- Stripe refund API
- Paystack refund API
- Bank transfer manual processing
- Reason code mapping

**Invoice Integration:**
- Updates invoice status to "refunded"
- Partial refund support
- Invoice amount adjustments
- Audit trail maintained

**Customer Communication:**
- Refund confirmation emails
- Processing time estimates
- Refund ID for tracking
- Professional email templates

### Database Model

#### `Refund`

```python
class Refund:
    id: int
    subscription_id: int
    invoice_id: int
    organization_id: int
    amount: Decimal
    currency: str
    refund_type: str  # full, partial, prorated
    reason: str  # customer_request, duplicate, fraud, other
    reason_details: str
    status: str  # pending, processing, succeeded, failed, cancelled
    provider: str
    provider_refund_id: str
    provider_charge_id: str
    is_within_refund_window: bool
    refund_window_days: int
    days_since_payment: int
    failure_reason: str
    requested_at: datetime
    processed_at: datetime
    requested_by: int  # User ID
```

### API Endpoints

#### Request Refund

```http
POST /v1/refunds/
Content-Type: application/json
Authorization: Bearer {token}

{
  "subscription_id": 123,
  "reason": "customer_request",
  "reason_details": "Not satisfied with service"
}
```

**Response:**
```json
{
  "id": 456,
  "organization_id": 1,
  "subscription_id": 123,
  "amount": 29.99,
  "currency": "USD",
  "refund_type": "full",
  "reason": "customer_request",
  "status": "succeeded",
  "provider": "stripe",
  "provider_refund_id": "re_xxxxx",
  "is_within_refund_window": true,
  "refund_window_days": 14,
  "days_since_payment": 7,
  "requested_at": "2026-01-14T10:00:00Z",
  "processed_at": "2026-01-14T10:00:05Z"
}
```

#### List Refunds

```http
GET /v1/refunds/?status=succeeded&limit=50
```

#### Get Refund

```http
GET /v1/refunds/{refund_id}
```

#### Cancel Refund

```http
POST /v1/refunds/{refund_id}/cancel
```

### Usage Examples

#### Request Full Refund

```python
from content_creation_crew.services.refund_service import get_refund_service

refund = refund_service.request_refund(
    organization_id=1,
    subscription_id=123,
    reason="customer_request",
    reason_details="Not satisfied with service"
)

# Automatically:
# 1. Validates policy (checks if within 14 days)
# 2. Calculates refund amount
# 3. Processes via Stripe/Paystack
# 4. Updates invoice status
# 5. Sends confirmation email
```

#### Request Partial Refund

```python
refund = refund_service.request_refund(
    organization_id=1,
    invoice_id=789,
    amount=Decimal("15.00"),  # Partial amount
    reason="duplicate"
)
```

#### Check Refund Policy

```python
from content_creation_crew.services.refund_service import RefundPolicy

can_refund, denial_reason, details = RefundPolicy.can_refund(
    payment_date=payment_date,
    amount=Decimal("29.99"),
    subscription_plan="pro"
)

if can_refund:
    print(f"Refund allowed: {details['refund_type']}")
    print(f"Amount: {details['refund_amount']}")
else:
    print(f"Refund denied: {denial_reason}")
```

### Refund Reasons

- `customer_request` - Customer requested refund
- `duplicate` - Duplicate payment
- `fraud` - Fraudulent transaction
- `other` - Other reason

---

## Billing Gateway Enhancements

Added two new methods to all gateway implementations:

### `charge_customer()`

Charges a customer's saved payment method (for dunning retries).

```python
gateway.charge_customer(
    customer_id="cus_xxxxx",
    amount=2999,  # In cents
    currency="USD",
    description="Retry payment for Pro Plan",
    metadata={"dunning_process_id": 123}
)

# Returns:
# {
#     "success": True/False,
#     "payment_intent_id": "pi_xxxxx",
#     "charge_id": "ch_xxxxx",
#     "failure_reason": "card_declined" (if failed)
# }
```

### `create_refund()`

Creates a refund for a previous charge.

```python
gateway.create_refund(
    charge_id="ch_xxxxx",
    amount=2999,  # In cents
    currency="USD",
    reason="customer_request",
    metadata={"refund_id": 456}
)

# Returns:
# {
#     "success": True/False,
#     "refund_id": "re_xxxxx",
#     "amount": 2999,
#     "status": "pending",
#     "error": "..." (if failed)
# }
```

### Implementation Details

**Stripe:**
- Uses `PaymentIntent.create()` with `off_session=True` for retries
- Uses `Refund.create()` for refunds
- Automatic payment method retrieval
- Error handling for card declines

**Paystack:**
- Uses `/transaction/charge_authorization` for retries
- Uses `/refund` endpoint for refunds
- Authorization code required
- Error handling with gateway responses

**Bank Transfer:**
- Returns manual processing required
- No automatic charging supported
- Refunds processed manually

---

## Testing

### Run Tests

```bash
# Dunning service tests
pytest tests/test_dunning_service.py -v

# Refund service tests
pytest tests/test_refund_service.py -v

# All tests
pytest tests/ -v -k "dunning or refund"
```

### Test Coverage

**Dunning Tests:**
- ✅ Start dunning process
- ✅ Existing dunning detection
- ✅ Retry schedule validation
- ✅ Successful payment retry
- ✅ Failed payment retry
- ✅ Cancel dunning process
- ✅ Process dunning actions

**Refund Tests:**
- ✅ Policy: Within window
- ✅ Policy: Outside window
- ✅ Policy: Prorated (annual)
- ✅ Policy: Past all windows
- ✅ Policy: Custom window
- ✅ Request refund
- ✅ Process refund success
- ✅ Process refund failure
- ✅ Cancel refund

---

## Configuration

### Environment Variables

```bash
# Dunning Configuration
DUNNING_GRACE_PERIOD_DAYS=21  # Days before cancellation
DUNNING_MAX_RETRIES=3  # Maximum retry attempts
DUNNING_RETRY_SCHEDULE="3,7,14"  # Days for retries

# Refund Configuration
REFUND_WINDOW_DAYS=14  # Full refund window
REFUND_PRORATED_THRESHOLD_DAYS=30  # Prorated window for annual
REFUND_AUTO_PROCESS=true  # Process immediately vs manual review

# Email Configuration
EMAIL_PROVIDER=smtp  # smtp, sendgrid, ses
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASS=your_password
```

### Service Configuration

```python
# In config.py
DUNNING_ENABLED = bool(os.getenv("DUNNING_ENABLED", "true"))
REFUND_ENABLED = bool(os.getenv("REFUND_ENABLED", "true"))
```

---

## Monitoring & Metrics

### Dunning Metrics

```prometheus
# Total dunning processing runs
dunning_processing_runs_total

# Payment retry attempts
dunning_retries_total

# Successful retries
dunning_retries_succeeded_total

# Emails sent
dunning_emails_sent_total

# Subscriptions cancelled
dunning_cancellations_total

# Processing errors
dunning_processing_errors_total
```

### Refund Metrics

```prometheus
# Total refunds requested
refunds_requested_total

# Refunds by status
refunds_total{status="succeeded"}
refunds_total{status="failed"}

# Refund amounts
refund_amount_total{currency="USD"}

# Processing time
refund_processing_seconds
```

### Alerts

**High Priority:**
```yaml
- alert: DunningProcessingFailed
  expr: increase(dunning_processing_errors_total[1h]) > 5
  severity: critical
  
- alert: HighRefundRate
  expr: rate(refunds_requested_total[24h]) > 10
  severity: warning
```

---

## Migration

### Database Migration

```bash
# Apply migration
alembic upgrade head

# Verify tables created
psql -d content_crew -c "\dt dunning*"
psql -d content_crew -c "\dt payment_attempts"
psql -d content_crew -c "\dt refunds"
```

### Existing Subscriptions

No migration needed for existing subscriptions. Dunning starts automatically on first payment failure.

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Run database migration
- [ ] Configure email provider
- [ ] Set environment variables
- [ ] Test Stripe webhook integration
- [ ] Test Paystack webhook integration
- [ ] Verify scheduled job registration
- [ ] Run integration tests

### Post-Deployment

- [ ] Monitor dunning processing job logs
- [ ] Verify email delivery
- [ ] Check Prometheus metrics
- [ ] Test refund flow end-to-end
- [ ] Monitor error rates
- [ ] Set up alerts

### Rollback Plan

If issues occur:
1. Stop scheduled jobs: `scheduler.pause()`
2. Manually process pending dunning
3. Review and fix issues
4. Resume: `scheduler.resume()`

---

## Troubleshooting

### Dunning Not Processing

**Check:**
1. Scheduler running: `scheduler.get_jobs()`
2. Database connectivity
3. Email provider configuration
4. Payment gateway credentials

**Logs:**
```bash
grep "dunning_processing" /var/log/api.log
```

### Refunds Failing

**Common Issues:**
1. Invalid charge ID
2. Charge already refunded
3. Insufficient balance (Stripe)
4. Provider API errors

**Solution:**
```python
# Check refund status
refund = db.query(Refund).filter(Refund.id == refund_id).first()
print(refund.failure_reason)
```

### Emails Not Sending

**Check:**
1. Email provider credentials
2. SMTP connectivity
3. Email queue
4. Rate limits

---

## Best Practices

### Dunning

1. **Monitor Recovery Rates:** Track % of payments recovered
2. **Test Email Templates:** Ensure they're user-friendly
3. **Update Payment Methods:** Provide easy update flow
4. **Communication:** Be professional and helpful
5. **Grace Period:** Give customers time to respond

### Refunds

1. **Process Quickly:** Automated processing preferred
2. **Clear Communication:** Explain timeline (5-10 days)
3. **Track Reasons:** Identify patterns
4. **Prevent Abuse:** Monitor refund rates
5. **Customer Service:** Offer alternatives before refunding

---

## Future Enhancements

### Phase 2 (Planned)

1. **Smart Retry Timing** - AI-powered optimal retry times
2. **Payment Method Update Links** - One-click update
3. **Partial Dunning** - Different strategies per plan
4. **Refund Analytics** - Dashboard with insights
5. **Chargeback Handling** - Dispute management
6. **Installment Plans** - Split payments for recovery

---

## Support

For questions or issues:
- **Email:** billing@contentcrew.ai
- **Documentation:** https://docs.contentcrew.ai/dunning-refunds
- **GitHub:** https://github.com/contentcrew/billing

---

## Change Log

### v1.0.0 (2026-01-14)
- ✅ Initial implementation
- ✅ Dunning management with intelligent retry
- ✅ Refund management with policy enforcement
- ✅ Stripe & Paystack integration
- ✅ Email notifications
- ✅ Scheduled jobs
- ✅ API endpoints
- ✅ Tests and documentation

---

**Status:** Production-Ready 🎉  
**Recovery Rate Target:** 40-60% of failed payments  
**Customer Satisfaction:** Professional communication + fair refund policy

