"""
Refund API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
import logging

from .database import User, get_db, Organization
from .auth import get_current_user
from .services.refund_service import RefundService, get_refund_service
from .db.models.dunning import Refund

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/refunds", tags=["refunds"])


class RefundRequest(BaseModel):
    """Request to create a refund"""
    subscription_id: Optional[int] = Field(None, description="Subscription ID to refund")
    invoice_id: Optional[int] = Field(None, description="Invoice ID to refund")
    amount: Optional[float] = Field(None, description="Specific amount to refund (for partial refunds)")
    reason: str = Field(default="customer_request", description="Refund reason: customer_request, duplicate, fraud, other")
    reason_details: Optional[str] = Field(None, max_length=500, description="Additional details about the refund")


class RefundResponse(BaseModel):
    """Refund response"""
    id: int
    organization_id: int
    subscription_id: Optional[int]
    invoice_id: Optional[int]
    amount: float
    currency: str
    refund_type: str
    reason: str
    reason_details: Optional[str]
    status: str
    provider: str
    provider_refund_id: Optional[str]
    is_within_refund_window: bool
    refund_window_days: Optional[int]
    days_since_payment: Optional[int]
    requested_at: str
    processed_at: Optional[str]
    
    class Config:
        from_attributes = True


@router.post("/", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def request_refund(
    request: RefundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request a refund
    
    Validates refund policy and processes refund automatically if allowed.
    
    **Refund Policy:**
    - 0-14 days: Full refund
    - 15-30 days: Prorated refund (annual plans only)
    - 30+ days: No refund
    
    **Reasons:**
    - `customer_request`: Customer requested refund
    - `duplicate`: Duplicate payment
    - `fraud`: Fraudulent transaction
    - `other`: Other reason
    """
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Validate request
    if not request.subscription_id and not request.invoice_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either subscription_id or invoice_id must be provided"
        )
    
    try:
        refund_service = get_refund_service(db)
        
        # Create refund
        refund = refund_service.request_refund(
            organization_id=org.id,
            subscription_id=request.subscription_id,
            invoice_id=request.invoice_id,
            amount=Decimal(str(request.amount)) if request.amount else None,
            reason=request.reason,
            reason_details=request.reason_details,
            requested_by=current_user.id,
        )
        
        return _refund_to_response(refund)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create refund: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process refund request"
        )


@router.get("/", response_model=List[RefundResponse])
async def list_refunds(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List refunds for the user's organization
    
    Query parameters:
    - status: Filter by status (pending, processing, succeeded, failed, cancelled)
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
        refund_service = get_refund_service(db)
        refunds = refund_service.list_refunds(
            organization_id=org.id,
            status=status_filter,
            limit=min(limit, 100),  # Max 100
            offset=offset
        )
        
        return [_refund_to_response(refund) for refund in refunds]
        
    except Exception as e:
        logger.error(f"Failed to list refunds: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list refunds"
        )


@router.get("/{refund_id}", response_model=RefundResponse)
async def get_refund(
    refund_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get refund details by ID"""
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    refund_service = get_refund_service(db)
    refund = refund_service.get_refund(refund_id, org.id)
    
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    
    return _refund_to_response(refund)


@router.post("/{refund_id}/cancel", response_model=RefundResponse)
async def cancel_refund(
    refund_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a pending refund
    
    Only refunds in 'pending' or 'processing' status can be cancelled.
    """
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Verify refund belongs to organization
    refund_service = get_refund_service(db)
    refund = refund_service.get_refund(refund_id, org.id)
    
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    
    try:
        cancelled_refund = refund_service.cancel_refund(refund_id)
        return _refund_to_response(cancelled_refund)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to cancel refund: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel refund"
        )


def _refund_to_response(refund: Refund) -> RefundResponse:
    """Convert Refund model to response"""
    return RefundResponse(
        id=refund.id,
        organization_id=refund.organization_id,
        subscription_id=refund.subscription_id,
        invoice_id=refund.invoice_id,
        amount=float(refund.amount),
        currency=refund.currency,
        refund_type=refund.refund_type,
        reason=refund.reason,
        reason_details=refund.reason_details,
        status=refund.status,
        provider=refund.provider,
        provider_refund_id=refund.provider_refund_id,
        is_within_refund_window=refund.is_within_refund_window,
        refund_window_days=refund.refund_window_days,
        days_since_payment=refund.days_since_payment,
        requested_at=refund.requested_at.isoformat(),
        processed_at=refund.processed_at.isoformat() if refund.processed_at else None,
    )

