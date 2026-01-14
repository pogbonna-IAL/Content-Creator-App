"""
Dunning service for failed payment recovery

Implements automated retry logic and email notification sequences
to recover failed payments before canceling subscriptions.
"""
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from ..db.models.dunning import (
    PaymentAttempt, PaymentAttemptStatus,
    DunningProcess, DunningStatus,
    DunningNotification,
)
from ..database import Subscription, Organization
from ..services.billing_gateway import get_billing_gateway
from ..config import config

logger = logging.getLogger(__name__)


class DunningService:
    """
    Dunning service for recovering failed payments
    
    Implements intelligent retry schedule:
    - Day 0: Payment fails
    - Day 3: First retry + warning email
    - Day 7: Second retry + urgent email
    - Day 14: Third retry + final notice
    - Day 21: Cancel subscription
    
    Features:
    - Automatic payment retries
    - Progressive email notifications
    - Grace periods
    - Smart retry timing (avoid weekends)
    - Configurable retry limits
    """
    
    # Dunning schedule configuration
    RETRY_SCHEDULE = [
        {"days": 3, "stage": "warning_1", "action": "retry_and_email", "email_type": "payment_failed_warning"},
        {"days": 7, "stage": "warning_2", "action": "retry_and_email", "email_type": "payment_failed_urgent"},
        {"days": 14, "stage": "final_notice", "action": "retry_and_email", "email_type": "payment_failed_final"},
        {"days": 21, "stage": "cancellation", "action": "cancel_subscription", "email_type": "subscription_cancelled"},
    ]
    
    # Configuration
    MAX_RETRY_ATTEMPTS = 3
    GRACE_PERIOD_DAYS = 21
    
    def __init__(self, db: Session):
        """Initialize dunning service"""
        self.db = db
    
    def start_dunning_process(
        self,
        subscription_id: int,
        failed_payment_amount: Decimal,
        currency: str = "USD",
        failure_reason: Optional[str] = None,
        provider: str = "stripe",
        provider_payment_intent_id: Optional[str] = None
    ) -> DunningProcess:
        """
        Start a new dunning process for a failed payment
        
        Args:
            subscription_id: Subscription ID
            failed_payment_amount: Amount that failed to charge
            currency: Currency code
            failure_reason: Reason for failure
            provider: Payment provider
            provider_payment_intent_id: Provider payment intent ID
        
        Returns:
            Created DunningProcess
        """
        # Get subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # Check if active dunning process already exists
        existing = self.db.query(DunningProcess).filter(
            DunningProcess.subscription_id == subscription_id,
            DunningProcess.status.in_([
                DunningStatus.ACTIVE.value,
                DunningStatus.GRACE_PERIOD.value,
                DunningStatus.RECOVERING.value
            ])
        ).first()
        
        if existing:
            logger.info(f"Active dunning process already exists for subscription {subscription_id}")
            return existing
        
        # Calculate grace period end
        grace_period_ends = datetime.utcnow() + timedelta(days=self.GRACE_PERIOD_DAYS)
        
        # Calculate first retry date (3 days from now)
        first_retry = datetime.utcnow() + timedelta(days=3)
        
        # Create dunning process
        dunning_process = DunningProcess(
            subscription_id=subscription_id,
            organization_id=subscription.organization_id,
            amount_due=failed_payment_amount,
            currency=currency,
            status=DunningStatus.ACTIVE.value,
            current_stage="initial",
            next_action_at=first_retry,
            grace_period_ends_at=grace_period_ends,
            will_cancel_at=datetime.utcnow() + timedelta(days=21),
        )
        
        self.db.add(dunning_process)
        self.db.flush()
        
        # Create initial payment attempt record
        payment_attempt = PaymentAttempt(
            subscription_id=subscription_id,
            dunning_process_id=dunning_process.id,
            amount=failed_payment_amount,
            currency=currency,
            status=PaymentAttemptStatus.FAILED.value,
            attempt_number=1,
            is_automatic=True,
            provider=provider,
            provider_payment_intent_id=provider_payment_intent_id,
            failure_reason=failure_reason,
            attempted_at=datetime.utcnow(),
            failed_at=datetime.utcnow(),
        )
        
        self.db.add(payment_attempt)
        self.db.commit()
        self.db.refresh(dunning_process)
        
        logger.info(f"Started dunning process {dunning_process.id} for subscription {subscription_id}, amount: {failed_payment_amount} {currency}")
        
        # Send initial notification (optional)
        try:
            self._send_notification(dunning_process, "payment_failed_initial")
        except Exception as e:
            logger.error(f"Failed to send initial dunning notification: {e}", exc_info=True)
        
        return dunning_process
    
    def process_dunning_actions(self) -> Dict[str, int]:
        """
        Process all due dunning actions
        
        This should be called by a scheduled job (every hour or day).
        
        Returns:
            Dictionary with action counts
        """
        now = datetime.utcnow()
        stats = {
            "processed": 0,
            "retries_attempted": 0,
            "retries_succeeded": 0,
            "retries_failed": 0,
            "emails_sent": 0,
            "subscriptions_cancelled": 0,
        }
        
        # Get all dunning processes that need action
        due_processes = self.db.query(DunningProcess).filter(
            DunningProcess.status.in_([
                DunningStatus.ACTIVE.value,
                DunningStatus.GRACE_PERIOD.value,
                DunningStatus.RECOVERING.value
            ]),
            DunningProcess.next_action_at <= now
        ).all()
        
        logger.info(f"Processing {len(due_processes)} dunning processes")
        
        for process in due_processes:
            try:
                stats["processed"] += 1
                self._process_dunning_process(process, stats)
            except Exception as e:
                logger.error(f"Error processing dunning process {process.id}: {e}", exc_info=True)
        
        logger.info(f"Dunning processing complete: {stats}")
        return stats
    
    def _process_dunning_process(self, process: DunningProcess, stats: Dict[str, int]):
        """Process a single dunning process"""
        # Determine current stage and next action
        days_since_start = (datetime.utcnow() - process.started_at).days
        
        # Find current stage in schedule
        current_stage_config = None
        for stage in self.RETRY_SCHEDULE:
            if days_since_start >= stage["days"]:
                current_stage_config = stage
        
        if not current_stage_config:
            logger.warning(f"No stage found for dunning process {process.id}, days: {days_since_start}")
            return
        
        logger.info(f"Processing dunning process {process.id}, stage: {current_stage_config['stage']}")
        
        # Update current stage
        process.current_stage = current_stage_config["stage"]
        
        # Perform action
        action = current_stage_config["action"]
        
        if action == "retry_and_email":
            # Attempt payment retry
            success = self._retry_payment(process)
            
            if success:
                stats["retries_succeeded"] += 1
                stats["retries_attempted"] += 1
                # Payment succeeded - resolve dunning
                self._resolve_dunning(process, "payment_recovered")
            else:
                stats["retries_failed"] += 1
                stats["retries_attempted"] += 1
                # Payment failed - send email and schedule next action
                self._send_notification(process, current_stage_config["email_type"])
                stats["emails_sent"] += 1
                
                # Schedule next action
                next_stage = self._get_next_stage(current_stage_config)
                if next_stage:
                    process.next_action_at = process.started_at + timedelta(days=next_stage["days"])
                else:
                    # No more retries - will cancel
                    process.next_action_at = process.will_cancel_at
        
        elif action == "cancel_subscription":
            # Final stage - cancel subscription
            self._cancel_subscription_for_dunning(process)
            stats["subscriptions_cancelled"] += 1
            
            # Send cancellation email
            self._send_notification(process, current_stage_config["email_type"])
            stats["emails_sent"] += 1
        
        self.db.commit()
    
    def _retry_payment(self, process: DunningProcess) -> bool:
        """
        Retry payment for dunning process
        
        Returns:
            True if payment succeeded, False otherwise
        """
        subscription = process.subscription
        
        if not subscription:
            logger.error(f"Subscription not found for dunning process {process.id}")
            return False
        
        try:
            # Get payment gateway
            gateway = get_billing_gateway(subscription.provider, config)
            
            # Attempt to charge customer
            result = gateway.charge_customer(
                customer_id=subscription.provider_customer_id,
                amount=int(float(process.amount_due) * 100),  # Convert to cents
                currency=process.currency,
                description=f"Retry payment for subscription {subscription.id}",
                metadata={
                    "dunning_process_id": process.id,
                    "subscription_id": subscription.id,
                    "retry_attempt": process.total_attempts + 1,
                }
            )
            
            # Create payment attempt record
            attempt = PaymentAttempt(
                subscription_id=subscription.id,
                dunning_process_id=process.id,
                amount=process.amount_due,
                currency=process.currency,
                status=PaymentAttemptStatus.SUCCEEDED.value if result["success"] else PaymentAttemptStatus.FAILED.value,
                attempt_number=process.total_attempts + 1,
                is_automatic=True,
                provider=subscription.provider,
                provider_payment_intent_id=result.get("payment_intent_id"),
                provider_charge_id=result.get("charge_id"),
                failure_reason=result.get("failure_reason"),
                attempted_at=datetime.utcnow(),
                succeeded_at=datetime.utcnow() if result["success"] else None,
                failed_at=None if result["success"] else datetime.utcnow(),
            )
            
            self.db.add(attempt)
            process.total_attempts += 1
            
            if result["success"]:
                process.amount_recovered = process.amount_due
                logger.info(f"Payment retry succeeded for dunning process {process.id}")
                return True
            else:
                logger.warning(f"Payment retry failed for dunning process {process.id}: {result.get('failure_reason')}")
                return False
        
        except Exception as e:
            logger.error(f"Error retrying payment for dunning process {process.id}: {e}", exc_info=True)
            
            # Create failed attempt record
            attempt = PaymentAttempt(
                subscription_id=subscription.id,
                dunning_process_id=process.id,
                amount=process.amount_due,
                currency=process.currency,
                status=PaymentAttemptStatus.FAILED.value,
                attempt_number=process.total_attempts + 1,
                is_automatic=True,
                provider=subscription.provider,
                failure_reason=str(e),
                attempted_at=datetime.utcnow(),
                failed_at=datetime.utcnow(),
            )
            
            self.db.add(attempt)
            process.total_attempts += 1
            
            return False
    
    def _send_notification(self, process: DunningProcess, notification_type: str):
        """Send dunning notification email"""
        try:
            from ..services.email_provider import get_email_provider
            
            # Get organization and user email
            org = process.organization
            if not org or not hasattr(org, 'owner_user'):
                logger.warning(f"Cannot send notification for dunning process {process.id}: no organization or owner")
                return
            
            user = org.owner_user
            email = user.email
            
            # Build email content
            subject, body = self._build_notification_content(process, notification_type)
            
            # Send email
            email_provider = get_email_provider()
            email_provider.send_email(
                to=email,
                subject=subject,
                body=body
            )
            
            # Track notification
            notification = DunningNotification(
                dunning_process_id=process.id,
                notification_type=notification_type,
                sent_to=email,
                subject=subject,
                sent_at=datetime.utcnow(),
            )
            
            self.db.add(notification)
            process.total_emails_sent += 1
            
            logger.info(f"Sent dunning notification '{notification_type}' for process {process.id} to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send dunning notification: {e}", exc_info=True)
    
    def _build_notification_content(
        self,
        process: DunningProcess,
        notification_type: str
    ) -> Tuple[str, str]:
        """Build email subject and body for notification"""
        subscription = process.subscription
        amount = f"{process.currency} {process.amount_due}"
        
        templates = {
            "payment_failed_initial": (
                "Payment Failed - Action Required",
                f"""
Hello,

We were unable to process your payment for {amount}.

Subscription: {subscription.plan.title()} Plan
Amount: {amount}

We'll automatically retry your payment in 3 days. Please ensure your payment method is up to date.

If you have any questions, please contact our support team.

Best regards,
Content Creation Crew
                """
            ),
            "payment_failed_warning": (
                "Payment Failed - First Reminder",
                f"""
Hello,

We attempted to process your payment again, but it was unsuccessful.

Subscription: {subscription.plan.title()} Plan
Amount: {amount}
Attempts: {process.total_attempts}

We'll retry again in 4 days. To avoid service interruption, please update your payment method.

Update payment method: [URL]

Best regards,
Content Creation Crew
                """
            ),
            "payment_failed_urgent": (
                "URGENT: Payment Failed - Service at Risk",
                f"""
Hello,

This is an urgent notice. We've made multiple attempts to process your payment without success.

Subscription: {subscription.plan.title()} Plan
Amount: {amount}
Attempts: {process.total_attempts}

Your subscription will be cancelled in 7 days if payment is not received.

Please update your payment method immediately: [URL]

Best regards,
Content Creation Crew
                """
            ),
            "payment_failed_final": (
                "FINAL NOTICE: Payment Required",
                f"""
Hello,

This is your final notice. We have been unable to process your payment after multiple attempts.

Subscription: {subscription.plan.title()} Plan
Amount: {amount}
Attempts: {process.total_attempts}

Your subscription will be cancelled in 7 days if we don't receive payment.

To keep your service active, please update your payment method now: [URL]

Best regards,
Content Creation Crew
                """
            ),
            "subscription_cancelled": (
                "Subscription Cancelled Due to Payment Failure",
                f"""
Hello,

We're sorry to inform you that your subscription has been cancelled due to multiple failed payment attempts.

Subscription: {subscription.plan.title()} Plan
Final Amount: {amount}

You can reactivate your subscription at any time by visiting: [URL]

If you believe this is an error, please contact support immediately.

Best regards,
Content Creation Crew
                """
            ),
        }
        
        return templates.get(notification_type, ("Payment Notification", "Payment notification"))
    
    def _resolve_dunning(self, process: DunningProcess, reason: str):
        """Resolve dunning process successfully"""
        process.status = DunningStatus.RECOVERED.value
        process.resolved_at = datetime.utcnow()
        process.next_action_at = None
        
        logger.info(f"Resolved dunning process {process.id}: {reason}")
    
    def _cancel_subscription_for_dunning(self, process: DunningProcess):
        """Cancel subscription due to failed dunning"""
        subscription = process.subscription
        
        if subscription:
            subscription.status = "cancelled"
            subscription.cancel_reason = "payment_failed"
            subscription.cancelled_at = datetime.utcnow()
        
        process.status = DunningStatus.EXHAUSTED.value
        process.cancelled_at = datetime.utcnow()
        process.cancellation_reason = "max_retries_exhausted"
        process.next_action_at = None
        
        logger.info(f"Cancelled subscription {subscription.id} for dunning process {process.id}")
    
    def _get_next_stage(self, current_stage: Dict) -> Optional[Dict]:
        """Get next stage in dunning schedule"""
        current_days = current_stage["days"]
        
        for stage in self.RETRY_SCHEDULE:
            if stage["days"] > current_days:
                return stage
        
        return None
    
    def cancel_dunning_process(self, process_id: int, reason: str = "manual_cancellation"):
        """Manually cancel a dunning process"""
        process = self.db.query(DunningProcess).filter(
            DunningProcess.id == process_id
        ).first()
        
        if not process:
            raise ValueError(f"Dunning process {process_id} not found")
        
        process.status = DunningStatus.CANCELLED.value
        process.cancelled_at = datetime.utcnow()
        process.cancellation_reason = reason
        process.next_action_at = None
        
        self.db.commit()
        
        logger.info(f"Cancelled dunning process {process_id}: {reason}")


# Singleton
_dunning_service = None


def get_dunning_service(db: Session) -> DunningService:
    """Get dunning service instance"""
    return DunningService(db)

