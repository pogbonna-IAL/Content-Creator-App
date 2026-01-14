"""
Tests for refund service
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from src.content_creation_crew.services.refund_service import RefundService, RefundPolicy


class TestRefundPolicy:
    """Test refund policy enforcement"""
    
    def test_within_refund_window(self):
        """Test refund within 14-day window"""
        payment_date = datetime.utcnow() - timedelta(days=7)
        
        can_refund, reason, details = RefundPolicy.can_refund(
            payment_date=payment_date,
            amount=Decimal("29.99")
        )
        
        assert can_refund is True
        assert reason is None
        assert details["refund_type"] == "full"
        assert details["refund_amount"] == Decimal("29.99")
        assert details["is_within_window"] is True
    
    def test_outside_refund_window_monthly(self):
        """Test refund outside window for monthly subscription"""
        payment_date = datetime.utcnow() - timedelta(days=20)
        
        can_refund, reason, details = RefundPolicy.can_refund(
            payment_date=payment_date,
            amount=Decimal("29.99"),
            subscription_plan="pro"
        )
        
        assert can_refund is False
        assert "expired" in reason.lower()
        assert details["is_within_window"] is False
    
    def test_prorated_refund_annual(self):
        """Test prorated refund for annual subscription"""
        payment_date = datetime.utcnow() - timedelta(days=20)
        
        can_refund, reason, details = RefundPolicy.can_refund(
            payment_date=payment_date,
            amount=Decimal("299.99"),
            subscription_plan="pro_annual"
        )
        
        assert can_refund is True
        assert reason is None
        assert details["refund_type"] == "prorated"
        assert details["refund_amount"] < Decimal("299.99")  # Prorated
        assert details["days_used"] == 20
    
    def test_past_all_windows(self):
        """Test refund past all windows"""
        payment_date = datetime.utcnow() - timedelta(days=35)
        
        can_refund, reason, details = RefundPolicy.can_refund(
            payment_date=payment_date,
            amount=Decimal("29.99")
        )
        
        assert can_refund is False
        assert "30 days" in reason
    
    def test_custom_refund_window(self):
        """Test custom refund window"""
        payment_date = datetime.utcnow() - timedelta(days=10)
        
        can_refund, reason, details = RefundPolicy.can_refund(
            payment_date=payment_date,
            amount=Decimal("29.99"),
            refund_window_days=7  # Custom 7-day window
        )
        
        assert can_refund is False  # 10 days > 7 days
        assert details["refund_window_days"] == 7


class TestRefundService:
    """Test refund service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        return db
    
    @pytest.fixture
    def refund_service(self, mock_db):
        """Create refund service"""
        return RefundService(mock_db)
    
    @pytest.fixture
    def mock_subscription(self):
        """Mock subscription"""
        sub = Mock()
        sub.id = 123
        sub.organization_id = 1
        sub.plan = "pro"
        sub.provider = "stripe"
        sub.created_at = datetime.utcnow() - timedelta(days=5)
        return sub
    
    @pytest.fixture
    def mock_organization(self):
        """Mock organization"""
        org = Mock()
        org.id = 1
        org.owner_user = Mock(email="test@example.com")
        return org
    
    def test_request_refund_subscription(self, refund_service, mock_db, mock_subscription, mock_organization):
        """Test requesting refund for subscription"""
        mock_db.query().filter().first.side_effect = [mock_organization, mock_subscription]
        
        with patch.object(refund_service, 'process_refund'):
            refund = refund_service.request_refund(
                organization_id=1,
                subscription_id=123,
                reason="customer_request"
            )
            
            assert mock_db.add.called
            assert mock_db.commit.called
    
    def test_request_refund_outside_window(self, refund_service, mock_db, mock_organization):
        """Test requesting refund outside window"""
        mock_db.query().filter().first.return_value = mock_organization
        
        old_subscription = Mock()
        old_subscription.id = 123
        old_subscription.organization_id = 1
        old_subscription.plan = "pro"
        old_subscription.provider = "stripe"
        old_subscription.created_at = datetime.utcnow() - timedelta(days=35)
        
        mock_db.query().filter().filter().first.return_value = old_subscription
        
        with pytest.raises(ValueError, match="not allowed"):
            refund_service.request_refund(
                organization_id=1,
                subscription_id=123,
                reason="customer_request"
            )
    
    @patch('src.content_creation_crew.services.refund_service.get_billing_gateway')
    def test_process_refund_success(self, mock_gateway_factory, refund_service, mock_db):
        """Test successful refund processing"""
        refund = Mock()
        refund.id = 1
        refund.status = "pending"
        refund.provider = "stripe"
        refund.amount = Decimal("29.99")
        refund.currency = "USD"
        refund.reason = "customer_request"
        refund.invoice_id = None
        
        mock_db.query().filter().first.return_value = refund
        
        mock_gateway = Mock()
        mock_gateway.create_refund.return_value = {
            "success": True,
            "refund_id": "re_test123",
            "amount": 2999,
            "currency": "usd"
        }
        mock_gateway_factory.return_value = mock_gateway
        
        with patch.object(refund_service, '_get_charge_id', return_value="ch_test123"):
            result = refund_service.process_refund(1)
            
            assert result is True
            assert refund.status == "succeeded"
    
    @patch('src.content_creation_crew.services.refund_service.get_billing_gateway')
    def test_process_refund_failure(self, mock_gateway_factory, refund_service, mock_db):
        """Test failed refund processing"""
        refund = Mock()
        refund.id = 1
        refund.status = "pending"
        refund.provider = "stripe"
        refund.amount = Decimal("29.99")
        refund.currency = "USD"
        refund.reason = "customer_request"
        refund.invoice_id = None
        
        mock_db.query().filter().first.return_value = refund
        
        mock_gateway = Mock()
        mock_gateway.create_refund.return_value = {
            "success": False,
            "error": "Charge already refunded"
        }
        mock_gateway_factory.return_value = mock_gateway
        
        with patch.object(refund_service, '_get_charge_id', return_value="ch_test123"):
            result = refund_service.process_refund(1)
            
            assert result is False
            assert refund.status == "failed"
            assert refund.failure_reason is not None
    
    def test_cancel_refund(self, refund_service, mock_db):
        """Test cancelling a refund"""
        refund = Mock()
        refund.id = 1
        refund.status = "pending"
        mock_db.query().filter().first.return_value = refund
        
        cancelled = refund_service.cancel_refund(1)
        
        assert refund.status == "cancelled"
        assert mock_db.commit.called
    
    def test_cancel_refund_invalid_status(self, refund_service, mock_db):
        """Test cancelling refund with invalid status"""
        refund = Mock()
        refund.id = 1
        refund.status = "succeeded"
        mock_db.query().filter().first.return_value = refund
        
        with pytest.raises(ValueError, match="Cannot cancel"):
            refund_service.cancel_refund(1)

