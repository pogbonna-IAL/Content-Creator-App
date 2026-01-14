"""
Tests for tax calculator
"""
import pytest
from decimal import Decimal
from src.content_creation_crew.services.tax_calculator import TaxCalculator, TaxResult


class TestTaxCalculator:
    """Test tax calculator for multi-jurisdiction support"""
    
    def setup_method(self):
        """Setup test"""
        self.calculator = TaxCalculator()
    
    def test_nigeria_vat(self):
        """Test Nigeria VAT calculation (7.5%)"""
        result = self.calculator.calculate_tax(
            amount=Decimal("100.00"),
            country_code="NG"
        )
        
        assert result.subtotal == Decimal("100.00")
        assert result.tax_rate == Decimal("0.075")
        assert result.tax_amount == Decimal("7.50")
        assert result.total == Decimal("107.50")
        assert result.tax_name == "VAT"
        assert result.tax_jurisdiction == "Nigeria"
        assert not result.reverse_charge
    
    def test_us_sales_tax_california(self):
        """Test US sales tax for California (7.25%)"""
        result = self.calculator.calculate_tax(
            amount=Decimal("100.00"),
            country_code="US",
            state_code="CA"
        )
        
        assert result.subtotal == Decimal("100.00")
        assert result.tax_rate == Decimal("0.0725")
        assert result.tax_amount == Decimal("7.25")
        assert result.total == Decimal("107.25")
        assert result.tax_name == "Sales Tax"
        assert result.tax_jurisdiction == "US-CA"
    
    def test_us_sales_tax_no_state(self):
        """Test US without state - no tax"""
        result = self.calculator.calculate_tax(
            amount=Decimal("100.00"),
            country_code="US"
        )
        
        assert result.tax_amount == Decimal("0")
        assert result.tax_exempt
    
    def test_uk_vat(self):
        """Test UK VAT (20%)"""
        result = self.calculator.calculate_tax(
            amount=Decimal("100.00"),
            country_code="GB"
        )
        
        assert result.subtotal == Decimal("100.00")
        assert result.tax_rate == Decimal("0.20")
        assert result.tax_amount == Decimal("20.00")
        assert result.total == Decimal("120.00")
        assert result.tax_name == "VAT"
        assert result.tax_jurisdiction == "UK"
    
    def test_ireland_vat(self):
        """Test Ireland VAT (23%)"""
        result = self.calculator.calculate_tax(
            amount=Decimal("100.00"),
            country_code="IE"
        )
        
        assert result.subtotal == Decimal("100.00")
        assert result.tax_rate == Decimal("0.23")
        assert result.tax_amount == Decimal("23.00")
        assert result.total == Decimal("123.00")
        assert result.tax_name == "VAT"
        assert result.tax_jurisdiction == "IE"
    
    def test_eu_reverse_charge(self):
        """Test EU B2B reverse charge"""
        result = self.calculator.calculate_tax(
            amount=Decimal("100.00"),
            country_code="IE",
            customer_type="business",
            tax_id="IE1234567T"  # Valid format
        )
        
        assert result.subtotal == Decimal("100.00")
        assert result.tax_rate == Decimal("0")
        assert result.tax_amount == Decimal("0")
        assert result.total == Decimal("100.00")
        assert result.reverse_charge
        assert "reverse charge" in result.exemption_reason.lower()
    
    def test_tax_exempt_customer(self):
        """Test tax exempt customer"""
        result = self.calculator.calculate_tax(
            amount=Decimal("100.00"),
            country_code="NG",
            tax_exempt=True
        )
        
        assert result.tax_amount == Decimal("0")
        assert result.total == Decimal("100.00")
        assert result.tax_exempt
    
    def test_validate_nigeria_tin(self):
        """Test Nigeria TIN validation"""
        is_valid, error = self.calculator.validate_tax_id(
            "12345678-0001",
            "NG",
            "tin"
        )
        
        assert is_valid
        assert error is None
    
    def test_validate_nigeria_tin_invalid(self):
        """Test invalid Nigeria TIN"""
        is_valid, error = self.calculator.validate_tax_id(
            "123-456",
            "NG",
            "tin"
        )
        
        assert not is_valid
        assert "format" in error.lower()
    
    def test_validate_us_ein(self):
        """Test US EIN validation"""
        is_valid, error = self.calculator.validate_tax_id(
            "12-3456789",
            "US",
            "ein"
        )
        
        assert is_valid
        assert error is None
    
    def test_validate_uk_vat(self):
        """Test UK VAT validation"""
        is_valid, error = self.calculator.validate_tax_id(
            "GB123456789",
            "GB",
            "vat"
        )
        
        assert is_valid
        assert error is None
    
    def test_validate_ireland_vat(self):
        """Test Ireland VAT validation"""
        is_valid, error = self.calculator.validate_tax_id(
            "IE1234567T",
            "IE",
            "vat"
        )
        
        assert is_valid
        assert error is None
    
    def test_rounding(self):
        """Test currency rounding"""
        result = self.calculator.calculate_tax(
            amount=Decimal("99.99"),
            country_code="NG"
        )
        
        # 99.99 * 0.075 = 7.49925, should round to 7.50
        assert result.tax_amount == Decimal("7.50")
        assert result.total == Decimal("107.49")
    
    def test_unsupported_country(self):
        """Test unsupported country - no tax"""
        result = self.calculator.calculate_tax(
            amount=Decimal("100.00"),
            country_code="XX"  # Unknown country
        )
        
        assert result.tax_amount == Decimal("0")
        assert result.tax_exempt
        assert "No tax rules" in result.exemption_reason

