"""
Invoice service for creating and managing invoices
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from ..db.models.invoice import Invoice, InvoiceStatus, BillingAddress
from ..database import Organization, Subscription
from ..services.tax_calculator import get_tax_calculator, TaxResult
from ..services.invoice_generator import get_invoice_generator
from ..services.storage_provider import get_storage_provider

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for managing invoices"""
    
    def __init__(self, db: Session):
        """Initialize invoice service"""
        self.db = db
        self.tax_calculator = get_tax_calculator()
    
    def create_invoice(
        self,
        organization_id: int,
        subscription_id: Optional[int],
        line_items: List[Dict[str, Any]],
        currency: str = "USD",
        invoice_date: Optional[date] = None,
        due_days: int = 14,
        notes: Optional[str] = None,
        memo: Optional[str] = None,
        provider: Optional[str] = None,
        provider_invoice_id: Optional[str] = None,
    ) -> Invoice:
        """
        Create a new invoice
        
        Args:
            organization_id: Organization ID
            subscription_id: Optional subscription ID
            line_items: List of line items [{"description": "...", "quantity": 1, "unit_price": 29.99}]
            currency: Currency code (USD, EUR, GBP, NGN)
            invoice_date: Invoice date (defaults to today)
            due_days: Days until due (default 14)
            notes: Internal notes
            memo: Customer-visible memo
            provider: Payment provider
            provider_invoice_id: External invoice ID
        
        Returns:
            Created Invoice object
        """
        # Validate organization
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        
        # Get or create billing address
        billing_address = self._get_or_create_billing_address(org)
        
        # Calculate subtotal
        subtotal = Decimal("0")
        processed_items = []
        
        for item in line_items:
            quantity = Decimal(str(item.get('quantity', 1)))
            unit_price = Decimal(str(item.get('unit_price', 0)))
            amount = quantity * unit_price
            subtotal += amount
            
            processed_items.append({
                "description": item.get('description', ''),
                "quantity": float(quantity),
                "unit_price": float(unit_price),
                "amount": float(amount),
            })
        
        # Calculate tax
        tax_result = self._calculate_tax_for_organization(billing_address, subtotal)
        
        # Generate invoice number
        invoice_number = self._generate_invoice_number()
        
        # Set dates
        if invoice_date is None:
            invoice_date = date.today()
        due_date = invoice_date + timedelta(days=due_days)
        
        # Calculate totals
        total = subtotal + tax_result.tax_amount
        amount_due = total
        
        # Get customer details snapshot
        customer_details = self._get_customer_details(org, billing_address)
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            organization_id=organization_id,
            subscription_id=subscription_id,
            subtotal=subtotal,
            tax_amount=tax_result.tax_amount,
            total=total,
            amount_paid=Decimal("0"),
            amount_due=amount_due,
            currency=currency,
            status=InvoiceStatus.ISSUED.value,
            invoice_date=invoice_date,
            due_date=due_date,
            tax_details=tax_result.to_dict(),
            line_items=processed_items,
            customer_details=customer_details,
            notes=notes,
            memo=memo,
            provider=provider,
            provider_invoice_id=provider_invoice_id,
        )
        
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        
        logger.info(f"Created invoice {invoice_number} for org {organization_id}, total: {total} {currency}")
        
        # Generate PDF asynchronously (don't block)
        try:
            self._generate_and_store_pdf(invoice)
        except Exception as e:
            logger.error(f"Failed to generate PDF for invoice {invoice.id}: {e}", exc_info=True)
        
        return invoice
    
    def get_invoice(self, invoice_id: int, organization_id: int) -> Optional[Invoice]:
        """Get invoice by ID (with org validation)"""
        return self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.organization_id == organization_id
        ).first()
    
    def list_invoices(
        self,
        organization_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Invoice]:
        """List invoices for an organization"""
        query = self.db.query(Invoice).filter(
            Invoice.organization_id == organization_id
        )
        
        if status:
            query = query.filter(Invoice.status == status)
        
        query = query.order_by(desc(Invoice.invoice_date))
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def mark_invoice_paid(
        self,
        invoice_id: int,
        amount_paid: Decimal,
        paid_at: Optional[datetime] = None
    ) -> Invoice:
        """Mark invoice as paid"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        invoice.amount_paid += amount_paid
        invoice.amount_due = invoice.total - invoice.amount_paid
        
        if invoice.amount_due <= Decimal("0"):
            invoice.status = InvoiceStatus.PAID.value
            invoice.paid_at = paid_at or datetime.utcnow()
            invoice.amount_due = Decimal("0")
        
        self.db.commit()
        self.db.refresh(invoice)
        
        logger.info(f"Marked invoice {invoice.invoice_number} paid: {amount_paid}")
        
        return invoice
    
    def void_invoice(self, invoice_id: int, reason: Optional[str] = None) -> Invoice:
        """Void an invoice"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        if invoice.status == InvoiceStatus.PAID.value:
            raise ValueError("Cannot void a paid invoice. Create a refund instead.")
        
        invoice.status = InvoiceStatus.VOID.value
        invoice.void_at = datetime.utcnow()
        if reason:
            invoice.notes = f"{invoice.notes or ''}\nVoid reason: {reason}".strip()
        
        self.db.commit()
        self.db.refresh(invoice)
        
        logger.info(f"Voided invoice {invoice.invoice_number}")
        
        return invoice
    
    def send_invoice_email(self, invoice_id: int) -> bool:
        """
        Send invoice via email
        
        Returns:
            True if sent successfully
        """
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Get customer email
        customer_email = invoice.customer_details.get('email')
        if not customer_email:
            raise ValueError("No customer email found")
        
        # Generate PDF if not exists
        if not invoice.pdf_url:
            self._generate_and_store_pdf(invoice)
        
        # Send email (implement email service integration)
        try:
            from ..services.email_provider import get_email_provider
            email_provider = get_email_provider()
            
            # Build email
            subject = f"Invoice {invoice.invoice_number} from {InvoiceGenerator.COMPANY_NAME}"
            body = self._build_invoice_email_body(invoice)
            
            # TODO: Attach PDF or include download link
            # For now, include link in email body
            
            email_provider.send_email(
                to=customer_email,
                subject=subject,
                body=body,
                html_body=self._build_invoice_email_html(invoice)
            )
            
            # Update tracking
            invoice.emailed_to = customer_email
            invoice.emailed_at = datetime.utcnow()
            invoice.email_count += 1
            self.db.commit()
            
            logger.info(f"Sent invoice {invoice.invoice_number} to {customer_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}", exc_info=True)
            return False
    
    def get_or_create_billing_address(
        self,
        organization_id: int,
        address_data: Optional[Dict[str, Any]] = None
    ) -> BillingAddress:
        """Get or create billing address for organization"""
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        
        billing_address = self.db.query(BillingAddress).filter(
            BillingAddress.organization_id == organization_id
        ).first()
        
        if billing_address and not address_data:
            return billing_address
        
        if not billing_address and not address_data:
            # Create default billing address from org owner
            user = org.owner_user if hasattr(org, 'owner_user') else None
            if not user:
                raise ValueError("No billing address and no owner user found")
            
            billing_address = BillingAddress(
                organization_id=organization_id,
                contact_name=user.name or user.email,
                email=user.email,
                address_line1="Not provided",
                city="Not provided",
                postal_code="00000",
                country_code="NG",  # Default to Nigeria
            )
            self.db.add(billing_address)
            self.db.commit()
            self.db.refresh(billing_address)
        
        elif address_data:
            # Create or update billing address
            if not billing_address:
                billing_address = BillingAddress(organization_id=organization_id)
                self.db.add(billing_address)
            
            # Update fields
            for key, value in address_data.items():
                if hasattr(billing_address, key):
                    setattr(billing_address, key, value)
            
            self.db.commit()
            self.db.refresh(billing_address)
        
        return billing_address
    
    def _get_or_create_billing_address(self, org: Organization) -> BillingAddress:
        """Internal helper to get or create billing address"""
        return self.get_or_create_billing_address(org.id)
    
    def _calculate_tax_for_organization(
        self,
        billing_address: BillingAddress,
        amount: Decimal
    ) -> TaxResult:
        """Calculate tax based on billing address"""
        return self.tax_calculator.calculate_tax(
            amount=amount,
            country_code=billing_address.country_code,
            state_code=billing_address.state_province,
            customer_type=billing_address.customer_type,
            tax_id=billing_address.tax_id,
            tax_exempt=billing_address.tax_exempt,
        )
    
    def _generate_invoice_number(self) -> str:
        """
        Generate unique invoice number
        
        Format: INV-YYYY-NNNN (e.g., INV-2026-0001)
        """
        year = datetime.now().year
        prefix = f"INV-{year}-"
        
        # Find highest number for this year
        last_invoice = self.db.query(Invoice).filter(
            Invoice.invoice_number.like(f"{prefix}%")
        ).order_by(desc(Invoice.invoice_number)).first()
        
        if last_invoice:
            # Extract number and increment
            last_number = int(last_invoice.invoice_number.split('-')[-1])
            next_number = last_number + 1
        else:
            next_number = 1
        
        return f"{prefix}{next_number:04d}"
    
    def _get_customer_details(
        self,
        org: Organization,
        billing_address: BillingAddress
    ) -> Dict[str, Any]:
        """Get customer details snapshot for invoice"""
        return {
            "organization_id": org.id,
            "organization_name": org.name,
            "company_name": billing_address.company_name,
            "contact_name": billing_address.contact_name,
            "email": billing_address.email,
            "phone": billing_address.phone,
            "address_line1": billing_address.address_line1,
            "address_line2": billing_address.address_line2,
            "city": billing_address.city,
            "state_province": billing_address.state_province,
            "postal_code": billing_address.postal_code,
            "country_code": billing_address.country_code,
            "tax_id": billing_address.tax_id,
            "tax_id_type": billing_address.tax_id_type,
        }
    
    def _generate_and_store_pdf(self, invoice: Invoice) -> str:
        """Generate PDF and store it"""
        try:
            invoice_generator = get_invoice_generator()
            
            # Generate PDF
            pdf_bytes = invoice_generator.generate_invoice_pdf(
                invoice_data={
                    "invoice_number": invoice.invoice_number,
                    "invoice_date": invoice.invoice_date.isoformat(),
                    "due_date": invoice.due_date.isoformat(),
                    "status": invoice.status,
                    "subtotal": float(invoice.subtotal),
                    "tax_amount": float(invoice.tax_amount),
                    "total": float(invoice.total),
                    "amount_paid": float(invoice.amount_paid),
                    "amount_due": float(invoice.amount_due),
                    "currency": invoice.currency,
                    "memo": invoice.memo,
                },
                customer_data=invoice.customer_details,
                line_items=invoice.line_items,
                tax_details=invoice.tax_details,
            )
            
            # Store PDF
            storage = get_storage_provider()
            filename = f"invoices/{invoice.organization_id}/{invoice.invoice_number}.pdf"
            pdf_url = storage.put(filename, pdf_bytes, content_type="application/pdf")
            
            # Update invoice
            invoice.pdf_url = pdf_url
            invoice.pdf_generated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Generated and stored PDF for invoice {invoice.invoice_number}")
            return pdf_url
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}", exc_info=True)
            raise
    
    def _build_invoice_email_body(self, invoice: Invoice) -> str:
        """Build plain text email body"""
        return f"""
Hello {invoice.customer_details.get('contact_name', 'Customer')},

Your invoice {invoice.invoice_number} is now available.

Amount Due: {invoice.currency} {invoice.total}
Due Date: {invoice.due_date}

You can view and download your invoice at:
[Invoice URL will be provided]

If you have any questions, please contact us at billing@contentcrew.ai

Thank you for your business!

Content Creation Crew
"""
    
    def _build_invoice_email_html(self, invoice: Invoice) -> str:
        """Build HTML email body"""
        return f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Invoice {invoice.invoice_number}</h2>
    <p>Hello {invoice.customer_details.get('contact_name', 'Customer')},</p>
    <p>Your invoice is now available.</p>
    
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Invoice Number:</td>
            <td style="padding: 8px;">{invoice.invoice_number}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Amount Due:</td>
            <td style="padding: 8px;">{invoice.currency} {invoice.total}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Due Date:</td>
            <td style="padding: 8px;">{invoice.due_date}</td>
        </tr>
    </table>
    
    <p>If you have any questions, please contact us at <a href="mailto:billing@contentcrew.ai">billing@contentcrew.ai</a></p>
    
    <p>Thank you for your business!</p>
    <p><strong>Content Creation Crew</strong></p>
</body>
</html>
"""

