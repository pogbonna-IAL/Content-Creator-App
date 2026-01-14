"""
Tests for invoice service
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import Mock, MagicMock
from src.content_creation_crew.services.invoice_service import InvoiceService
from src.content_creation_crew.db.models.invoice import Invoice, InvoiceStatus, BillingAddress


class TestInvoiceService:
    """Test invoice service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        return db
    
    @pytest.fixture
    def invoice_service(self, mock_db):
        """Create invoice service"""
        return InvoiceService(mock_db)
    
    def test_generate_invoice_number_first(self, invoice_service, mock_db):
        """Test invoice number generation - first invoice"""
        mock_db.query().filter().order_by().first.return_value = None
        
        number = invoice_service._generate_invoice_number()
        
        assert number.startswith("INV-2026-")
        assert number.endswith("0001")
    
    def test_generate_invoice_number_increment(self, invoice_service, mock_db):
        """Test invoice number generation - increment"""
        mock_invoice = Mock()
        mock_invoice.invoice_number = "INV-2026-0005"
        mock_db.query().filter().order_by().first.return_value = mock_invoice
        
        number = invoice_service._generate_invoice_number()
        
        assert number == "INV-2026-0006"
    
    def test_invoice_properties(self):
        """Test invoice properties"""
        invoice = Invoice(
            id=1,
            invoice_number="INV-2026-0001",
            organization_id=1,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("7.50"),
            total=Decimal("107.50"),
            amount_paid=Decimal("107.50"),
            amount_due=Decimal("0"),
            currency="USD",
            status=InvoiceStatus.PAID.value,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            line_items=[],
            customer_details={}
        )
        
        assert invoice.is_paid
        assert not invoice.is_overdue
    
    def test_invoice_overdue(self):
        """Test invoice overdue check"""
        invoice = Invoice(
            id=1,
            invoice_number="INV-2026-0001",
            organization_id=1,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("0"),
            total=Decimal("100.00"),
            amount_paid=Decimal("0"),
            amount_due=Decimal("100.00"),
            currency="USD",
            status=InvoiceStatus.ISSUED.value,
            invoice_date=date.today() - timedelta(days=30),
            due_date=date.today() - timedelta(days=1),  # Yesterday
            line_items=[],
            customer_details={}
        )
        
        assert invoice.is_overdue
        assert not invoice.is_paid

