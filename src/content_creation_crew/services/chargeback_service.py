"""
Chargeback service for handling payment disputes

Manages chargebacks when customers contest charges with their bank/card issuer.
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from ..database import Organization
from ..db.models.billing_advanced import Chargeback
from ..db.models.invoice import Invoice
from ..db.models.dunning import Refund

logger = logging.getLogger(__name__)


class ChargebackService:
    """
    Service for managing chargebacks and disputes
    
    Features:
    - Record chargebacks from payment provider webhooks
    - Track dispute status
    - Evidence submission workflow
    - Automatic refund processing
    - Fraud detection patterns
    """
    
    # Chargeback reason codes (Stripe standard)
    REASON_CODES = {
        "fraudulent": "Customer disputes the charge as fraudulent",
        "duplicate": "Customer claims to have been charged multiple times",
        "product_not_received": "Customer claims product/service not received",
        "product_unacceptable": "Product/service not as described",
        "subscription_canceled": "Subscription was cancelled but charged anyway",
        "credit_not_processed": "Customer claims refund not received",
        "general": "General dispute"
    }
    
    def __init__(self, db: Session):
        """Initialize chargeback service"""
        self.db = db
    
    def create_chargeback(
        self,
        invoice_id: int,
        organization_id: int,
        amount: Decimal,
        currency: str,
        reason: str,
        provider_chargeback_id: str,
        payment_provider: str = "stripe",
        evidence_due_date: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> Chargeback:
        """
        Create a chargeback record
        
        Args:
            invoice_id: Related invoice
            organization_id: Organization ID
            amount: Disputed amount
            currency: Currency code
            reason: Reason code
            provider_chargeback_id: Provider's chargeback ID
            payment_provider: Payment provider
            evidence_due_date: Deadline for evidence submission
            metadata: Additional data from provider
        
        Returns:
            Created Chargeback
        """
        # Validate invoice
        invoice = self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.organization_id == organization_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Check for duplicate
        existing = self.db.query(Chargeback).filter(
            Chargeback.provider_chargeback_id == provider_chargeback_id
        ).first()
        
        if existing:
            logger.warning(f"Chargeback {provider_chargeback_id} already exists")
            return existing
        
        # Set evidence due date (typically 7-21 days)
        if evidence_due_date is None:
            evidence_due_date = datetime.utcnow() + timedelta(days=14)
        
        # Create chargeback
        chargeback = Chargeback(
            invoice_id=invoice_id,
            organization_id=organization_id,
            amount=amount,
            currency=currency,
            reason=reason,
            status="open",
            provider_chargeback_id=provider_chargeback_id,
            payment_provider=payment_provider,
            disputed_at=datetime.utcnow(),
            evidence_due_date=evidence_due_date,
            metadata=metadata or {}
        )
        
        self.db.add(chargeback)
        
        # Update invoice status
        invoice.status = "disputed"
        
        self.db.commit()
        self.db.refresh(chargeback)
        
        logger.warning(
            f"Chargeback created: {provider_chargeback_id} "
            f"for invoice {invoice.invoice_number}, "
            f"amount: ${amount} {currency}, reason: {reason}"
        )
        
        # Send alert email to admin/accounting
        try:
            self._send_chargeback_alert(chargeback, invoice)
        except Exception as e:
            logger.error(f"Failed to send chargeback alert: {e}")
        
        # Check for fraud patterns
        self._check_fraud_patterns(organization_id)
        
        return chargeback
    
    def submit_evidence(
        self,
        chargeback_id: int,
        evidence: Dict[str, Any],
        submitted_by: Optional[int] = None
    ) -> Chargeback:
        """
        Submit evidence for a chargeback dispute
        
        Args:
            chargeback_id: Chargeback ID
            evidence: Evidence details (receipts, communication logs, etc.)
            submitted_by: User ID submitting evidence
        
        Returns:
            Updated Chargeback
        """
        chargeback = self.db.query(Chargeback).filter(
            Chargeback.id == chargeback_id
        ).first()
        
        if not chargeback:
            raise ValueError(f"Chargeback {chargeback_id} not found")
        
        if chargeback.status != "open":
            raise ValueError(f"Cannot submit evidence for chargeback with status {chargeback.status}")
        
        # Check deadline
        if datetime.utcnow() > chargeback.evidence_due_date:
            logger.warning(f"Evidence deadline passed for chargeback {chargeback_id}")
        
        # Update chargeback
        chargeback.evidence_details = evidence
        chargeback.evidence_submitted_at = datetime.utcnow()
        chargeback.status = "under_review"
        
        if submitted_by:
            chargeback.metadata = chargeback.metadata or {}
            chargeback.metadata["evidence_submitted_by"] = submitted_by
        
        self.db.commit()
        
        logger.info(f"Evidence submitted for chargeback {chargeback.provider_chargeback_id}")
        
        # Submit to payment provider
        try:
            self._submit_evidence_to_provider(chargeback, evidence)
        except Exception as e:
            logger.error(f"Failed to submit evidence to provider: {e}")
        
        return chargeback
    
    def update_chargeback_status(
        self,
        provider_chargeback_id: str,
        status: str,
        resolution: Optional[str] = None
    ) -> Chargeback:
        """
        Update chargeback status (called from webhook)
        
        Args:
            provider_chargeback_id: Provider's chargeback ID
            status: New status (won, lost, warning_closed)
            resolution: Resolution details
        
        Returns:
            Updated Chargeback
        """
        chargeback = self.db.query(Chargeback).filter(
            Chargeback.provider_chargeback_id == provider_chargeback_id
        ).first()
        
        if not chargeback:
            raise ValueError(f"Chargeback {provider_chargeback_id} not found")
        
        old_status = chargeback.status
        chargeback.status = status
        chargeback.resolved_at = datetime.utcnow()
        
        if resolution:
            chargeback.metadata = chargeback.metadata or {}
            chargeback.metadata["resolution"] = resolution
        
        # Get invoice
        invoice = chargeback.invoice
        
        if status == "won":
            # We won the dispute - restore invoice
            invoice.status = "paid"
            
            logger.info(
                f"Chargeback WON: {chargeback.provider_chargeback_id} "
                f"for invoice {invoice.invoice_number}"
            )
        
        elif status == "lost":
            # We lost - process refund if not already done
            invoice.status = "refunded"
            
            # Create refund record
            try:
                from .refund_service import get_refund_service
                refund_service = get_refund_service(self.db)
                
                refund_service.create_refund(
                    invoice_id=invoice.id,
                    amount=chargeback.amount,
                    reason="chargeback_lost",
                    reason_details=f"Lost chargeback dispute: {chargeback.reason}",
                    refund_method="chargeback",
                    user_id=None  # System-initiated
                )
            except Exception as e:
                logger.error(f"Failed to create refund for lost chargeback: {e}")
            
            logger.warning(
                f"Chargeback LOST: {chargeback.provider_chargeback_id} "
                f"for invoice {invoice.invoice_number}"
            )
        
        elif status == "warning_closed":
            # Warning closed without funds movement
            invoice.status = "paid"
            
            logger.info(
                f"Chargeback warning closed: {chargeback.provider_chargeback_id}"
            )
        
        self.db.commit()
        
        # Send notification
        try:
            self._send_resolution_notification(chargeback, status)
        except Exception as e:
            logger.error(f"Failed to send resolution notification: {e}")
        
        return chargeback
    
    def get_chargeback(
        self,
        chargeback_id: int,
        organization_id: int
    ) -> Optional[Chargeback]:
        """Get chargeback by ID"""
        return self.db.query(Chargeback).filter(
            Chargeback.id == chargeback_id,
            Chargeback.organization_id == organization_id
        ).first()
    
    def list_chargebacks(
        self,
        organization_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Chargeback]:
        """List chargebacks for organization"""
        query = self.db.query(Chargeback).filter(
            Chargeback.organization_id == organization_id
        )
        
        if status:
            query = query.filter(Chargeback.status == status)
        
        query = query.order_by(Chargeback.disputed_at.desc())
        query = query.limit(limit)
        
        return query.all()
    
    def get_chargeback_stats(
        self,
        organization_id: Optional[int] = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Get chargeback statistics
        
        Args:
            organization_id: Optional org filter
            days: Lookback period
        
        Returns:
            Chargeback statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(Chargeback).filter(
            Chargeback.disputed_at >= cutoff
        )
        
        if organization_id:
            query = query.filter(Chargeback.organization_id == organization_id)
        
        chargebacks = query.all()
        
        stats = {
            "total_chargebacks": len(chargebacks),
            "total_amount": sum(cb.amount for cb in chargebacks),
            "by_status": {},
            "by_reason": {},
            "win_rate": 0,
            "average_amount": 0
        }
        
        if chargebacks:
            stats["average_amount"] = float(stats["total_amount"] / len(chargebacks))
            
            # Count by status
            for cb in chargebacks:
                stats["by_status"][cb.status] = stats["by_status"].get(cb.status, 0) + 1
                stats["by_reason"][cb.reason] = stats["by_reason"].get(cb.reason, 0) + 1
            
            # Calculate win rate
            won = stats["by_status"].get("won", 0)
            lost = stats["by_status"].get("lost", 0)
            total_resolved = won + lost
            
            if total_resolved > 0:
                stats["win_rate"] = (won / total_resolved) * 100
        
        stats["total_amount"] = float(stats["total_amount"])
        
        return stats
    
    def _check_fraud_patterns(self, organization_id: int):
        """
        Check for fraud patterns (multiple chargebacks)
        
        If organization has high chargeback rate, flag for review
        """
        # Get chargebacks in last 90 days
        cutoff = datetime.utcnow() - timedelta(days=90)
        
        chargeback_count = self.db.query(Chargeback).filter(
            Chargeback.organization_id == organization_id,
            Chargeback.disputed_at >= cutoff
        ).count()
        
        # Flag if more than 3 chargebacks in 90 days
        if chargeback_count >= 3:
            logger.warning(
                f"FRAUD ALERT: Organization {organization_id} has "
                f"{chargeback_count} chargebacks in 90 days"
            )
            
            # In production: suspend account, notify fraud team, etc.
    
    def _send_chargeback_alert(self, chargeback: Chargeback, invoice: Invoice):
        """Send alert email about new chargeback"""
        # Would integrate with EmailProvider
        logger.info(
            f"Chargeback alert would be sent for {chargeback.provider_chargeback_id}"
        )
    
    def _send_resolution_notification(self, chargeback: Chargeback, status: str):
        """Send notification about chargeback resolution"""
        logger.info(
            f"Resolution notification would be sent: {status} "
            f"for {chargeback.provider_chargeback_id}"
        )
    
    def _submit_evidence_to_provider(self, chargeback: Chargeback, evidence: Dict):
        """Submit evidence to payment provider API"""
        # Would integrate with Stripe/Paystack dispute API
        logger.info(
            f"Evidence would be submitted to {chargeback.payment_provider} "
            f"for {chargeback.provider_chargeback_id}"
        )


def get_chargeback_service(db: Session) -> ChargebackService:
    """Get chargeback service instance"""
    return ChargebackService(db)

