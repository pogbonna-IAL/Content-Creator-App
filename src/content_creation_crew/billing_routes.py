"""
Billing API routes - Subscription management and payment processing
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import json
import logging

from .database import User, get_db, Organization, Subscription
from .auth import get_current_user
from .services.billing_service import BillingService
from .services.billing_gateway import get_billing_gateway
from .db.models.subscription import SubscriptionPlan, PaymentProvider, SubscriptionStatus
from .config import config
from .middleware.csrf import verify_csrf_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/billing", tags=["billing"])


class UpgradeRequest(BaseModel):
    """Request to upgrade subscription"""
    plan: str = Field(..., description="Plan name: basic, pro, or enterprise")
    provider: str = Field(..., description="Payment provider: stripe, paystack, or bank_transfer")


class BankTransferRequest(BaseModel):
    """Request to create bank transfer subscription"""
    plan: str = Field(..., description="Plan name: basic, pro, or enterprise")
    reference: Optional[str] = Field(None, description="Payment reference number")


class SubscriptionResponse(BaseModel):
    """Subscription response model"""
    id: int
    plan: str
    status: str
    provider: Optional[str]
    current_period_end: datetime
    created_at: datetime
    updated_at: datetime


@router.post("/upgrade")
async def upgrade_subscription(
    request: UpgradeRequest,
    fastapi_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token")
):
    """
    Upgrade subscription to a new plan
    
    Rules:
    - Do not auto-upgrade without verified webhook/verification step
    - For bank_transfer: creates pending subscription that requires manual verification
    - For stripe/paystack: creates subscription that will be activated via webhook
    - Requires CSRF token for security
    """
    # Verify CSRF token for billing actions
    verify_csrf_token(fastapi_request, x_csrf_token)
    
    billing_service = BillingService(db)
    
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Validate plan
    try:
        plan = SubscriptionPlan(request.plan.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {request.plan}. Must be one of: free, basic, pro, enterprise"
        )
    
    # Validate provider
    try:
        provider = PaymentProvider(request.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {request.provider}. Must be one of: stripe, paystack, bank_transfer"
        )
    
    # Cancel existing active subscription
    existing = billing_service.get_active_subscription(org.id)
    if existing:
        billing_service.cancel_subscription(existing.id)
    
    # Create new subscription
    try:
        gateway = get_billing_gateway(provider.value, config)
        subscription = billing_service.create_subscription(org.id, plan, provider, gateway)
        
        # For bank transfer, return payment instructions
        if provider == PaymentProvider.STRIPE or provider == PaymentProvider.PAYSTACK:
            return {
                "subscription": SubscriptionResponse(
                    id=subscription.id,
                    plan=subscription.plan,
                    status=subscription.status,
                    provider=subscription.provider,
                    current_period_end=subscription.current_period_end,
                    created_at=subscription.created_at,
                    updated_at=subscription.updated_at
                ),
                "message": "Subscription created. Payment will be processed via webhook.",
                "requires_verification": False
            }
        else:  # bank_transfer
            payment_instructions = gateway._get_payment_instructions(plan.value)
            return {
                "subscription": SubscriptionResponse(
                    id=subscription.id,
                    plan=subscription.plan,
                    status="pending_verification",
                    provider=subscription.provider,
                    current_period_end=subscription.current_period_end,
                    created_at=subscription.created_at,
                    updated_at=subscription.updated_at
                ),
                "payment_instructions": payment_instructions,
                "message": "Subscription created. Please complete bank transfer and wait for verification.",
                "requires_verification": True
            }
    except Exception as e:
        logger.error(f"Subscription upgrade failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.post("/bank-transfer")
async def create_bank_transfer_request(
    request: BankTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a bank transfer subscription request
    
    Returns payment instructions and creates a pending subscription
    """
    billing_service = BillingService(db)
    
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Validate plan
    try:
        plan = SubscriptionPlan(request.plan.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {request.plan}"
        )
    
        # Create bank transfer subscription
        try:
            gateway = get_billing_gateway("bank_transfer", config)
            subscription = billing_service.create_subscription(org.id, plan, PaymentProvider.BANK_TRANSFER, gateway)
            
            # Override status to pending_verification for bank transfer
            subscription.status = "pending_verification"
            db.commit()
            db.refresh(subscription)
        
        payment_instructions = gateway._get_payment_instructions(plan.value)
        
        return {
            "subscription": SubscriptionResponse(
                id=subscription.id,
                plan=subscription.plan,
                status=subscription.status,
                provider=subscription.provider,
                current_period_end=subscription.current_period_end,
                created_at=subscription.created_at,
                updated_at=subscription.updated_at
            ),
            "payment_instructions": payment_instructions,
            "reference": request.reference
        }
    except Exception as e:
        logger.error(f"Bank transfer request failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bank transfer request: {str(e)}"
        )


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription"""
    billing_service = BillingService(db)
    
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    subscription = billing_service.get_active_subscription(org.id)
    
    if not subscription:
        # Return free tier
        return {
            "subscription": None,
            "plan": "free",
            "status": "active"
        }
    
    return {
        "subscription": SubscriptionResponse(
            id=subscription.id,
            plan=subscription.plan,
            status=subscription.status,
            provider=subscription.provider,
            current_period_end=subscription.current_period_end,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at
        )
    }


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel current subscription"""
    billing_service = BillingService(db)
    
    # Get user's organization
    org = db.query(Organization).filter(Organization.owner_user_id == current_user.id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    subscription = billing_service.get_active_subscription(org.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    cancelled = billing_service.cancel_subscription(subscription.id)
    
    return {
        "subscription": SubscriptionResponse(
            id=cancelled.id,
            plan=cancelled.plan,
            status=cancelled.status,
            provider=cancelled.provider,
            current_period_end=cancelled.current_period_end,
            created_at=cancelled.created_at,
            updated_at=cancelled.updated_at
        ),
        "message": "Subscription cancelled successfully"
    }


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stripe webhook endpoint with signature verification and replay protection
    """
    try:
        # Get signature from header
        signature = request.headers.get("stripe-signature")
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        # Get raw body
        body = await request.body()
        
        # Verify signature
        gateway = get_billing_gateway("stripe", config)
        if not gateway.verify_webhook_signature(body, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse event
        payload = json.loads(body.decode())
        parsed_event = gateway.parse_webhook_event(payload)
        
        # Process webhook
        billing_service = BillingService(db)
        subscription = billing_service.update_subscription_from_webhook(
            PaymentProvider.STRIPE,
            parsed_event["event_type"],
            parsed_event["provider_event_id"],
            parsed_event
        )
        
        return {"status": "ok", "processed": subscription is not None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stripe webhook processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post("/webhooks/paystack")
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Paystack webhook endpoint with signature verification and replay protection
    """
    try:
        # Get signature from header
        signature = request.headers.get("x-paystack-signature")
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing x-paystack-signature header"
            )
        
        # Get raw body
        body = await request.body()
        
        # Verify signature
        gateway = get_billing_gateway("paystack", config)
        if not gateway.verify_webhook_signature(body, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse event
        payload = json.loads(body.decode())
        parsed_event = gateway.parse_webhook_event(payload)
        
        # Process webhook
        billing_service = BillingService(db)
        subscription = billing_service.update_subscription_from_webhook(
            PaymentProvider.PAYSTACK,
            parsed_event["event_type"],
            parsed_event["provider_event_id"],
            parsed_event
        )
        
        return {"status": "ok", "processed": subscription is not None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Paystack webhook processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )
