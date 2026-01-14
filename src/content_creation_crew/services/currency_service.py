"""
Multi-currency support service

Handles exchange rates and currency conversions.
"""
from typing import Dict, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
import httpx

from ..db.models.billing_advanced import ExchangeRate
from ..config import config

logger = logging.getLogger(__name__)


class CurrencyService:
    """
    Service for currency exchange and conversion
    
    Supports: USD, EUR, GBP, NGN
    """
    
    BASE_CURRENCY = "USD"
    SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "NGN"]
    
    # Fallback rates (used if API fails)
    FALLBACK_RATES = {
        "USD": Decimal("1.00"),
        "EUR": Decimal("0.92"),
        "GBP": Decimal("0.79"),
        "NGN": Decimal("1550.00"),
    }
    
    def __init__(self, db: Session):
        """Initialize currency service"""
        self.db = db
        self.api_key = getattr(config, 'EXCHANGE_RATE_API_KEY', None)
        self.api_provider = getattr(config, 'EXCHANGE_RATE_PROVIDER', 'fallback')
    
    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        as_of_date: Optional[datetime] = None
    ) -> Decimal:
        """
        Get exchange rate between two currencies
        
        Args:
            from_currency: Source currency code (USD, EUR, GBP, NGN)
            to_currency: Target currency code
            as_of_date: Historical date (defaults to today)
        
        Returns:
            Exchange rate as Decimal
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Validate currencies
        if from_currency not in self.SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {from_currency}")
        if to_currency not in self.SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {to_currency}")
        
        # Same currency
        if from_currency == to_currency:
            return Decimal("1.00")
        
        # Get date
        if as_of_date is None:
            as_of_date = datetime.utcnow()
        
        # Try to get from database
        rate = self._get_cached_rate(from_currency, to_currency, as_of_date)
        
        if rate:
            return rate
        
        # Not in cache - fetch and store
        try:
            rates = self._fetch_rates_from_api()
            self._store_rates(rates)
            
            # Try again from cache
            rate = self._get_cached_rate(from_currency, to_currency, as_of_date)
            if rate:
                return rate
        except Exception as e:
            logger.error(f"Failed to fetch exchange rates: {e}", exc_info=True)
        
        # Fallback to hardcoded rates
        logger.warning(f"Using fallback exchange rate for {from_currency} → {to_currency}")
        return self._calculate_fallback_rate(from_currency, to_currency)
    
    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """
        Convert amount between currencies
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
        
        Returns:
            Converted amount
        """
        rate = self.get_rate(from_currency, to_currency)
        converted = amount * rate
        return converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def get_all_rates(self, base_currency: str = "USD") -> Dict[str, Decimal]:
        """
        Get all current exchange rates for a base currency
        
        Args:
            base_currency: Base currency (default USD)
        
        Returns:
            Dictionary of currency codes to rates
        """
        rates = {}
        
        for currency in self.SUPPORTED_CURRENCIES:
            if currency != base_currency:
                rates[currency] = self.get_rate(base_currency, currency)
        
        return rates
    
    def update_rates(self) -> Dict[str, Decimal]:
        """
        Update all exchange rates from API
        
        Should be called daily via scheduled job.
        
        Returns:
            Dictionary of updated rates
        """
        logger.info("Updating exchange rates...")
        
        try:
            rates = self._fetch_rates_from_api()
            self._store_rates(rates)
            
            logger.info(f"Successfully updated {len(rates)} exchange rates")
            return rates
            
        except Exception as e:
            logger.error(f"Failed to update exchange rates: {e}", exc_info=True)
            raise
    
    def _get_cached_rate(
        self,
        from_currency: str,
        to_currency: str,
        as_of_date: datetime
    ) -> Optional[Decimal]:
        """Get rate from database cache"""
        # Look for rate from today or yesterday (allow 24h cache)
        cutoff = as_of_date - timedelta(days=1)
        
        rate_record = self.db.query(ExchangeRate).filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
            ExchangeRate.effective_date >= cutoff,
            ExchangeRate.effective_date <= as_of_date
        ).order_by(ExchangeRate.effective_date.desc()).first()
        
        if rate_record:
            return rate_record.rate
        
        return None
    
    def _store_rates(self, rates: Dict[str, Decimal]):
        """Store rates in database"""
        now = datetime.utcnow()
        
        for currency_pair, rate in rates.items():
            parts = currency_pair.split('_')
            if len(parts) != 2:
                continue
            
            from_currency, to_currency = parts
            
            # Create or update rate
            existing = self.db.query(ExchangeRate).filter(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.effective_date >= now.date()
            ).first()
            
            if existing:
                existing.rate = rate
                existing.updated_at = now
            else:
                new_rate = ExchangeRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    source=self.api_provider,
                    effective_date=now,
                    expires_at=now + timedelta(days=1)
                )
                self.db.add(new_rate)
        
        self.db.commit()
    
    def _fetch_rates_from_api(self) -> Dict[str, Decimal]:
        """
        Fetch current rates from API provider
        
        Supported providers:
        - openexchangerates (requires API key)
        - exchangerate-api (free)
        - fallback (hardcoded rates)
        """
        if self.api_provider == "openexchangerates" and self.api_key:
            return self._fetch_from_openexchangerates()
        elif self.api_provider == "exchangerate-api":
            return self._fetch_from_exchangerate_api()
        else:
            # Use fallback rates
            return self._get_fallback_rates_dict()
    
    def _fetch_from_openexchangerates(self) -> Dict[str, Decimal]:
        """Fetch from openexchangerates.org"""
        url = f"https://openexchangerates.org/api/latest.json?app_id={self.api_key}"
        
        try:
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            base = data.get("base", "USD")
            
            for target in self.SUPPORTED_CURRENCIES:
                if target != base and target in data["rates"]:
                    rates[f"{base}_{target}"] = Decimal(str(data["rates"][target]))
            
            return rates
            
        except Exception as e:
            logger.error(f"Failed to fetch from openexchangerates: {e}")
            raise
    
    def _fetch_from_exchangerate_api(self) -> Dict[str, Decimal]:
        """Fetch from exchangerate-api.com (free tier)"""
        url = f"https://api.exchangerate-api.com/v4/latest/{self.BASE_CURRENCY}"
        
        try:
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            
            for target in self.SUPPORTED_CURRENCIES:
                if target != self.BASE_CURRENCY and target in data["rates"]:
                    rates[f"{self.BASE_CURRENCY}_{target}"] = Decimal(str(data["rates"][target]))
            
            return rates
            
        except Exception as e:
            logger.error(f"Failed to fetch from exchangerate-api: {e}")
            raise
    
    def _calculate_fallback_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """Calculate rate using fallback rates (via USD)"""
        from_rate = self.FALLBACK_RATES[from_currency]
        to_rate = self.FALLBACK_RATES[to_currency]
        
        # Convert via USD: from → USD → to
        # e.g., EUR → USD → GBP
        # 1 EUR = 1/0.92 USD = 1.087 USD
        # 1.087 USD = 1.087 * 0.79 GBP = 0.859 GBP
        
        if from_currency == self.BASE_CURRENCY:
            return to_rate
        elif to_currency == self.BASE_CURRENCY:
            return Decimal("1") / from_rate
        else:
            # Via USD
            to_usd = Decimal("1") / from_rate
            to_target = to_usd * to_rate
            return to_target
    
    def _get_fallback_rates_dict(self) -> Dict[str, Decimal]:
        """Get fallback rates as dict"""
        rates = {}
        
        for target in self.SUPPORTED_CURRENCIES:
            if target != self.BASE_CURRENCY:
                rates[f"{self.BASE_CURRENCY}_{target}"] = self.FALLBACK_RATES[target]
        
        return rates


def get_currency_service(db: Session) -> CurrencyService:
    """Get currency service instance"""
    return CurrencyService(db)

