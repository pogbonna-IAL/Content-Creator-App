"""
Payment Plan service for installment payments

Allows customers to split large payments into smaller installments.
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from ..database import Organization, Subscription
from ..db.models.billing_advanced import PaymentPlan, PaymentInstallment
from ..db.models.invoice import Invoice

logger = logging.getLogger(__name__)


class PaymentPlanService:
    """
    Service for creating and managing payment plans
    
    Features:
    - Split large invoices into installments
    - Automatic installment processing
    - Configurable down payment
    - Grace period for failed payments
    - Auto-retry on failure
    """
    
    # Default configurations
    DEFAULT_MIN_AMOUNT = Decimal("100.00")  # Minimum amount to allow payment plan
    DEFAULT_MAX_INSTALLMENTS = 12
    DEFAULT_DOWN_PAYMENT_PERCENT = Decimal("0.25")  # 25% down payment
    DEFAULT_GRACE_DAYS = 3
    
    def __init__(self, db: Session):
        """Initialize payment plan service"""
        self.db = db
    
    def create_payment_plan(
        self,
        invoice_id: int,
        organization_id: int,
        num_installments: int,
        down_payment_percent: Optional[Decimal] = None,
        first_installment_date: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> PaymentPlan:
        """
        Create a payment plan for an invoice
        
        Args:
            invoice_id: Invoice to split into installments
            organization_id: Organization ID
            num_installments: Number of installments (2-12)
            down_payment_percent: Down payment percentage (default 25%)
            first_installment_date: When first installment is due
            user_id: User creating the plan
        
        Returns:
            Created PaymentPlan
        """
        # Get invoice
        invoice = self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.organization_id == organization_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Validate amount
        if invoice.total < self.DEFAULT_MIN_AMOUNT:
            raise ValueError(
                f"Invoice amount must be at least ${self.DEFAULT_MIN_AMOUNT}"
            )
        
        # Validate installments
        if num_installments < 2 or num_installments > self.DEFAULT_MAX_INSTALLMENTS:
            raise ValueError(
                f"Number of installments must be between 2 and {self.DEFAULT_MAX_INSTALLMENTS}"
            )
        
        # Check if plan already exists
        existing = self.db.query(PaymentPlan).filter(
            PaymentPlan.invoice_id == invoice_id,
            PaymentPlan.status.in_(["active", "pending"])
        ).first()
        
        if existing:
            raise ValueError("Payment plan already exists for this invoice")
        
        # Calculate amounts
        down_payment_percent = down_payment_percent or self.DEFAULT_DOWN_PAYMENT_PERCENT
        
        down_payment = (invoice.total * down_payment_percent).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        remaining_amount = invoice.total - down_payment
        installment_amount = (remaining_amount / num_installments).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Adjust last installment for rounding
        last_installment_amount = remaining_amount - (installment_amount * (num_installments - 1))
        
        # Determine dates
        now = datetime.utcnow()
        if first_installment_date is None:
            first_installment_date = now + timedelta(days=30)
        
        # Create payment plan
        plan = PaymentPlan(
            invoice_id=invoice_id,
            organization_id=organization_id,
            total_amount=invoice.total,
            down_payment_amount=down_payment,
            remaining_amount=remaining_amount,
            installment_amount=installment_amount,
            num_installments=num_installments,
            installments_paid=0,
            currency=invoice.currency,
            status="pending",  # Pending until down payment received
            first_installment_date=first_installment_date,
            created_by=user_id
        )
        
        self.db.add(plan)
        self.db.flush()  # Get plan ID
        
        # Create installments
        installments = []
        for i in range(num_installments):
            due_date = first_installment_date + timedelta(days=30 * i)
            
            # Last installment gets adjusted amount
            amount = last_installment_amount if i == num_installments - 1 else installment_amount
            
            installment = PaymentInstallment(
                payment_plan_id=plan.id,
                installment_number=i + 1,
                amount=amount,
                due_date=due_date,
                status="pending"
            )
            
            self.db.add(installment)
            installments.append(installment)
        
        self.db.commit()
        self.db.refresh(plan)
        
        logger.info(
            f"Created payment plan {plan.id} for invoice {invoice_id}: "
            f"{num_installments} installments of ${installment_amount}"
        )
        
        return plan
    
    def process_down_payment(
        self,
        plan_id: int,
        payment_method_id: str,
        payment_provider: str = "stripe"
    ) -> Dict[str, Any]:
        """
        Process down payment for payment plan
        
        Args:
            plan_id: Payment plan ID
            payment_method_id: Payment method (Stripe PM ID)
            payment_provider: Payment provider (stripe/paystack)
        
        Returns:
            Payment result
        """
        plan = self.db.query(PaymentPlan).filter(
            PaymentPlan.id == plan_id
        ).first()
        
        if not plan:
            raise ValueError(f"Payment plan {plan_id} not found")
        
        if plan.status != "pending":
            raise ValueError(f"Payment plan status is {plan.status}, expected pending")
        
        # Process payment via billing gateway
        try:
            from .billing_gateway import get_billing_gateway
            
            gateway = get_billing_gateway(payment_provider)
            
            result = gateway.charge_customer(
                amount=float(plan.down_payment_amount),
                currency=plan.currency,
                payment_method_id=payment_method_id,
                description=f"Down payment for payment plan {plan.id}"
            )
            
            if result["status"] == "succeeded":
                # Update plan
                plan.status = "active"
                plan.down_payment_received_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(f"Down payment received for plan {plan.id}")
                
                return {
                    "success": True,
                    "plan_id": plan.id,
                    "amount_paid": float(plan.down_payment_amount),
                    "status": "active"
                }
            else:
                logger.warning(f"Down payment failed for plan {plan.id}: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Payment failed")
                }
        
        except Exception as e:
            logger.error(f"Failed to process down payment: {e}", exc_info=True)
            raise
    
    def process_installment(
        self,
        installment_id: int,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single installment payment
        
        Args:
            installment_id: Installment ID
            payment_method_id: Optional payment method (uses saved if not provided)
        
        Returns:
            Payment result
        """
        installment = self.db.query(PaymentInstallment).filter(
            PaymentInstallment.id == installment_id
        ).first()
        
        if not installment:
            raise ValueError(f"Installment {installment_id} not found")
        
        if installment.status == "paid":
            return {"success": True, "message": "Already paid"}
        
        # Get plan
        plan = installment.payment_plan
        
        # Get payment method (would come from organization's saved payment method)
        if not payment_method_id:
            # In production, retrieve from organization's default payment method
            raise ValueError("Payment method required")
        
        # Process payment
        try:
            from .billing_gateway import get_billing_gateway
            
            # Determine provider from plan metadata
            provider = plan.metadata.get("payment_provider", "stripe") if plan.metadata else "stripe"
            gateway = get_billing_gateway(provider)
            
            result = gateway.charge_customer(
                amount=float(installment.amount),
                currency=plan.currency,
                payment_method_id=payment_method_id,
                description=f"Installment {installment.installment_number}/{plan.num_installments} for plan {plan.id}"
            )
            
            if result["status"] == "succeeded":
                # Update installment
                installment.status = "paid"
                installment.paid_at = datetime.utcnow()
                installment.payment_gateway_id = result.get("transaction_id")
                
                # Update plan
                plan.installments_paid += 1
                
                # Check if completed
                if plan.installments_paid >= plan.num_installments:
                    plan.status = "completed"
                    plan.completed_at = datetime.utcnow()
                    
                    logger.info(f"Payment plan {plan.id} completed!")
                
                self.db.commit()
                
                return {
                    "success": True,
                    "installment_id": installment.id,
                    "amount_paid": float(installment.amount),
                    "installments_remaining": plan.num_installments - plan.installments_paid
                }
            else:
                # Record failure
                installment.retry_count = (installment.retry_count or 0) + 1
                installment.last_retry_at = datetime.utcnow()
                
                # Mark as failed if exceeded retries
                if installment.retry_count >= 3:
                    installment.status = "failed"
                    plan.status = "failed"
                
                self.db.commit()
                
                return {
                    "success": False,
                    "error": result.get("error", "Payment failed"),
                    "retry_count": installment.retry_count
                }
        
        except Exception as e:
            logger.error(f"Failed to process installment: {e}", exc_info=True)
            raise
    
    def process_due_installments(self) -> Dict[str, Any]:
        """
        Process all due installments (scheduled job)
        
        Returns:
            Processing summary
        """
        now = datetime.utcnow()
        
        # Find due installments
        due_installments = self.db.query(PaymentInstallment).join(
            PaymentPlan
        ).filter(
            PaymentPlan.status == "active",
            PaymentInstallment.status == "pending",
            PaymentInstallment.due_date <= now
        ).all()
        
        results = {
            "total": len(due_installments),
            "succeeded": 0,
            "failed": 0,
            "errors": []
        }
        
        for installment in due_installments:
            try:
                # Get organization's default payment method
                # In production, this would come from organization record
                plan = installment.payment_plan
                org = self.db.query(Organization).filter(
                    Organization.id == plan.organization_id
                ).first()
                
                if not org:
                    logger.warning(f"Organization {plan.organization_id} not found")
                    continue
                
                # Get payment method (would be stored on organization)
                payment_method_id = getattr(org, 'default_payment_method_id', None)
                
                if not payment_method_id:
                    logger.warning(
                        f"No payment method for org {org.id}, "
                        f"skipping installment {installment.id}"
                    )
                    continue
                
                # Process
                result = self.process_installment(
                    installment_id=installment.id,
                    payment_method_id=payment_method_id
                )
                
                if result["success"]:
                    results["succeeded"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "installment_id": installment.id,
                        "error": result.get("error")
                    })
            
            except Exception as e:
                logger.error(
                    f"Failed to process installment {installment.id}: {e}",
                    exc_info=True
                )
                results["failed"] += 1
                results["errors"].append({
                    "installment_id": installment.id,
                    "error": str(e)
                })
        
        logger.info(
            f"Processed {results['total']} due installments: "
            f"{results['succeeded']} succeeded, {results['failed']} failed"
        )
        
        return results
    
    def get_payment_plan(
        self,
        plan_id: int,
        organization_id: int
    ) -> Optional[PaymentPlan]:
        """Get payment plan by ID"""
        return self.db.query(PaymentPlan).filter(
            PaymentPlan.id == plan_id,
            PaymentPlan.organization_id == organization_id
        ).first()
    
    def list_payment_plans(
        self,
        organization_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[PaymentPlan]:
        """List payment plans for organization"""
        query = self.db.query(PaymentPlan).filter(
            PaymentPlan.organization_id == organization_id
        )
        
        if status:
            query = query.filter(PaymentPlan.status == status)
        
        query = query.order_by(PaymentPlan.created_at.desc())
        query = query.limit(limit)
        
        return query.all()
    
    def cancel_payment_plan(
        self,
        plan_id: int,
        reason: Optional[str] = None
    ) -> PaymentPlan:
        """Cancel a payment plan"""
        plan = self.db.query(PaymentPlan).filter(
            PaymentPlan.id == plan_id
        ).first()
        
        if not plan:
            raise ValueError(f"Payment plan {plan_id} not found")
        
        if plan.status in ["completed", "cancelled"]:
            raise ValueError(f"Cannot cancel plan with status {plan.status}")
        
        plan.status = "cancelled"
        plan.cancelled_at = datetime.utcnow()
        
        if reason:
            plan.metadata = plan.metadata or {}
            plan.metadata["cancellation_reason"] = reason
        
        # Cancel pending installments
        pending_installments = self.db.query(PaymentInstallment).filter(
            PaymentInstallment.payment_plan_id == plan.id,
            PaymentInstallment.status == "pending"
        ).all()
        
        for installment in pending_installments:
            installment.status = "cancelled"
        
        self.db.commit()
        
        logger.info(f"Cancelled payment plan {plan.id}")
        
        return plan


def get_payment_plan_service(db: Session) -> PaymentPlanService:
    """Get payment plan service instance"""
    return PaymentPlanService(db)

