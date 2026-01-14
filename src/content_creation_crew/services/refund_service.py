"""
Refund service for processing customer refunds

Handles refund requests with policy enforcement and provider integration.
"""
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from ..db.models.dunning import Refund
from ..db.models.invoice import Invoice, InvoiceStatus
from ..database import Subscription, Organization
from ..services.billing_gateway import get_billing_gateway
from ..config import config

logger = logging.getLogger(__name__)


class RefundPolicy:
    """Refund policy enforcement"""
    
    # Default refund window (14 days)
    DEFAULT_REFUND_WINDOW_DAYS = 14
    
    # Prorated refund threshold (cancel mid-term)
    PRORATED_REFUND_THRESHOLD_DAYS = 30
    
    @staticmethod
    def can_refund(
        payment_date: datetime,
        amount: Decimal,
        subscription_plan: Optional[str] = None,
        refund_window_days: Optional[int] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check if refund is allowed per policy
        
        Returns:
            (is_allowed, denial_reason, refund_details)
        """
        if refund_window_days is None:
            refund_window_days = RefundPolicy.DEFAULT_REFUND_WINDOW_DAYS
        
        days_since_payment = (datetime.utcnow() - payment_date).days
        
        # Within refund window - full refund
        if days_since_payment <= refund_window_days:
            return True, None, {
                "refund_type": "full",
                "refund_amount": amount,
                "is_within_window": True,
                "days_since_payment": days_since_payment,
                "refund_window_days": refund_window_days,
            }
        
        # Outside window but < 30 days - prorated refund for annual subscriptions
        elif days_since_payment <= RefundPolicy.PRORATED_REFUND_THRESHOLD_DAYS:
            if subscription_plan and "annual" in subscription_plan.lower():
                # Calculate prorated amount
                days_used = days_since_payment
                days_in_year = 365
                prorated_amount = amount * (Decimal(days_in_year - days_used) / Decimal(days_in_year))
                
                return True, None, {
                    "refund_type": "prorated",
                    "refund_amount": prorated_amount,
                    "is_within_window": False,
                    "days_since_payment": days_since_payment,
                    "days_used": days_used,
                    "prorated_percentage": float((days_in_year - days_used) / days_in_year * 100),
                }
            else:
                return False, f"Refund window expired ({refund_window_days} days)", {
                    "is_within_window": False,
                    "days_since_payment": days_since_payment,
                }
        
        # Past all refund windows
        else:
            return False, f"Refund not available after {RefundPolicy.PRORATED_REFUND_THRESHOLD_DAYS} days", {
                "is_within_window": False,
                "days_since_payment": days_since_payment,
            }


class RefundService:
    """Service for processing refunds"""
    
    def __init__(self, db: Session):
        """Initialize refund service"""
        self.db = db
        self.policy = RefundPolicy()
    
    def request_refund(
        self,
        organization_id: int,
        subscription_id: Optional[int] = None,
        invoice_id: Optional[int] = None,
        amount: Optional[Decimal] = None,
        reason: str = "customer_request",
        reason_details: Optional[str] = None,
        requested_by: Optional[int] = None,
    ) -> Refund:
        """
        Request a refund
        
        Args:
            organization_id: Organization ID
            subscription_id: Optional subscription ID
            invoice_id: Optional invoice ID (if not subscription-based)
            amount: Optional specific amount (for partial refunds)
            reason: Refund reason code
            reason_details: Additional details
            requested_by: User ID who requested refund
        
        Returns:
            Created Refund object
        """
        # Validate organization
        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        
        # Get payment details
        if subscription_id:
            subscription = self.db.query(Subscription).filter(
                Subscription.id == subscription_id,
                Subscription.organization_id == organization_id
            ).first()
            
            if not subscription:
                raise ValueError(f"Subscription {subscription_id} not found")
            
            payment_date = subscription.created_at
            refund_amount = amount or self._get_subscription_amount(subscription)
            currency = "USD"  # TODO: Get from subscription
            provider = subscription.provider
            subscription_plan = subscription.plan
            
        elif invoice_id:
            invoice = self.db.query(Invoice).filter(
                Invoice.id == invoice_id,
                Invoice.organization_id == organization_id
            ).first()
            
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")
            
            if invoice.status != InvoiceStatus.PAID.value:
                raise ValueError(f"Cannot refund unpaid invoice")
            
            payment_date = invoice.paid_at or invoice.created_at
            refund_amount = amount or invoice.total
            currency = invoice.currency
            provider = invoice.provider or "stripe"
            subscription_plan = None
            
        else:
            raise ValueError("Either subscription_id or invoice_id must be provided")
        
        # Check refund policy
        can_refund, denial_reason, refund_details = self.policy.can_refund(
            payment_date=payment_date,
            amount=refund_amount,
            subscription_plan=subscription_plan,
        )
        
        if not can_refund:
            raise ValueError(f"Refund not allowed: {denial_reason}")
        
        # Adjust amount based on policy
        final_amount = refund_details["refund_amount"]
        refund_type = refund_details["refund_type"]
        
        # Create refund record
        refund = Refund(
            organization_id=organization_id,
            subscription_id=subscription_id,
            invoice_id=invoice_id,
            amount=final_amount,
            currency=currency,
            refund_type=refund_type,
            reason=reason,
            reason_details=reason_details,
            status="pending",
            provider=provider,
            is_within_refund_window=refund_details["is_within_window"],
            refund_window_days=RefundPolicy.DEFAULT_REFUND_WINDOW_DAYS,
            days_since_payment=refund_details.get("days_since_payment"),
            requested_by=requested_by,
        )
        
        self.db.add(refund)
        self.db.commit()
        self.db.refresh(refund)
        
        logger.info(f"Created refund request {refund.id} for org {organization_id}, amount: {final_amount} {currency}, type: {refund_type}")
        
        # Process refund immediately
        try:
            self.process_refund(refund.id)
        except Exception as e:
            logger.error(f"Failed to process refund {refund.id}: {e}", exc_info=True)
            refund.status = "failed"
            refund.failure_reason = str(e)
            self.db.commit()
        
        return refund
    
    def process_refund(self, refund_id: int) -> bool:
        """
        Process a refund through the payment provider
        
        Returns:
            True if successful
        """
        refund = self.db.query(Refund).filter(Refund.id == refund_id).first()
        
        if not refund:
            raise ValueError(f"Refund {refund_id} not found")
        
        if refund.status != "pending":
            logger.warning(f"Refund {refund_id} already processed: {refund.status}")
            return refund.status == "succeeded"
        
        try:
            # Update status
            refund.status = "processing"
            self.db.commit()
            
            # Get payment gateway
            gateway = get_billing_gateway(refund.provider, config)
            
            # Find charge ID to refund
            charge_id = self._get_charge_id(refund)
            
            if not charge_id:
                raise ValueError("No charge ID found for refund")
            
            # Process refund through provider
            result = gateway.create_refund(
                charge_id=charge_id,
                amount=int(float(refund.amount) * 100),  # Convert to cents
                currency=refund.currency,
                reason=refund.reason,
                metadata={
                    "refund_id": refund.id,
                    "organization_id": refund.organization_id,
                    "subscription_id": refund.subscription_id,
                    "invoice_id": refund.invoice_id,
                }
            )
            
            # Update refund record
            if result["success"]:
                refund.status = "succeeded"
                refund.provider_refund_id = result.get("refund_id")
                refund.processed_at = datetime.utcnow()
                
                logger.info(f"Refund {refund_id} processed successfully: {result.get('refund_id')}")
                
                # Update invoice status if applicable
                if refund.invoice_id:
                    self._update_invoice_for_refund(refund)
                
                # Send refund confirmation email
                try:
                    self._send_refund_confirmation(refund)
                except Exception as e:
                    logger.error(f"Failed to send refund confirmation: {e}", exc_info=True)
                
                self.db.commit()
                return True
            else:
                refund.status = "failed"
                refund.failure_reason = result.get("error", "Unknown error")
                
                logger.error(f"Refund {refund_id} failed: {result.get('error')}")
                
                self.db.commit()
                return False
        
        except Exception as e:
            logger.error(f"Error processing refund {refund_id}: {e}", exc_info=True)
            
            refund.status = "failed"
            refund.failure_reason = str(e)
            
            self.db.commit()
            return False
    
    def list_refunds(
        self,
        organization_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Refund]:
        """List refunds for an organization"""
        query = self.db.query(Refund).filter(
            Refund.organization_id == organization_id
        )
        
        if status:
            query = query.filter(Refund.status == status)
        
        query = query.order_by(Refund.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_refund(self, refund_id: int, organization_id: int) -> Optional[Refund]:
        """Get refund by ID"""
        return self.db.query(Refund).filter(
            Refund.id == refund_id,
            Refund.organization_id == organization_id
        ).first()
    
    def cancel_refund(self, refund_id: int) -> Refund:
        """Cancel a pending refund"""
        refund = self.db.query(Refund).filter(Refund.id == refund_id).first()
        
        if not refund:
            raise ValueError(f"Refund {refund_id} not found")
        
        if refund.status not in ["pending", "processing"]:
            raise ValueError(f"Cannot cancel refund with status: {refund.status}")
        
        refund.status = "cancelled"
        self.db.commit()
        
        logger.info(f"Cancelled refund {refund_id}")
        
        return refund
    
    def _get_subscription_amount(self, subscription: Subscription) -> Decimal:
        """Get subscription amount for refund"""
        # TODO: Get actual amount from subscription plan
        plan_amounts = {
            "free": Decimal("0"),
            "basic": Decimal("9.99"),
            "pro": Decimal("29.99"),
            "enterprise": Decimal("99.99"),
        }
        
        return plan_amounts.get(subscription.plan, Decimal("0"))
    
    def _get_charge_id(self, refund: Refund) -> Optional[str]:
        """Get charge ID for refund"""
        # Try to get from subscription
        if refund.subscription_id:
            subscription = refund.subscription
            if subscription and subscription.provider_subscription_id:
                # For Stripe, we might need to query the latest invoice
                return subscription.provider_subscription_id
        
        # Try to get from invoice
        if refund.invoice_id:
            invoice = refund.invoice
            if invoice and invoice.provider_payment_intent_id:
                return invoice.provider_payment_intent_id
        
        return None
    
    def _update_invoice_for_refund(self, refund: Refund):
        """Update invoice status after refund"""
        if not refund.invoice_id:
            return
        
        invoice = refund.invoice
        if invoice:
            if refund.amount >= invoice.total:
                invoice.status = InvoiceStatus.REFUNDED.value
            else:
                # Partial refund - update amounts
                invoice.amount_paid -= refund.amount
                invoice.amount_due += refund.amount
            
            logger.info(f"Updated invoice {invoice.id} for refund {refund.id}")
    
    def _send_refund_confirmation(self, refund: Refund):
        """Send refund confirmation email"""
        try:
            from ..services.email_provider import get_email_provider
            
            # Get organization and user email
            org = refund.organization
            if not org or not hasattr(org, 'owner_user'):
                logger.warning(f"Cannot send refund confirmation for refund {refund.id}: no organization or owner")
                return
            
            user = org.owner_user
            email = user.email
            
            # Build email
            subject = f"Refund Confirmed - {refund.currency} {refund.amount}"
            body = f"""
Hello,

Your refund has been processed successfully.

Refund Details:
- Amount: {refund.currency} {refund.amount}
- Type: {refund.refund_type.title()}
- Reason: {refund.reason.replace('_', ' ').title()}
- Refund ID: {refund.provider_refund_id}

The refund will appear in your account within 5-10 business days, depending on your financial institution.

If you have any questions, please contact our support team.

Best regards,
Content Creation Crew
            """
            
            # Send email
            email_provider = get_email_provider()
            email_provider.send_email(
                to=email,
                subject=subject,
                body=body
            )
            
            logger.info(f"Sent refund confirmation for refund {refund.id} to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send refund confirmation: {e}", exc_info=True)


def get_refund_service(db: Session) -> RefundService:
    """Get refund service instance"""
    return RefundService(db)

