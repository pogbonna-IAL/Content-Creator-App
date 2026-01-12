"""
Billing Gateway - Abstract interface for payment providers
Supports Bank Transfer, Paystack, and Stripe
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BillingGateway(ABC):
    """Abstract base class for payment providers"""
    
    @abstractmethod
    def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a customer in the payment provider"""
        pass
    
    @abstractmethod
    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a subscription"""
        pass
    
    @abstractmethod
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription"""
        pass
    
    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        pass
    
    @abstractmethod
    def parse_webhook_event(self, payload: Dict) -> Dict[str, Any]:
        """Parse webhook event into standardized format"""
        pass


class BankTransferGateway(BillingGateway):
    """Bank Transfer gateway - manual payment processing"""
    
    def __init__(self, bank_details: Dict[str, str]):
        """
        Initialize bank transfer gateway
        
        Args:
            bank_details: Dict with bank account details (account_number, bank_name, etc.)
        """
        self.bank_details = bank_details
    
    def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Bank transfer doesn't create customers - return local ID"""
        return {
            "customer_id": f"bank_{email}",
            "provider": "bank_transfer",
            "status": "pending"
        }
    
    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a bank transfer request"""
        return {
            "subscription_id": f"bank_{customer_id}_{int(datetime.utcnow().timestamp())}",
            "provider": "bank_transfer",
            "status": "pending_verification",
            "payment_instructions": self._get_payment_instructions(plan_id, metadata),
            "bank_details": self.bank_details
        }
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Bank transfer subscriptions are cancelled manually"""
        return {
            "subscription_id": subscription_id,
            "status": "cancelled",
            "provider": "bank_transfer"
        }
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Bank transfer doesn't use webhooks - manual verification"""
        return False
    
    def parse_webhook_event(self, payload: Dict) -> Dict[str, Any]:
        """Bank transfer doesn't use webhooks"""
        return {}
    
    def _get_payment_instructions(self, plan_id: str, metadata: Optional[Dict] = None) -> Dict[str, str]:
        """Get payment instructions for bank transfer"""
        return {
            "account_number": self.bank_details.get("account_number", ""),
            "bank_name": self.bank_details.get("bank_name", ""),
            "account_name": self.bank_details.get("account_name", ""),
            "routing_number": self.bank_details.get("routing_number", ""),
            "instructions": f"Please transfer payment for plan {plan_id} to the account above. Include your email in the transfer reference."
        }


