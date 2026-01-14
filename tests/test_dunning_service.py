"""
Tests for dunning service
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from src.content_creation_crew.services.dunning_service import DunningService
from src.content_creation_crew.db.models.dunning import DunningProcess, DunningStatus, PaymentAttempt


class TestDunningService:
    """Test dunning service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        return db
    
    @pytest.fixture
    def dunning_service(self, mock_db):
        """Create dunning service"""
        return DunningService(mock_db)
    
    @pytest.fixture
    def mock_subscription(self):
        """Mock subscription"""
        sub = Mock()
        sub.id = 123
        sub.organization_id = 1
        sub.plan = "pro"
        sub.provider = "stripe"
        sub.provider_customer_id = "cus_test123"
        return sub
    
    def test_start_dunning_process(self, dunning_service, mock_db, mock_subscription):
        """Test starting a dunning process"""
        mock_db.query().filter().first.return_value = mock_subscription
        mock_db.query().filter().filter().first.return_value = None  # No existing dunning
        
        process = dunning_service.start_dunning_process(
            subscription_id=123,
            failed_payment_amount=Decimal("29.99"),
            failure_reason="card_declined",
            provider="stripe"
        )
        
        assert mock_db.add.called
        assert mock_db.commit.called
    
    def test_start_dunning_process_existing(self, dunning_service, mock_db, mock_subscription):
        """Test starting dunning when one already exists"""
        mock_db.query().filter().first.return_value = mock_subscription
        
        existing_process = Mock()
        existing_process.id = 1
        existing_process.status = DunningStatus.ACTIVE.value
        mock_db.query().filter().filter().first.return_value = existing_process
        
        process = dunning_service.start_dunning_process(
            subscription_id=123,
            failed_payment_amount=Decimal("29.99")
        )
        
        assert process == existing_process
    
    def test_dunning_schedule(self, dunning_service):
        """Test dunning schedule configuration"""
        assert len(DunningService.RETRY_SCHEDULE) == 4
        assert DunningService.RETRY_SCHEDULE[0]["days"] == 3
        assert DunningService.RETRY_SCHEDULE[-1]["days"] == 21
        assert DunningService.RETRY_SCHEDULE[-1]["action"] == "cancel_subscription"
    
    def test_process_dunning_actions(self, dunning_service, mock_db):
        """Test processing dunning actions"""
        mock_db.query().filter().filter().all.return_value = []
        
        stats = dunning_service.process_dunning_actions()
        
        assert "processed" in stats
        assert "retries_attempted" in stats
        assert "emails_sent" in stats
    
    @patch('src.content_creation_crew.services.dunning_service.get_billing_gateway')
    def test_retry_payment_success(self, mock_gateway_factory, dunning_service, mock_db, mock_subscription):
        """Test successful payment retry"""
        process = Mock()
        process.id = 1
        process.subscription = mock_subscription
        process.amount_due = Decimal("29.99")
        process.currency = "USD"
        process.total_attempts = 0
        
        mock_gateway = Mock()
        mock_gateway.charge_customer.return_value = {
            "success": True,
            "payment_intent_id": "pi_test123",
            "charge_id": "ch_test123"
        }
        mock_gateway_factory.return_value = mock_gateway
        
        result = dunning_service._retry_payment(process)
        
        assert result is True
        assert mock_gateway.charge_customer.called
    
    @patch('src.content_creation_crew.services.dunning_service.get_billing_gateway')
    def test_retry_payment_failure(self, mock_gateway_factory, dunning_service, mock_db, mock_subscription):
        """Test failed payment retry"""
        process = Mock()
        process.id = 1
        process.subscription = mock_subscription
        process.amount_due = Decimal("29.99")
        process.currency = "USD"
        process.total_attempts = 0
        
        mock_gateway = Mock()
        mock_gateway.charge_customer.return_value = {
            "success": False,
            "failure_reason": "card_declined"
        }
        mock_gateway_factory.return_value = mock_gateway
        
        result = dunning_service._retry_payment(process)
        
        assert result is False
    
    def test_cancel_dunning_process(self, dunning_service, mock_db):
        """Test cancelling a dunning process"""
        process = Mock()
        process.id = 1
        process.status = DunningStatus.ACTIVE.value
        mock_db.query().filter().first.return_value = process
        
        dunning_service.cancel_dunning_process(1, "manual_cancellation")
        
        assert process.status == DunningStatus.CANCELLED.value
        assert process.cancellation_reason == "manual_cancellation"
        assert mock_db.commit.called

