"""
Credit Note service for issuing credits and refund documentation

A credit note is like a negative invoice - it documents money owed back to the customer.
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.orm import Session
import logging

from ..database import Organization
from ..db.models.billing_advanced import CreditNote
from ..db.models.invoice import Invoice, BillingAddress
from ..db.models.dunning import Refund

logger = logging.getLogger(__name__)


class CreditNoteService:
    """Service for creating and managing credit notes"""
    
    def __init__(self, db: Session):
        """Initialize credit note service"""
        self.db = db
    
    def create_credit_note(
        self,
        organization_id: int,
        amount: Decimal,
        credit_type: str,
        reason: str,
        invoice_id: Optional[int] = None,
        refund_id: Optional[int] = None,
        reason_details: Optional[str] = None,
        line_items: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[int] = None,
    ) -> CreditNote:
        """
        Create a credit note
        
        Args:
            organization_id: Organization ID
            amount: Credit amount (before tax)
            credit_type: Type (refund, adjustment, proration, goodwill)
            reason: Reason code
            invoice_id: Related invoice (optional)
            refund_id: Related refund (optional)
            reason_details: Additional details
            line_items: Line items for credit note
            user_id: User creating credit note
        
        Returns:
            Created CreditNote
        """
        # Validate organization
        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        
        # Get billing address
        billing_address = self._get_billing_address(organization_id)
        
        # Get customer details
        customer_details = self._get_customer_details(org, billing_address)
        
        # Calculate tax (use same rate as original invoice if available)
        tax_rate = Decimal("0")
        if invoice_id:
            invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if invoice and invoice.tax_details:
                tax_rate = Decimal(str(invoice.tax_details.get("tax_rate", 0)))
        
        subtotal = amount
        tax_amount = (subtotal * tax_rate).quantize(Decimal("0.01"))
        total = subtotal + tax_amount
        
        # Process line items
        if not line_items:
            line_items = [{
                "description": f"Credit - {reason.replace('_', ' ').title()}",
                "quantity": 1,
                "unit_price": float(subtotal),
                "amount": float(subtotal)
            }]
        
        # Generate credit note number
        credit_note_number = self._generate_credit_note_number()
        
        # Create credit note
        credit_note = CreditNote(
            credit_note_number=credit_note_number,
            organization_id=organization_id,
            invoice_id=invoice_id,
            refund_id=refund_id,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            currency="USD",  # TODO: Get from organization/invoice
            credit_type=credit_type,
            reason=reason,
            reason_details=reason_details,
            status="issued",
            credit_note_date=datetime.utcnow(),
            line_items=line_items,
            customer_details=customer_details,
            created_by=user_id,
        )
        
        self.db.add(credit_note)
        self.db.commit()
        self.db.refresh(credit_note)
        
        logger.info(
            f"Created credit note {credit_note_number} for org {organization_id}, "
            f"amount: ${total:.2f}, type: {credit_type}"
        )
        
        # Generate PDF
        try:
            self._generate_pdf(credit_note)
        except Exception as e:
            logger.error(f"Failed to generate credit note PDF: {e}", exc_info=True)
        
        return credit_note
    
    def create_from_refund(self, refund: Refund) -> CreditNote:
        """
        Automatically create credit note from refund
        
        Args:
            refund: Refund object
        
        Returns:
            Created CreditNote
        """
        return self.create_credit_note(
            organization_id=refund.organization_id,
            amount=refund.amount,
            credit_type="refund",
            reason=refund.reason,
            invoice_id=refund.invoice_id,
            refund_id=refund.id,
            reason_details=refund.reason_details,
            line_items=[{
                "description": f"Refund - {refund.reason.replace('_', ' ').title()}",
                "quantity": 1,
                "unit_price": float(refund.amount),
                "amount": float(refund.amount)
            }]
        )
    
    def list_credit_notes(
        self,
        organization_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[CreditNote]:
        """List credit notes for organization"""
        query = self.db.query(CreditNote).filter(
            CreditNote.organization_id == organization_id
        )
        
        if status:
            query = query.filter(CreditNote.status == status)
        
        query = query.order_by(CreditNote.credit_note_date.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_credit_note(
        self,
        credit_note_id: int,
        organization_id: int
    ) -> Optional[CreditNote]:
        """Get credit note by ID"""
        return self.db.query(CreditNote).filter(
            CreditNote.id == credit_note_id,
            CreditNote.organization_id == organization_id
        ).first()
    
    def void_credit_note(
        self,
        credit_note_id: int,
        reason: Optional[str] = None
    ) -> CreditNote:
        """Void a credit note"""
        credit_note = self.db.query(CreditNote).filter(
            CreditNote.id == credit_note_id
        ).first()
        
        if not credit_note:
            raise ValueError(f"Credit note {credit_note_id} not found")
        
        if credit_note.status == "void":
            raise ValueError("Credit note already voided")
        
        credit_note.status = "void"
        credit_note.void_at = datetime.utcnow()
        
        if reason:
            credit_note.metadata = credit_note.metadata or {}
            credit_note.metadata["void_reason"] = reason
        
        self.db.commit()
        
        logger.info(f"Voided credit note {credit_note.credit_note_number}")
        
        return credit_note
    
    def _generate_credit_note_number(self) -> str:
        """Generate unique credit note number (CN-YYYY-NNNN)"""
        year = datetime.now().year
        prefix = f"CN-{year}-"
        
        # Find highest number for this year
        last_cn = self.db.query(CreditNote).filter(
            CreditNote.credit_note_number.like(f"{prefix}%")
        ).order_by(CreditNote.credit_note_number.desc()).first()
        
        if last_cn:
            last_number = int(last_cn.credit_note_number.split('-')[-1])
            next_number = last_number + 1
        else:
            next_number = 1
        
        return f"{prefix}{next_number:04d}"
    
    def _get_billing_address(self, organization_id: int) -> Optional[BillingAddress]:
        """Get billing address for organization"""
        return self.db.query(BillingAddress).filter(
            BillingAddress.organization_id == organization_id
        ).first()
    
    def _get_customer_details(
        self,
        org: Organization,
        billing_address: Optional[BillingAddress]
    ) -> Dict[str, Any]:
        """Get customer details snapshot"""
        if billing_address:
            return {
                "organization_id": org.id,
                "organization_name": org.name,
                "company_name": billing_address.company_name,
                "contact_name": billing_address.contact_name,
                "email": billing_address.email,
                "address_line1": billing_address.address_line1,
                "city": billing_address.city,
                "postal_code": billing_address.postal_code,
                "country_code": billing_address.country_code,
            }
        else:
            return {
                "organization_id": org.id,
                "organization_name": org.name,
                "email": org.owner_user.email if hasattr(org, 'owner_user') else None,
            }
    
    def _generate_pdf(self, credit_note: CreditNote):
        """Generate PDF for credit note"""
        try:
            from .invoice_generator import get_invoice_generator
            from .storage_provider import get_storage_provider
            
            generator = get_invoice_generator()
            
            # Adapt credit note data to invoice format (with negative amounts)
            invoice_data = {
                "invoice_number": credit_note.credit_note_number,
                "invoice_date": credit_note.credit_note_date.date().isoformat(),
                "due_date": credit_note.credit_note_date.date().isoformat(),
                "status": credit_note.status,
                "subtotal": -float(credit_note.subtotal),  # Negative
                "tax_amount": -float(credit_note.tax_amount),  # Negative
                "total": -float(credit_note.total),  # Negative
                "amount_paid": 0,
                "amount_due": -float(credit_note.total),  # Negative
                "currency": credit_note.currency,
                "memo": f"Credit Note - {credit_note.reason.replace('_', ' ').title()}",
            }
            
            # Generate PDF (will show as credit/negative invoice)
            pdf_bytes = generator.generate_invoice_pdf(
                invoice_data=invoice_data,
                customer_data=credit_note.customer_details,
                line_items=credit_note.line_items,
                tax_details=None
            )
            
            # Store PDF
            storage = get_storage_provider()
            filename = f"credit_notes/{credit_note.organization_id}/{credit_note.credit_note_number}.pdf"
            pdf_url = storage.put(filename, pdf_bytes, content_type="application/pdf")
            
            # Update credit note
            credit_note.pdf_url = pdf_url
            credit_note.pdf_generated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Generated PDF for credit note {credit_note.credit_note_number}")
            
        except Exception as e:
            logger.error(f"Failed to generate credit note PDF: {e}", exc_info=True)
            raise


def get_credit_note_service(db: Session) -> CreditNoteService:
    """Get credit note service instance"""
    return CreditNoteService(db)