class StripeGateway(BillingGateway):
    """Stripe payment gateway"""
    
    def __init__(self, api_key: str, webhook_secret: str, is_test: bool = False):
        """
        Initialize Stripe gateway
        
        Args:
            api_key: Stripe API key (test or live)
            webhook_secret: Stripe webhook signing secret
            is_test: Whether using test mode
        """
        try:
            import stripe
            self.stripe = stripe
            self.stripe.api_key = api_key
            self.webhook_secret = webhook_secret
            self.is_test = is_test
        except ImportError:
            raise ImportError("stripe package is required. Install with: pip install stripe")
    
    def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a Stripe customer"""
        try:
            customer = self.stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            return {
                "customer_id": customer.id,
                "provider": "stripe",
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise
    
    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a Stripe subscription"""
        try:
            subscription = self.stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": plan_id}],
                metadata=metadata or {}
            )
            return {
                "subscription_id": subscription.id,
                "customer_id": customer_id,
                "provider": "stripe",
                "status": subscription.status,
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end)
            }
        except Exception as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            raise
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a Stripe subscription"""
        try:
            subscription = self.stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "provider": "stripe"
            }
        except Exception as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            raise
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            self.stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            return True
        except self.stripe.error.SignatureVerificationError:
            return False
        except Exception as e:
            logger.error(f"Stripe webhook verification failed: {e}")
            return False
    
    def parse_webhook_event(self, payload: Dict) -> Dict[str, Any]:
        """Parse Stripe webhook event"""
        event_type = payload.get("type", "")
        data = payload.get("data", {}).get("object", {})
        
        # Map Stripe events to our standard format
        event_mapping = {
            "customer.subscription.created": "subscription_created",
            "customer.subscription.updated": "subscription_updated",
            "customer.subscription.deleted": "subscription_cancelled",
            "invoice.paid": "payment_succeeded",
            "invoice.payment_failed": "payment_failed",
        }
        
        return {
            "event_type": event_mapping.get(event_type, event_type),
            "provider_event_id": payload.get("id", ""),
            "subscription_id": data.get("id", ""),
            "customer_id": data.get("customer", ""),
            "status": data.get("status", ""),
            "current_period_end": datetime.fromtimestamp(data.get("current_period_end", 0)) if data.get("current_period_end") else None,
            "raw_data": data
        }


class PaystackGateway(BillingGateway):
    """Paystack payment gateway"""
    
    def __init__(self, secret_key: str, public_key: str, webhook_secret: str, is_test: bool = False):
        """
        Initialize Paystack gateway
        
        Args:
            secret_key: Paystack secret key (test or live)
            public_key: Paystack public key (test or live)
            webhook_secret: Paystack webhook secret
            is_test: Whether using test mode
        """
        self.secret_key = secret_key
        self.public_key = public_key
        self.webhook_secret = webhook_secret
        self.is_test = is_test
        self.base_url = "https://api.paystack.co"
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Paystack API"""
        import httpx
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = httpx.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = httpx.post(url, headers=headers, json=data or {}, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Paystack API request failed: {e}")
            raise
    
    def create_customer(self, email: str, name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a Paystack customer"""
        try:
            result = self._make_request(
                "POST",
                "/customer",
                {
                    "email": email,
                    "first_name": name.split()[0] if name else "",
                    "last_name": " ".join(name.split()[1:]) if name and len(name.split()) > 1 else "",
                    "metadata": metadata or {}
                }
            )
            customer_data = result.get("data", {})
            return {
                "customer_id": str(customer_data.get("id", "")),
                "customer_code": customer_data.get("customer_code", ""),
                "provider": "paystack",
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Paystack customer creation failed: {e}")
            raise
    
    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a Paystack subscription"""
        try:
            result = self._make_request(
                "POST",
                "/subscription",
                {
                    "customer": customer_id,
                    "plan": plan_id,
                    "metadata": metadata or {}
                }
            )
            subscription_data = result.get("data", {})
            return {
                "subscription_id": str(subscription_data.get("id", "")),
                "customer_id": customer_id,
                "provider": "paystack",
                "status": subscription_data.get("status", ""),
                "current_period_end": datetime.fromisoformat(subscription_data.get("next_payment_date", "").replace("Z", "+00:00")) if subscription_data.get("next_payment_date") else None
            }
        except Exception as e:
            logger.error(f"Paystack subscription creation failed: {e}")
            raise
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a Paystack subscription"""
        try:
            result = self._make_request(
                "POST",
                f"/subscription/{subscription_id}/disable"
            )
            subscription_data = result.get("data", {})
            return {
                "subscription_id": subscription_id,
                "status": subscription_data.get("status", "cancelled"),
                "provider": "paystack"
            }
        except Exception as e:
            logger.error(f"Paystack subscription cancellation failed: {e}")
            raise
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Paystack webhook signature"""
        import hmac
        import hashlib
        
        try:
            computed_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha512
            ).hexdigest()
            return hmac.compare_digest(computed_signature, signature)
        except Exception as e:
            logger.error(f"Paystack webhook verification failed: {e}")
            return False
    
    def parse_webhook_event(self, payload: Dict) -> Dict[str, Any]:
        """Parse Paystack webhook event"""
        event_type = payload.get("event", "")
        data = payload.get("data", {})
        
        # Map Paystack events to our standard format
        event_mapping = {
            "subscription.create": "subscription_created",
            "subscription.update": "subscription_updated",
            "subscription.disable": "subscription_cancelled",
            "charge.success": "payment_succeeded",
            "charge.failed": "payment_failed",
        }
        
        return {
            "event_type": event_mapping.get(event_type, event_type),
            "provider_event_id": str(payload.get("id", "")),
            "subscription_id": str(data.get("id", "")),
            "customer_id": str(data.get("customer", {}).get("id", "") if isinstance(data.get("customer"), dict) else data.get("customer", "")),
            "status": data.get("status", ""),
            "current_period_end": datetime.fromisoformat(data.get("next_payment_date", "").replace("Z", "+00:00")) if data.get("next_payment_date") else None,
            "raw_data": data
        }


def get_billing_gateway(provider: str, config) -> BillingGateway:
    """
    Factory function to get the appropriate billing gateway
    
    Args:
        provider: 'bank_transfer', 'stripe', or 'paystack'
        config: Config object with payment provider settings
    
    Returns:
        BillingGateway instance
    """
    is_staging = config.ENV == "staging"
    
    if provider == "bank_transfer":
        bank_details = {
            "account_number": config.BANK_ACCOUNT_NUMBER or "",
            "bank_name": config.BANK_NAME or "Your Bank",
            "account_name": config.BANK_ACCOUNT_NAME or "Content Creation Crew",
            "routing_number": config.BANK_ROUTING_NUMBER or ""
        }
        return BankTransferGateway(bank_details)
    
    elif provider == "stripe":
        if is_staging:
            api_key = config.STRIPE_TEST_SECRET_KEY
            webhook_secret = config.STRIPE_TEST_WEBHOOK_SECRET
        else:
            api_key = config.STRIPE_SECRET_KEY
            webhook_secret = config.STRIPE_WEBHOOK_SECRET
        
        if not api_key:
            raise ValueError("Stripe API key not configured")
        if not webhook_secret:
            raise ValueError("Stripe webhook secret not configured (required for staging/prod)")
        
        return StripeGateway(api_key, webhook_secret, is_test=is_staging)
    
    elif provider == "paystack":
        if is_staging:
            secret_key = config.PAYSTACK_TEST_SECRET_KEY
            public_key = config.PAYSTACK_TEST_PUBLIC_KEY
            webhook_secret = config.PAYSTACK_TEST_WEBHOOK_SECRET
        else:
            secret_key = config.PAYSTACK_SECRET_KEY
            public_key = config.PAYSTACK_PUBLIC_KEY
            webhook_secret = config.PAYSTACK_WEBHOOK_SECRET
        
        if not secret_key:
            raise ValueError("Paystack secret key not configured")
        if not webhook_secret:
            raise ValueError("Paystack webhook secret not configured (required for staging/prod)")
        
        return PaystackGateway(secret_key, public_key, webhook_secret, is_test=is_staging)
    
    else:
        raise ValueError(f"Unsupported payment provider: {provider}")

