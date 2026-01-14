"""
Multi-jurisdiction tax calculator

Supports tax calculation for:
- Nigeria (VAT 7.5%)
- United States (Sales tax by state)
- United Kingdom (VAT 20%)
- Ireland/EU (VAT 23% + reverse charge)
"""
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class TaxResult:
    """Tax calculation result"""
    subtotal: Decimal
    tax_rate: Decimal  # e.g., 0.20 for 20%
    tax_amount: Decimal
    total: Decimal
    tax_name: str  # e.g., "VAT", "Sales Tax", "GST"
    tax_jurisdiction: str  # e.g., "UK", "California", "Nigeria"
    reverse_charge: bool = False  # True for EU B2B
    tax_exempt: bool = False
    exemption_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "subtotal": float(self.subtotal),
            "tax_rate": float(self.tax_rate),
            "tax_amount": float(self.tax_amount),
            "total": float(self.total),
            "tax_name": self.tax_name,
            "tax_jurisdiction": self.tax_jurisdiction,
            "reverse_charge": self.reverse_charge,
            "tax_exempt": self.tax_exempt,
            "exemption_reason": self.exemption_reason,
        }


class TaxCalculator:
    """
    Multi-jurisdiction tax calculator
    
    Supports:
    - Nigeria VAT (7.5%)
    - US Sales Tax (varies by state)
    - UK VAT (20%)
    - Ireland VAT (23%)
    - EU reverse charge mechanism
    """
    
    # Nigeria VAT
    NIGERIA_VAT_RATE = Decimal("0.075")  # 7.5%
    
    # UK VAT
    UK_VAT_RATE = Decimal("0.20")  # 20%
    UK_VAT_THRESHOLD = Decimal("85000")  # £85,000 annual threshold
    
    # Ireland/EU VAT
    IRELAND_VAT_RATE = Decimal("0.23")  # 23%
    EU_VAT_THRESHOLD = Decimal("10000")  # €10,000 for digital services
    
    # US Sales Tax by state (simplified - in production use TaxJar/Avalara)
    US_SALES_TAX = {
        "AL": Decimal("0.04"),    # Alabama 4%
        "AK": Decimal("0.00"),    # Alaska 0% (local taxes may apply)
        "AZ": Decimal("0.056"),   # Arizona 5.6%
        "AR": Decimal("0.065"),   # Arkansas 6.5%
        "CA": Decimal("0.0725"),  # California 7.25%
        "CO": Decimal("0.029"),   # Colorado 2.9%
        "CT": Decimal("0.0635"),  # Connecticut 6.35%
        "DE": Decimal("0.00"),    # Delaware 0%
        "FL": Decimal("0.06"),    # Florida 6%
        "GA": Decimal("0.04"),    # Georgia 4%
        "HI": Decimal("0.04"),    # Hawaii 4%
        "ID": Decimal("0.06"),    # Idaho 6%
        "IL": Decimal("0.0625"),  # Illinois 6.25%
        "IN": Decimal("0.07"),    # Indiana 7%
        "IA": Decimal("0.06"),    # Iowa 6%
        "KS": Decimal("0.065"),   # Kansas 6.5%
        "KY": Decimal("0.06"),    # Kentucky 6%
        "LA": Decimal("0.0445"),  # Louisiana 4.45%
        "ME": Decimal("0.055"),   # Maine 5.5%
        "MD": Decimal("0.06"),    # Maryland 6%
        "MA": Decimal("0.0625"),  # Massachusetts 6.25%
        "MI": Decimal("0.06"),    # Michigan 6%
        "MN": Decimal("0.06875"), # Minnesota 6.875%
        "MS": Decimal("0.07"),    # Mississippi 7%
        "MO": Decimal("0.04225"), # Missouri 4.225%
        "MT": Decimal("0.00"),    # Montana 0%
        "NE": Decimal("0.055"),   # Nebraska 5.5%
        "NV": Decimal("0.0685"),  # Nevada 6.85%
        "NH": Decimal("0.00"),    # New Hampshire 0%
        "NJ": Decimal("0.06625"), # New Jersey 6.625%
        "NM": Decimal("0.05125"), # New Mexico 5.125%
        "NY": Decimal("0.04"),    # New York 4%
        "NC": Decimal("0.0475"),  # North Carolina 4.75%
        "ND": Decimal("0.05"),    # North Dakota 5%
        "OH": Decimal("0.0575"),  # Ohio 5.75%
        "OK": Decimal("0.045"),   # Oklahoma 4.5%
        "OR": Decimal("0.00"),    # Oregon 0%
        "PA": Decimal("0.06"),    # Pennsylvania 6%
        "RI": Decimal("0.07"),    # Rhode Island 7%
        "SC": Decimal("0.06"),    # South Carolina 6%
        "SD": Decimal("0.045"),   # South Dakota 4.5%
        "TN": Decimal("0.07"),    # Tennessee 7%
        "TX": Decimal("0.0625"),  # Texas 6.25%
        "UT": Decimal("0.0485"),  # Utah 4.85%
        "VT": Decimal("0.06"),    # Vermont 6%
        "VA": Decimal("0.053"),   # Virginia 5.3%
        "WA": Decimal("0.065"),   # Washington 6.5%
        "WV": Decimal("0.06"),    # West Virginia 6%
        "WI": Decimal("0.05"),    # Wisconsin 5%
        "WY": Decimal("0.04"),    # Wyoming 4%
    }
    
    # EU country VAT rates (for reference)
    EU_VAT_RATES = {
        "IE": Decimal("0.23"),  # Ireland 23%
        "DE": Decimal("0.19"),  # Germany 19%
        "FR": Decimal("0.20"),  # France 20%
        "ES": Decimal("0.21"),  # Spain 21%
        "IT": Decimal("0.22"),  # Italy 22%
        "NL": Decimal("0.21"),  # Netherlands 21%
        "BE": Decimal("0.21"),  # Belgium 21%
        "AT": Decimal("0.20"),  # Austria 20%
        "PT": Decimal("0.23"),  # Portugal 23%
        "PL": Decimal("0.23"),  # Poland 23%
        "SE": Decimal("0.25"),  # Sweden 25%
        "DK": Decimal("0.25"),  # Denmark 25%
        "FI": Decimal("0.24"),  # Finland 24%
        # Add more as needed
    }
    
    # EU member countries (for reverse charge)
    EU_COUNTRIES = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE"
    }
    
    def __init__(self):
        """Initialize tax calculator"""
        pass
    
    def calculate_tax(
        self,
        amount: Decimal,
        country_code: str,
        state_code: Optional[str] = None,
        customer_type: str = "individual",
        tax_id: Optional[str] = None,
        tax_exempt: bool = False,
        supplier_country: str = "NG"  # Default to Nigeria as supplier
    ) -> TaxResult:
        """
        Calculate tax for a transaction
        
        Args:
            amount: Transaction amount (subtotal before tax)
            country_code: Customer country (ISO 3166-1 alpha-2)
            state_code: US state code (if applicable)
            customer_type: "individual" or "business"
            tax_id: Customer's tax ID (VAT/GST number)
            tax_exempt: Whether customer is tax exempt
            supplier_country: Supplier country code (default: NG)
        
        Returns:
            TaxResult with calculated tax
        """
        amount = Decimal(str(amount))
        country_code = country_code.upper()
        
        # Check tax exemption
        if tax_exempt:
            return TaxResult(
                subtotal=amount,
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=amount,
                tax_name="Exempt",
                tax_jurisdiction=country_code,
                tax_exempt=True,
                exemption_reason="Tax exempt customer"
            )
        
        # Route to appropriate tax calculator
        if country_code == "NG":
            return self._calculate_nigeria_vat(amount)
        elif country_code == "US":
            return self._calculate_us_sales_tax(amount, state_code)
        elif country_code == "GB":
            return self._calculate_uk_vat(amount, customer_type, tax_id)
        elif country_code in self.EU_COUNTRIES:
            return self._calculate_eu_vat(
                amount, country_code, customer_type, tax_id, supplier_country
            )
        else:
            # No tax for other countries (expand as needed)
            logger.warning(f"No tax rules for country: {country_code}")
            return TaxResult(
                subtotal=amount,
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=amount,
                tax_name="No Tax",
                tax_jurisdiction=country_code,
                tax_exempt=True,
                exemption_reason=f"No tax rules configured for {country_code}"
            )
    
    def _calculate_nigeria_vat(self, amount: Decimal) -> TaxResult:
        """
        Calculate Nigeria VAT (7.5%)
        
        Nigeria VAT applies to most goods and services.
        Certain items are exempt (financial services, basic food items, etc.)
        """
        tax_amount = self._round_currency(amount * self.NIGERIA_VAT_RATE)
        total = amount + tax_amount
        
        return TaxResult(
            subtotal=amount,
            tax_rate=self.NIGERIA_VAT_RATE,
            tax_amount=tax_amount,
            total=total,
            tax_name="VAT",
            tax_jurisdiction="Nigeria"
        )
    
    def _calculate_us_sales_tax(
        self,
        amount: Decimal,
        state_code: Optional[str]
    ) -> TaxResult:
        """
        Calculate US sales tax by state
        
        Note: This is simplified. In production, use TaxJar or Avalara for:
        - Local/city tax rates
        - Product-specific exemptions
        - Nexus determination
        - Economic nexus thresholds
        """
        if not state_code:
            # No state provided - no tax
            return TaxResult(
                subtotal=amount,
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=amount,
                tax_name="Sales Tax",
                tax_jurisdiction="US",
                tax_exempt=True,
                exemption_reason="State not provided"
            )
        
        state_code = state_code.upper()
        tax_rate = self.US_SALES_TAX.get(state_code, Decimal("0"))
        
        if tax_rate == Decimal("0"):
            return TaxResult(
                subtotal=amount,
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=amount,
                tax_name="Sales Tax",
                tax_jurisdiction=f"US-{state_code}",
                tax_exempt=True,
                exemption_reason=f"{state_code} has no state sales tax"
            )
        
        tax_amount = self._round_currency(amount * tax_rate)
        total = amount + tax_amount
        
        return TaxResult(
            subtotal=amount,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total=total,
            tax_name="Sales Tax",
            tax_jurisdiction=f"US-{state_code}"
        )
    
    def _calculate_uk_vat(
        self,
        amount: Decimal,
        customer_type: str,
        tax_id: Optional[str]
    ) -> TaxResult:
        """
        Calculate UK VAT (20%)
        
        UK VAT applies to most digital services.
        Businesses can reclaim VAT (but still charged).
        Some services are exempt or zero-rated.
        """
        # VAT applies to digital services regardless of customer type
        # (Businesses can reclaim it, but we still charge it)
        tax_amount = self._round_currency(amount * self.UK_VAT_RATE)
        total = amount + tax_amount
        
        return TaxResult(
            subtotal=amount,
            tax_rate=self.UK_VAT_RATE,
            tax_amount=tax_amount,
            total=total,
            tax_name="VAT",
            tax_jurisdiction="UK"
        )
    
    def _calculate_eu_vat(
        self,
        amount: Decimal,
        country_code: str,
        customer_type: str,
        tax_id: Optional[str],
        supplier_country: str
    ) -> TaxResult:
        """
        Calculate EU VAT with reverse charge mechanism
        
        Rules:
        - B2C (individual): Charge supplier country VAT (Nigeria doesn't apply)
        - B2C in EU: Charge customer country VAT if over threshold
        - B2B with valid VAT ID: Reverse charge (0% - customer self-accounts)
        - B2B without valid VAT ID: Charge supplier country VAT
        
        For Ireland specifically: 23% VAT
        """
        # Get VAT rate for customer's country
        vat_rate = self.EU_VAT_RATES.get(country_code, Decimal("0.20"))  # Default 20%
        
        # Special handling for Ireland
        if country_code == "IE":
            vat_rate = self.IRELAND_VAT_RATE
        
        # B2B with valid VAT ID: Reverse charge
        if customer_type == "business" and tax_id and self._validate_eu_vat_format(tax_id, country_code):
            return TaxResult(
                subtotal=amount,
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=amount,
                tax_name="VAT",
                tax_jurisdiction=country_code,
                reverse_charge=True,
                exemption_reason="EU B2B reverse charge - customer self-accounts for VAT"
            )
        
        # B2C or B2B without valid VAT ID: Charge VAT
        tax_amount = self._round_currency(amount * vat_rate)
        total = amount + tax_amount
        
        return TaxResult(
            subtotal=amount,
            tax_rate=vat_rate,
            tax_amount=tax_amount,
            total=total,
            tax_name="VAT",
            tax_jurisdiction=country_code
        )
    
    def _validate_eu_vat_format(self, tax_id: str, country_code: str) -> bool:
        """
        Validate EU VAT number format (basic validation)
        
        In production, use VIES API for real validation:
        https://ec.europa.eu/taxation_customs/vies/
        """
        if not tax_id:
            return False
        
        # Remove spaces and convert to uppercase
        tax_id = tax_id.replace(" ", "").upper()
        
        # VAT format patterns by country
        patterns = {
            "IE": r"^IE\d{7}[A-Z]{1,2}$|^IE\d[A-Z]\d{5}[A-Z]$",  # Ireland
            "GB": r"^GB\d{9}$|^GB\d{12}$|^GBGD\d{3}$|^GBHA\d{3}$",  # UK
            "DE": r"^DE\d{9}$",  # Germany
            "FR": r"^FR[A-Z0-9]{2}\d{9}$",  # France
            "ES": r"^ES[A-Z0-9]\d{7}[A-Z0-9]$",  # Spain
            "IT": r"^IT\d{11}$",  # Italy
            "NL": r"^NL\d{9}B\d{2}$",  # Netherlands
            "BE": r"^BE0\d{9}$",  # Belgium
            "AT": r"^ATU\d{8}$",  # Austria
            "PT": r"^PT\d{9}$",  # Portugal
            "PL": r"^PL\d{10}$",  # Poland
            "SE": r"^SE\d{12}$",  # Sweden
            "DK": r"^DK\d{8}$",  # Denmark
            "FI": r"^FI\d{8}$",  # Finland
        }
        
        pattern = patterns.get(country_code)
        if not pattern:
            logger.warning(f"No VAT pattern for country: {country_code}")
            return False
        
        return bool(re.match(pattern, tax_id))
    
    def validate_tax_id(
        self,
        tax_id: str,
        country_code: str,
        tax_id_type: str = "vat"
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate tax ID format
        
        Returns:
            (is_valid, error_message)
        """
        if not tax_id:
            return False, "Tax ID is required"
        
        country_code = country_code.upper()
        
        # Nigeria TIN
        if country_code == "NG":
            # Nigeria TIN format: 12345678-0001
            if not re.match(r"^\d{8}-\d{4}$", tax_id):
                return False, "Nigeria TIN must be in format: 12345678-0001"
            return True, None
        
        # US EIN
        elif country_code == "US":
            # EIN format: 12-3456789
            clean_ein = tax_id.replace("-", "")
            if not re.match(r"^\d{9}$", clean_ein):
                return False, "US EIN must be 9 digits (format: 12-3456789)"
            return True, None
        
        # UK VAT
        elif country_code == "GB":
            clean_vat = tax_id.replace(" ", "").upper()
            if not re.match(r"^GB\d{9}$|^GB\d{12}$", clean_vat):
                return False, "UK VAT must be GB followed by 9 or 12 digits"
            return True, None
        
        # EU VAT
        elif country_code in self.EU_COUNTRIES:
            if self._validate_eu_vat_format(tax_id, country_code):
                return True, None
            return False, f"Invalid {country_code} VAT format"
        
        return True, None  # Unknown format - accept
    
    def _round_currency(self, amount: Decimal) -> Decimal:
        """Round to 2 decimal places (currency precision)"""
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Singleton instance
_tax_calculator = None


def get_tax_calculator() -> TaxCalculator:
    """Get singleton tax calculator instance"""
    global _tax_calculator
    if _tax_calculator is None:
        _tax_calculator = TaxCalculator()
    return _tax_calculator

