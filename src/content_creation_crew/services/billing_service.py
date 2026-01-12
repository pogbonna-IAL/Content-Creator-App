"""
Billing Service - Manages subscriptions and payment processing
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from ..database import Organization, Subscription, BillingEvent
from ..db.models.subscription import SubscriptionPlan, SubscriptionStatus, PaymentProvider
from ..db.models.billing import BillingEventType
from .billing_gateway import get_billing_gateway, BillingGateway
from ..config import config

logger = logging.getLogger(__name__)


class BillingService:
    """Service for managing billing and subscriptions"""
    
    def __init__(self, db: Session):
        """
        Initialize billing service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_subscription(
        self,
        org_id: int,
        plan: SubscriptionPlan,
        provider: PaymentProvider,
        gateway: Optional[BillingGateway] = None
    ) -> Subscription:
        """
        Create a new subscription
        
        Args:
            org_id: Organization ID
            plan: Subscription plan
            provider: Payment provider
            gateway: Optional billing gateway (auto-created if not provided)
        
        Returns:
            Created Subscription object
        """
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise ValueError(f"Organization {org_id} not found")
        
        # Get or create gateway
        if not gateway:
            gateway = get_billing_gateway(provider.value, config)
        
        # Get user email for customer creation
        user = org.owner_user if hasattr(org, 'owner_user') else None
        if not user:
            raise ValueError(f"Organization {org_id} has no owner user")
        
        # Create customer in payment provider
        customer_data = gateway.create_customer(
            email=user.email,
            name=user.name or user.email,
            metadata={"org_id": org_id}
        )
        
        # Calculate period end (1 month from now)
        current_period_end = datetime.utcnow() + timedelta(days=30)
        
        # Create subscription record
        subscription = Subscription(
            org_id=org_id,
            plan=plan.value,
            status=SubscriptionStatus.ACTIVE.value,
            provider=provider.value,
            provider_customer_id=customer_data.get("customer_id"),
            provider_subscription_id=None,  # Will be set when subscription is created
            current_period_end=current_period_end
        )
        self.db.add(subscription)
        self.db.flush()
        
        # For bank transfer, create pending subscription (no provider subscription needed)
        if provider == PaymentProvider.STRIPE or provider == PaymentProvider.PAYSTACK:
            # Create subscription in payment provider
            subscription_data = gateway.create_subscription(
                customer_id=customer_data["customer_id"],
                plan_id=self._get_plan_id(plan, provider),
                metadata={"org_id": org_id, "subscription_id": subscription.id}
            )
            subscription.provider_subscription_id = subscription_data.get("subscription_id")
            if subscription_data.get("current_period_end"):
                subscription.current_period_end = subscription_data["current_period_end"]
        elif provider == PaymentProvider.BANK_TRANSFER:
            # Bank transfer subscriptions are pending until manually verified
            subscription.status = "pending_verification"
        
        self.db.commit()
        self.db.refresh(subscription)
        
        logger.info(f"Created subscription {subscription.id} for org {org_id}, plan {plan.value}, provider {provider.value}")
        
        return subscription
    
    def update_subscription_from_webhook(
        self,
        provider: PaymentProvider,
        event_type: str,
        provider_event_id: str,
        payload: Dict[str, Any]
    ) -> Optional[Subscription]:
        """
        Update subscription based on webhook event
        
        Args:
            provider: Payment provider
            event_type: Event type (subscription_created, subscription_updated, etc.)
            provider_event_id: Unique event ID from provider
            payload: Event payload
        
        Returns:
            Updated Subscription object or None
        """
        # Check for replay protection
        existing_event = self.db.query(BillingEvent).filter(
            BillingEvent.provider_event_id == provider_event_id
        ).first()
        
        if existing_event:
            logger.warning(f"Duplicate webhook event {provider_event_id} - ignoring")
            return None
        
        # Log billing event
        billing_event = BillingEvent(
            org_id=payload.get("org_id") or self._get_org_id_from_payload(provider, payload),
            provider=provider.value,
            event_type=event_type,
            provider_event_id=provider_event_id,
            payload_json=payload
        )
        self.db.add(billing_event)
        
        # Get subscription ID from payload
        subscription_id = payload.get("subscription_id")
        if not subscription_id:
            logger.warning(f"No subscription_id in webhook payload for event {provider_event_id}")
            self.db.commit()
            return None
        
        # Find subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.provider_subscription_id == str(subscription_id),
            Subscription.provider == provider.value
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found for provider_subscription_id {subscription_id}")
            self.db.commit()
            return None
        
        # Update subscription based on event type
        if event_type == "subscription_created":
            subscription.status = SubscriptionStatus.ACTIVE.value
            if payload.get("current_period_end"):
                subscription.current_period_end = payload["current_period_end"]
        
        elif event_type == "subscription_updated":
            if payload.get("status"):
                status_map = {
                    "active": SubscriptionStatus.ACTIVE.value,
                    "cancelled": SubscriptionStatus.CANCELLED.value,
                    "past_due": SubscriptionStatus.PAST_DUE.value,
                    "expired": SubscriptionStatus.EXPIRED.value,
                }
                subscription.status = status_map.get(payload["status"], subscription.status)
            if payload.get("current_period_end"):
                subscription.current_period_end = payload["current_period_end"]
        
        elif event_type == "subscription_cancelled":
            subscription.status = SubscriptionStatus.CANCELLED.value
        
        elif event_type == "payment_succeeded":
            # Renew subscription on successful payment
            if subscription.status == SubscriptionStatus.PAST_DUE.value:
                subscription.status = SubscriptionStatus.ACTIVE.value
            if payload.get("current_period_end"):
                subscription.current_period_end = payload["current_period_end"]
        
        elif event_type == "payment_failed":
            subscription.status = SubscriptionStatus.PAST_DUE.value
        
        subscription.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(subscription)
        
        logger.info(f"Updated subscription {subscription.id} from webhook event {event_type}")
        
        return subscription
    
    def cancel_subscription(self, subscription_id: int) -> Subscription:
        """
        Cancel a subscription
        
        Args:
            subscription_id: Subscription ID
        
        Returns:
            Updated Subscription object
        """
        subscription = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # Cancel in payment provider if applicable
        if subscription.provider_subscription_id and subscription.provider in [PaymentProvider.STRIPE.value, PaymentProvider.PAYSTACK.value]:
            try:
                gateway = get_billing_gateway(subscription.provider, config)
                gateway.cancel_subscription(subscription.provider_subscription_id)
            except Exception as e:
                logger.error(f"Failed to cancel subscription in provider: {e}")
        
        subscription.status = SubscriptionStatus.CANCELLED.value
        subscription.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(subscription)
        
        logger.info(f"Cancelled subscription {subscription_id}")
        
        return subscription
    
    def get_active_subscription(self, org_id: int) -> Optional[Subscription]:
        """Get active subscription for organization"""
        return self.db.query(Subscription).filter(
            Subscription.org_id == org_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
    
    def _get_plan_id(self, plan: SubscriptionPlan, provider: PaymentProvider) -> str:
        """Get plan ID for payment provider (stub - should be configured)"""
        # In a real implementation, this would map plans to provider-specific plan IDs
        # For now, return a placeholder
        plan_map = {
            (SubscriptionPlan.BASIC, PaymentProvider.STRIPE): "price_basic_monthly",
            (SubscriptionPlan.PRO, PaymentProvider.STRIPE): "price_pro_monthly",
            (SubscriptionPlan.ENTERPRISE, PaymentProvider.STRIPE): "price_enterprise_monthly",
            (SubscriptionPlan.BASIC, PaymentProvider.PAYSTACK): "plan_basic_monthly",
            (SubscriptionPlan.PRO, PaymentProvider.PAYSTACK): "plan_pro_monthly",
            (SubscriptionPlan.ENTERPRISE, PaymentProvider.PAYSTACK): "plan_enterprise_monthly",
        }
        return plan_map.get((plan, provider), f"plan_{plan.value}_monthly")
    
    def _get_org_id_from_payload(self, provider: PaymentProvider, payload: Dict[str, Any]) -> int:
        """Extract org_id from webhook payload"""
        # Try metadata first
        metadata = payload.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("org_id"):
            return int(metadata["org_id"])
        
        # Try customer lookup
        customer_id = payload.get("customer_id")
        if customer_id:
            subscription = self.db.query(Subscription).filter(
                Subscription.provider_customer_id == str(customer_id),
                Subscription.provider == provider.value
            ).first()
            if subscription:
                return subscription.org_id
        
        raise ValueError(f"Could not determine org_id from webhook payload")

