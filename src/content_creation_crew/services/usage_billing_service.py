"""
Usage-based billing service

Tracks and bills for metered usage (API calls, storage, compute time, etc.)
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

from ..database import Organization, Subscription
from ..db.models.billing_advanced import UsageMeter, UsageEvent

logger = logging.getLogger(__name__)


class UsageBillingService:
    """
    Service for usage-based billing
    
    Features:
    - Track usage across multiple meters
    - Calculate overage charges
    - Generate usage invoices
    - Reset meters at billing period
    """
    
    # Default meter configurations
    DEFAULT_METERS = {
        "api_calls": {
            "type": "counter",
            "unit_price": Decimal("0.01"),  # $0.01 per call
            "included_units": {
                "free": 1000,
                "basic": 5000,
                "pro": 10000,
                "enterprise": -1  # Unlimited
            }
        },
        "storage_gb": {
            "type": "gauge",
            "unit_price": Decimal("0.10"),  # $0.10 per GB
            "included_units": {
                "free": 1,
                "basic": 10,
                "pro": 100,
                "enterprise": 1000
            }
        },
        "video_minutes": {
            "type": "counter",
            "unit_price": Decimal("0.05"),  # $0.05 per minute
            "included_units": {
                "free": 10,
                "basic": 100,
                "pro": 500,
                "enterprise": -1
            }
        },
        "tts_characters": {
            "type": "counter",
            "unit_price": Decimal("0.000015"),  # $0.015 per 1000 characters
            "included_units": {
                "free": 10000,
                "basic": 100000,
                "pro": 500000,
                "enterprise": -1
            }
        }
    }
    
    def __init__(self, db: Session):
        """Initialize usage billing service"""
        self.db = db
    
    def initialize_meters(
        self,
        organization_id: int,
        subscription_id: int,
        plan: str
    ) -> List[UsageMeter]:
        """
        Initialize usage meters for an organization
        
        Args:
            organization_id: Organization ID
            subscription_id: Subscription ID
            plan: Subscription plan (free, basic, pro, enterprise)
        
        Returns:
            List of created meters
        """
        meters = []
        now = datetime.utcnow()
        period_end = now + timedelta(days=30)
        
        for meter_name, config in self.DEFAULT_METERS.items():
            # Check if meter already exists
            existing = self.db.query(UsageMeter).filter(
                UsageMeter.organization_id == organization_id,
                UsageMeter.meter_name == meter_name,
                UsageMeter.is_active == True
            ).first()
            
            if existing:
                logger.info(f"Meter {meter_name} already exists for org {organization_id}")
                meters.append(existing)
                continue
            
            # Get included units for plan
            included_units = config["included_units"].get(plan, 0)
            
            # Create meter
            meter = UsageMeter(
                organization_id=organization_id,
                subscription_id=subscription_id,
                meter_name=meter_name,
                meter_type=config["type"],
                unit_price=config["unit_price"],
                included_units=included_units,
                overage_price=config["unit_price"],
                period_start=now,
                period_end=period_end,
                is_active=True
            )
            
            self.db.add(meter)
            meters.append(meter)
        
        self.db.commit()
        
        logger.info(f"Initialized {len(meters)} usage meters for org {organization_id}")
        
        return meters
    
    def record_usage(
        self,
        organization_id: int,
        meter_name: str,
        value: Decimal,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> UsageEvent:
        """
        Record a usage event
        
        Args:
            organization_id: Organization ID
            meter_name: Meter name (api_calls, storage_gb, etc.)
            value: Usage value to add
            resource_id: Optional resource identifier
            resource_type: Optional resource type
            metadata: Optional additional data
        
        Returns:
            Created UsageEvent
        """
        # Get or create meter
        meter = self.db.query(UsageMeter).filter(
            UsageMeter.organization_id == organization_id,
            UsageMeter.meter_name == meter_name,
            UsageMeter.is_active == True
        ).first()
        
        if not meter:
            raise ValueError(f"Meter {meter_name} not found for org {organization_id}")
        
        # Create usage event
        previous_value = meter.current_value
        new_value = previous_value + value
        
        event = UsageEvent(
            meter_id=meter.id,
            organization_id=organization_id,
            event_type="increment",
            value=value,
            previous_value=previous_value,
            new_value=new_value,
            resource_id=resource_id,
            resource_type=resource_type,
            metadata=metadata
        )
        
        # Update meter
        meter.current_value = new_value
        meter.period_value += value
        meter.lifetime_value += value
        meter.updated_at = datetime.utcnow()
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.debug(
            f"Recorded usage for {meter_name}: "
            f"{float(value)} (total: {float(new_value)})"
        )
        
        return event
    
    def get_usage_summary(
        self,
        organization_id: int,
        meter_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary for organization
        
        Args:
            organization_id: Organization ID
            meter_name: Optional specific meter
        
        Returns:
            Dictionary with usage details
        """
        query = self.db.query(UsageMeter).filter(
            UsageMeter.organization_id == organization_id,
            UsageMeter.is_active == True
        )
        
        if meter_name:
            query = query.filter(UsageMeter.meter_name == meter_name)
        
        meters = query.all()
        
        summary = {
            "organization_id": organization_id,
            "meters": []
        }
        
        total_overage_charge = Decimal("0")
        
        for meter in meters:
            # Calculate overage
            overage_units = max(
                Decimal("0"),
                meter.period_value - meter.included_units
            )
            
            overage_charge = overage_units * meter.overage_price
            total_overage_charge += overage_charge
            
            # Calculate days remaining
            days_remaining = (meter.period_end - datetime.utcnow()).days
            
            meter_summary = {
                "meter_name": meter.meter_name,
                "meter_type": meter.meter_type,
                "current_value": float(meter.current_value),
                "period_value": float(meter.period_value),
                "included_units": float(meter.included_units),
                "overage_units": float(overage_units),
                "unit_price": float(meter.unit_price),
                "overage_charge": float(overage_charge),
                "period_start": meter.period_start.isoformat(),
                "period_end": meter.period_end.isoformat(),
                "days_remaining": days_remaining,
                "usage_percentage": float(
                    (meter.period_value / meter.included_units * 100)
                    if meter.included_units > 0 else 0
                )
            }
            
            summary["meters"].append(meter_summary)
        
        summary["total_overage_charge"] = float(total_overage_charge)
        summary["currency"] = "USD"
        
        return summary
    
    def calculate_usage_invoice_items(
        self,
        organization_id: int
    ) -> List[Dict[str, Any]]:
        """
        Calculate invoice line items for usage overages
        
        Args:
            organization_id: Organization ID
        
        Returns:
            List of line items for invoice
        """
        summary = self.get_usage_summary(organization_id)
        line_items = []
        
        for meter in summary["meters"]:
            if meter["overage_charge"] > 0:
                line_items.append({
                    "description": f"{meter['meter_name'].replace('_', ' ').title()} - Overage",
                    "quantity": meter["overage_units"],
                    "unit_price": meter["unit_price"],
                    "amount": meter["overage_charge"]
                })
        
        return line_items
    
    def reset_meters(
        self,
        organization_id: int,
        create_invoice: bool = True
    ) -> Dict[str, Any]:
        """
        Reset meters at end of billing period
        
        Args:
            organization_id: Organization ID
            create_invoice: Whether to generate usage invoice
        
        Returns:
            Dictionary with reset summary
        """
        meters = self.db.query(UsageMeter).filter(
            UsageMeter.organization_id == organization_id,
            UsageMeter.is_active == True
        ).all()
        
        now = datetime.utcnow()
        invoice = None
        
        # Generate usage invoice if needed
        if create_invoice:
            line_items = self.calculate_usage_invoice_items(organization_id)
            
            if line_items:
                try:
                    from .invoice_service import InvoiceService
                    invoice_service = InvoiceService(self.db)
                    
                    invoice = invoice_service.create_invoice(
                        organization_id=organization_id,
                        subscription_id=meters[0].subscription_id if meters else None,
                        line_items=line_items,
                        currency="USD",
                        due_days=14,
                        memo="Usage charges for billing period"
                    )
                    
                    logger.info(f"Created usage invoice {invoice.invoice_number} for org {organization_id}")
                except Exception as e:
                    logger.error(f"Failed to create usage invoice: {e}", exc_info=True)
        
        # Reset all meters
        for meter in meters:
            meter.period_value = Decimal("0")
            meter.period_start = now
            meter.period_end = now + timedelta(days=30)
            meter.last_reset_at = now
            meter.updated_at = now
        
        self.db.commit()
        
        logger.info(f"Reset {len(meters)} usage meters for org {organization_id}")
        
        return {
            "organization_id": organization_id,
            "meters_reset": len(meters),
            "invoice_created": invoice is not None,
            "invoice_id": invoice.id if invoice else None,
            "reset_at": now.isoformat()
        }
    
    def get_usage_history(
        self,
        organization_id: int,
        meter_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[UsageEvent]:
        """Get usage event history"""
        # Get meter
        meter = self.db.query(UsageMeter).filter(
            UsageMeter.organization_id == organization_id,
            UsageMeter.meter_name == meter_name
        ).first()
        
        if not meter:
            return []
        
        # Build query
        query = self.db.query(UsageEvent).filter(
            UsageEvent.meter_id == meter.id
        )
        
        if start_date:
            query = query.filter(UsageEvent.event_time >= start_date)
        if end_date:
            query = query.filter(UsageEvent.event_time <= end_date)
        
        query = query.order_by(UsageEvent.event_time.desc())
        query = query.limit(limit)
        
        return query.all()


def get_usage_billing_service(db: Session) -> UsageBillingService:
    """Get usage billing service instance"""
    return UsageBillingService(db)

