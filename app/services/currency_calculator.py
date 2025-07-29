"""
Currency calculation service for client calculations.

This module provides currency conversion and calculation services
for client transactions with commission handling.
"""

import datetime as dt
import decimal
from dataclasses import dataclass
from typing import Optional

import structlog

from app.services.rates_cache import get_rate as cached_cbr_rate

log = structlog.get_logger(__name__)


@dataclass
class CalculationResult:
    """Result of currency calculation."""
    
    amount_usd: decimal.Decimal
    amount_rub: decimal.Decimal
    rate_used: decimal.Decimal
    commission_percent: decimal.Decimal
    commission_amount: decimal.Decimal
    total_amount: decimal.Decimal
    calculation_date: dt.date
    is_estimate: bool = False


class CurrencyCalculatorService:
    """Service for currency calculations with commission handling."""
    
    def __init__(self, default_commission_percent: decimal.Decimal = decimal.Decimal("2.0")):
        """Initialize calculator with default commission rate."""
        self.default_commission_percent = default_commission_percent
        self.logger = log
    
    async def calculate_conversion(
        self,
        amount_usd: decimal.Decimal,
        target_date: dt.date,
        commission_percent: Optional[decimal.Decimal] = None,
        requested_tomorrow: bool = False,
    ) -> Optional[CalculationResult]:
        """
        Calculate currency conversion from USD to RUB with commission.
        
        Args:
            amount_usd: Amount in USD to convert
            target_date: Date for exchange rate
            commission_percent: Commission percentage (defaults to service default)
            requested_tomorrow: Whether this is for tomorrow's rate
            
        Returns:
            CalculationResult or None if rate unavailable
        """
        if commission_percent is None:
            commission_percent = self.default_commission_percent
            
        try:
            # Get exchange rate
            rate = await self._get_exchange_rate("USD", target_date, requested_tomorrow)
            if rate is None:
                return None
                
            # Calculate amounts
            amount_rub = amount_usd * rate
            commission_amount = amount_rub * (commission_percent / 100)
            total_amount = amount_rub + commission_amount
            
            result = CalculationResult(
                amount_usd=amount_usd,
                amount_rub=amount_rub,
                rate_used=rate,
                commission_percent=commission_percent,
                commission_amount=commission_amount,
                total_amount=total_amount,
                calculation_date=target_date,
                is_estimate=requested_tomorrow,
            )
            
            self.logger.info(
                "Currency calculation completed",
                amount_usd=str(amount_usd),
                amount_rub=str(amount_rub),
                rate=str(rate),
                commission=str(commission_percent),
                date=target_date.isoformat(),
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Currency calculation failed",
                error=str(e),
                amount_usd=str(amount_usd),
                date=target_date.isoformat(),
            )
            return None
    
    async def _get_exchange_rate(
        self, 
        currency: str, 
        target_date: dt.date, 
        requested_tomorrow: bool = False
    ) -> Optional[decimal.Decimal]:
        """Get exchange rate for specified currency and date."""
        try:
            rate = await cached_cbr_rate(
                target_date, 
                currency, 
                requested_tomorrow=requested_tomorrow
            )
            return rate
        except Exception as e:
            self.logger.error(
                "Failed to get exchange rate",
                currency=currency,
                date=target_date.isoformat(),
                error=str(e),
            )
            return None
    
    def format_calculation_result(self, result: CalculationResult) -> str:
        """Format calculation result for display."""
        status = "📊 Предварительный расчёт" if result.is_estimate else "💰 Расчёт для клиента"
        
        return (
            f"{status}\n\n"
            f"💵 Сумма USD: ${result.amount_usd:,.2f}\n"
            f"💸 Курс ЦБ: {result.rate_used:,.2f} ₽\n"
            f"💰 Сумма RUB: {result.amount_rub:,.2f} ₽\n"
            f"📈 Комиссия ({result.commission_percent}%): {result.commission_amount:,.2f} ₽\n"
            f"💯 К доплате: {result.total_amount:,.2f} ₽\n"
            f"📅 Дата: {result.calculation_date.strftime('%d.%m.%Y')}"
        )


# Default calculator instance
default_calculator = CurrencyCalculatorService()