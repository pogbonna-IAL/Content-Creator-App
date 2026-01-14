"""
Proration service for mid-cycle plan changes

Handles upgrade/downgrade calculations and invoice adjustments.
"""
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from ..database import Subscription, Organization
from ..db.models.billing_advanced import ProrationEvent

logger = logging.getLogger(__name__)


class ProrationService:
    """
    Service for calculating and applying proration for plan changes
    
    When a customer changes plans mid-cycle:
    1. Calculate unused time on old plan → credit
    2. Calculate prorated charge for new plan → charge
    3. Net amount = charge - credit
    4. Generate adjustment invoice
    """
    
    # Plan pricing (should come from database in production)
    PLAN_PRICES = {
        "free": Decimal("0.00"),
        "basic": Decimal("9.99"),
        "pro": Decimal("29.99"),
        "enterprise": Decimal("99.99"),
    }
    
    def __init__(self, db: Session):
        """Initialize proration service"""
        self.db = db
    
    def calculate_proration(
        self,
        subscription_id: int,
        new_plan: str,
        change_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate proration for a plan change
        
        Args:
            subscription_id: Current subscription ID
            new_plan: Target plan name
            change_date: When change takes effect (defaults to now)
        
        Returns:
            Dictionary with proration details
        """
        # Get subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # Get plan details
        old_plan = subscription.plan
        old_price = self.PLAN_PRICES.get(old_plan, Decimal("0"))
        new_price = self.PLAN_PRICES.get(new_plan, Decimal("0"))
        
        # Determine change type
        change_type = self._get_change_type(old_price, new_price)
        
        # Use current time if not specified
        if change_date is None:
            change_date = datetime.utcnow()
        
        # Calculate billing period
        period_start = subscription.current_period_start or subscription.created_at
        period_end = subscription.current_period_end or (period_start + timedelta(days=30))
        
        # Calculate days
        total_days = (period_end - period_start).days
        days_used = (change_date - period_start).days
        days_remaining = (period_end - change_date).days
        
        # Ensure non-negative
        days_used = max(0, days_used)
        days_remaining = max(0, days_remaining)
        
        # Calculate amounts
        if days_remaining <= 0:
            # No proration needed - at end of period
            credit_amount = Decimal("0")
            charge_amount = new_price
            net_amount = new_price
        else:
            # Proration needed
            # Credit: Unused portion of old plan
            credit_amount = self._calculate_credit(
                old_price, days_remaining, total_days
            )
            
            # Charge: Prorated amount for new plan
            charge_amount = self._calculate_charge(
                new_price, days_remaining, total_days
            )
            
            # Net amount (can be positive or negative)
            net_amount = charge_amount - credit_amount
        
        return {
            "subscription_id": subscription_id,
            "organization_id": subscription.organization_id,
            "old_plan": old_plan,
            "new_plan": new_plan,
            "change_type": change_type,
            "old_plan_price": float(old_price),
            "new_plan_price": float(new_price),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "change_date": change_date.isoformat(),
            "days_in_period": total_days,
            "days_used": days_used,
            "days_remaining": days_remaining,
            "credit_amount": float(credit_amount),
            "charge_amount": float(charge_amount),
            "net_amount": float(net_amount),
            "currency": "USD",
        }
    
    def apply_proration(
        self,
        subscription_id: int,
        new_plan: str,
        change_date: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> ProrationEvent:
        """
        Apply a plan change with proration
        
        Args:
            subscription_id: Subscription to change
            new_plan: Target plan
            change_date: Effective date
            user_id: User making the change
        
        Returns:
            Created ProrationEvent
        """
        # Calculate proration
        proration = self.calculate_proration(subscription_id, new_plan, change_date)
        
        # Get subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        
        # Create proration event
        event = ProrationEvent(
            subscription_id=subscription_id,
            organization_id=proration["organization_id"],
            old_plan=proration["old_plan"],
            new_plan=new_plan,
            change_type=proration["change_type"],
            old_plan_price=Decimal(str(proration["old_plan_price"])),
            new_plan_price=Decimal(str(proration["new_plan_price"])),
            days_in_period=proration["days_in_period"],
            days_used=proration["days_used"],
            days_remaining=proration["days_remaining"],
            credit_amount=Decimal(str(proration["credit_amount"])),
            charge_amount=Decimal(str(proration["charge_amount"])),
            net_amount=Decimal(str(proration["net_amount"])),
            currency="USD",
            period_start=datetime.fromisoformat(proration["period_start"]),
            period_end=datetime.fromisoformat(proration["period_end"]),
            change_date=datetime.fromisoformat(proration["change_date"]),
            status="pending",
            created_by=user_id,
        )
        
        self.db.add(event)
        
        # Update subscription
        subscription.plan = new_plan
        
        # If immediate change, update period prices
        if change_date is None or change_date <= datetime.utcnow():
            event.status = "applied"
            event.applied_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(
            f"Applied proration for subscription {subscription_id}: "
            f"{proration['old_plan']} → {new_plan}, "
            f"net amount: ${proration['net_amount']:.2f}"
        )
        
        # Generate adjustment invoice if net amount > 0
        if event.net_amount > 0:
            try:
                self._generate_proration_invoice(event)
            except Exception as e:
                logger.error(f"Failed to generate proration invoice: {e}", exc_info=True)
        
        return event
    
    def _calculate_credit(
        self,
        price: Decimal,
        days_remaining: int,
        total_days: int
    ) -> Decimal:
        """Calculate credit for unused portion"""
        if total_days == 0:
            return Decimal("0")
        
        credit = price * Decimal(days_remaining) / Decimal(total_days)
        return credit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def _calculate_charge(
        self,
        price: Decimal,
        days_remaining: int,
        total_days: int
    ) -> Decimal:
        """Calculate prorated charge for new plan"""
        if total_days == 0:
            return price
        
        charge = price * Decimal(days_remaining) / Decimal(total_days)
        return charge.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def _get_change_type(self, old_price: Decimal, new_price: Decimal) -> str:
        """Determine if upgrade, downgrade, or lateral"""
        if new_price > old_price:
            return "upgrade"
        elif new_price < old_price:
            return "downgrade"
        else:
            return "lateral"
    
    def _generate_proration_invoice(self, event: ProrationEvent):
        """Generate invoice for proration charge"""
        from .invoice_service import InvoiceService
        
        invoice_service = InvoiceService(self.db)
        
        # Create line items
        line_items = []
        
        # Credit line (if any)
        if event.credit_amount > 0:
            line_items.append({
                "description": f"Credit for unused {event.old_plan.title()} Plan ({event.days_remaining} days)",
                "quantity": 1,
                "unit_price": -float(event.credit_amount)  # Negative for credit
            })
        
        # Charge line
        if event.charge_amount > 0:
            line_items.append({
                "description": f"Prorated {event.new_plan.title()} Plan ({event.days_remaining} days)",
                "quantity": 1,
                "unit_price": float(event.charge_amount)
            })
        
        # Create invoice
        invoice = invoice_service.create_invoice(
            organization_id=event.organization_id,
            subscription_id=event.subscription_id,
            line_items=line_items,
            currency=event.currency,
            due_days=0,  # Due immediately
            memo=f"Plan change: {event.old_plan} → {event.new_plan}"
        )
        
        # Link invoice to proration event
        event.invoice_id = invoice.id
        self.db.commit()
        
        logger.info(f"Generated proration invoice {invoice.invoice_number} for proration event {event.id}")
        
        return invoice
    
    def get_proration_events(
        self,
        organization_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ):
        """Get proration events for an organization"""
        query = self.db.query(ProrationEvent).filter(
            ProrationEvent.organization_id == organization_id
        )
        
        if status:
            query = query.filter(ProrationEvent.status == status)
        
        query = query.order_by(ProrationEvent.created_at.desc())
        query = query.limit(limit)
        
        return query.all()


def get_proration_service(db: Session) -> ProrationService:
    """Get proration service instance"""
    return ProrationService(db)

