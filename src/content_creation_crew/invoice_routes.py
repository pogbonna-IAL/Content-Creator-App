"""
Invoice API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from decimal import Decimal
import logging

from .database import User, get_db, Organization
from .auth import get_current_user
from .services.invoice_service import InvoiceService
from .db.models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/invoices", tags=["invoices"])


class LineItemRequest(BaseModel):
    """Line item for invoice"""
    description: str = Field(..., max_length=500)
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(..., ge=0)


class CreateInvoiceRequest(BaseModel):
    """Request to create an invoice"""
    line_items: List[LineItemRequest] = Field(..., min_items=1)
    currency: str = Field(default="USD", max_length=3)
    invoice_date: Optional[date] = None
    due_days: int = Field(default=14, ge=0, le=365)
    notes: Optional[str] = Field(None, max_length=1000)
    memo: Optional[str] = Field(None, max_length=500)


class BillingAddressRequest(BaseModel):
    """Request to create/update billing address"""
    company_name: Optional[str] = Field(None, max_length=200)
    contact_name: str = Field(..., max_length=200)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address_line1: str = Field(..., max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: str = Field(..., max_length=20)
    country_code: str = Field(..., min_length=2, max_length=2)
    tax_id: Optional[str] = Field(None, max_length=50)
    tax_id_type: Optional[str] = Field(None, max_length=20)
    customer_type: str = Field(default="individual")
    tax_exempt: bool = Field(default=False)
    tax_exempt_reason: Optional[str] = Field(None, max_length=200)


class InvoiceResponse(BaseModel):
    """Invoice response"""
    id: int
    invoice_number: str
    organization_id: int
    subscription_id: Optional[int]
    subtotal: float
    tax_amount: float
    total: float
    amount_paid: float
    amount_due: float
    currency: str
    status: str
    invoice_date: str
    due_date: str
    paid_at: Optional[str]
    tax_details: Optional[dict]
    line_items: List[dict]
    customer_details: dict
    pdf_url: Optional[str]
    is_paid: bool
    is_overdue: bool
    created_at: str
    updated_at: str


@router.post("/", response_model=InvoiceResponse)
async def create_invoice(
    request: CreateInvoiceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new invoice
    
    Creates an invoice for the user's organization with automatic tax calculation
    based on the billing address.
    """
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    try:
        invoice_service = InvoiceService(db)
        
        # Convert line items
        line_items = [item.dict() for item in request.line_items]
        
        # Create invoice
        invoice = invoice_service.create_invoice(
            organization_id=org.id,
            subscription_id=None,  # Manual invoice
            line_items=line_items,
            currency=request.currency,
            invoice_date=request.invoice_date,
            due_days=request.due_days,
            notes=request.notes,
            memo=request.memo,
        )
        
        return invoice.to_dict()
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invoice"
        )


@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List invoices for the user's organization
    
    Query parameters:
    - status: Filter by status (draft, issued, paid, void, refunded)
    - limit: Maximum number of results (default 50)
    - offset: Pagination offset (default 0)
    """
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    try:
        invoice_service = InvoiceService(db)
        invoices = invoice_service.list_invoices(
            organization_id=org.id,
            status=status_filter,
            limit=min(limit, 100),  # Max 100
            offset=offset
        )
        
        return [invoice.to_dict() for invoice in invoices]
        
    except Exception as e:
        logger.error(f"Failed to list invoices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list invoices"
        )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get invoice by ID"""
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id, org.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return invoice.to_dict()


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download invoice PDF"""
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id, org.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if not invoice.pdf_url:
        # Generate PDF if not exists
        try:
            invoice_service._generate_and_store_pdf(invoice)
            db.refresh(invoice)
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate PDF"
            )
    
    # Get PDF from storage
    try:
        from .services.storage_provider import get_storage_provider
        storage = get_storage_provider()
        
        # Extract filename from URL
        filename = invoice.pdf_url.split('/')[-1] if '/' in invoice.pdf_url else invoice.pdf_url
        pdf_bytes = storage.get(f"invoices/{org.id}/{filename}")
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to download PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download PDF"
        )


@router.post("/{invoice_id}/send")
async def send_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send invoice via email"""
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id, org.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    try:
        success = invoice_service.send_invoice_email(invoice_id)
        
        if success:
            return {
                "status": "sent",
                "message": f"Invoice {invoice.invoice_number} sent successfully",
                "sent_to": invoice.customer_details.get('email')
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send invoice email"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to send invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invoice"
        )


@router.post("/{invoice_id}/void")
async def void_invoice(
    invoice_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Void an invoice"""
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id, org.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    try:
        voided_invoice = invoice_service.void_invoice(invoice_id, reason)
        return {
            "status": "voided",
            "invoice": voided_invoice.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Billing Address Routes
@router.get("/billing-address", response_model=dict)
async def get_billing_address(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get billing address for user's organization"""
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    try:
        invoice_service = InvoiceService(db)
        billing_address = invoice_service.get_or_create_billing_address(org.id)
        return billing_address.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to get billing address: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get billing address"
        )


@router.put("/billing-address", response_model=dict)
async def update_billing_address(
    request: BillingAddressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update billing address for user's organization"""
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    try:
        # Validate tax ID if provided
        if request.tax_id:
            from .services.tax_calculator import get_tax_calculator
            tax_calculator = get_tax_calculator()
            is_valid, error_msg = tax_calculator.validate_tax_id(
                request.tax_id,
                request.country_code,
                request.tax_id_type or "vat"
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tax ID: {error_msg}"
                )
        
        invoice_service = InvoiceService(db)
        billing_address = invoice_service.get_or_create_billing_address(
            org.id,
            address_data=request.dict()
        )
        
        return billing_address.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update billing address: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update billing address"
        )

