# Invoicing & Tax Quick Start Guide

Quick reference for invoice and tax features.

---

## Installation

```bash
# Install dependencies
pip install reportlab

# Run database migration
alembic upgrade head
```

---

## Create Your First Invoice

### 1. Set Up Billing Address

```python
# Via API
PUT /v1/invoices/billing-address

{
  "contact_name": "John Doe",
  "email": "john@acme.com",
  "address_line1": "123 Main Street",
  "city": "Lagos",
  "postal_code": "100001",
  "country_code": "NG",
  "customer_type": "business",
  "tax_id": "12345678-0001"
}
```

### 2. Create Invoice

```python
# Via API
POST /v1/invoices/

{
  "line_items": [{
    "description": "Pro Plan - Monthly Subscription",
    "quantity": 1,
    "unit_price": 29.99
  }],
  "currency": "USD",
  "due_days": 14
}
```

### 3. Download PDF

```http
GET /v1/invoices/123/pdf
```

---

## Tax Calculation Examples

### Nigeria (7.5% VAT)
```python
from content_creation_crew.services.tax_calculator import get_tax_calculator
calculator = get_tax_calculator()

result = calculator.calculate_tax(
    amount=Decimal("100.00"),
    country_code="NG"
)
# tax_amount: 7.50, total: 107.50
```

### US California (7.25% Sales Tax)
```python
result = calculator.calculate_tax(
    amount=Decimal("100.00"),
    country_code="US",
    state_code="CA"
)
# tax_amount: 7.25, total: 107.25
```

### UK (20% VAT)
```python
result = calculator.calculate_tax(
    amount=Decimal("100.00"),
    country_code="GB"
)
# tax_amount: 20.00, total: 120.00
```

### Ireland B2B (Reverse Charge - 0%)
```python
result = calculator.calculate_tax(
    amount=Decimal("100.00"),
    country_code="IE",
    customer_type="business",
    tax_id="IE1234567T"
)
# tax_amount: 0.00, reverse_charge: True
```

---

## Common Tasks

### List All Invoices
```http
GET /v1/invoices/?limit=50&offset=0
```

### List Paid Invoices Only
```http
GET /v1/invoices/?status=paid
```

### Get Invoice Details
```http
GET /v1/invoices/123
```

### Send Invoice Email
```http
POST /v1/invoices/123/send
```

### Void Invoice
```http
POST /v1/invoices/123/void
```

---

## Tax ID Formats

### Nigeria TIN
- **Format:** `12345678-0001`
- **Pattern:** 8 digits, hyphen, 4 digits
- **Example:** `98765432-0010`

### US EIN
- **Format:** `12-3456789`
- **Pattern:** 2 digits, hyphen, 7 digits
- **Example:** `12-3456789`

### UK VAT
- **Format:** `GB123456789`
- **Pattern:** GB followed by 9 or 12 digits
- **Example:** `GB123456789`

### Ireland VAT
- **Format:** `IE1234567T`
- **Pattern:** IE followed by 7 digits and 1-2 letters
- **Example:** `IE1234567T`

---

## Troubleshooting

### No Tax Calculated
✅ **Solution:** Ensure billing address has valid country_code

### PDF Not Generated
✅ **Solution:** Check ReportLab is installed: `pip install reportlab`

### Invalid Tax ID
✅ **Solution:** Use correct format for country (see Tax ID Formats above)

### Invoice Not Created from Webhook
✅ **Solution:** Check webhook logs and verify signature

---

## API Response Examples

### Invoice Created
```json
{
  "id": 123,
  "invoice_number": "INV-2026-0001",
  "organization_id": 1,
  "subtotal": 100.00,
  "tax_amount": 7.50,
  "total": 107.50,
  "currency": "USD",
  "status": "issued",
  "invoice_date": "2026-01-14",
  "due_date": "2026-01-28",
  "pdf_url": "https://storage/invoices/1/INV-2026-0001.pdf",
  "is_paid": false,
  "is_overdue": false,
  "tax_details": {
    "tax_name": "VAT",
    "tax_rate": 0.075,
    "tax_jurisdiction": "Nigeria"
  }
}
```

---

## Need Help?

- **Full Documentation:** [INVOICING-TAX-IMPLEMENTATION.md](./INVOICING-TAX-IMPLEMENTATION.md)
- **Gaps Analysis:** [BILLING-INVOICING-GAPS-ANALYSIS.md](./BILLING-INVOICING-GAPS-ANALYSIS.md)
- **Support:** billing@contentcrew.ai

