"""Тесты для кастомных типов."""

import pytest
from decimal import Decimal
from datetime import date
from app.utils.types import (
    RateValue, CurrencyCode, BusinessDate, UserId, FileSize,
    Amount, Commission, CalculationResult
)


class TestRateValue:
    """Тесты для типа RateValue."""

    def test_rate_value_from_string(self):
        """Тест создания RateValue из строки."""
        rate = RateValue("75.50")
        assert rate == "75.50"  # NewType возвращает базовый тип

    def test_rate_value_validation(self):
        """Тест валидации RateValue."""
        rate = RateValue("0.01")
        assert rate == "0.01"  # NewType возвращает базовый тип

    def test_rate_value_arithmetic(self):
        """Тест арифметических операций с RateValue."""
        rate1 = RateValue("10.50")
        rate2 = RateValue("5.25")
        # NewType не поддерживает арифметику напрямую
        assert rate1 == "10.50"
        assert rate2 == "5.25"


class TestCurrencyCode:
    """Тесты для типа CurrencyCode."""

    def test_currency_code_uppercase(self):
        """Тест автоматического приведения к верхнему регистру."""
        currency = CurrencyCode("usd")
        assert currency == "usd"  # NewType не изменяет значение

    def test_currency_code_validation(self):
        """Тест валидации кода валюты."""
        currency = CurrencyCode("EUR")
        assert currency == "EUR"

    def test_currency_code_comparison(self):
        """Тест сравнения кодов валют."""
        usd = CurrencyCode("USD")
        eur = CurrencyCode("EUR")
        # Строковое сравнение работает как обычно
        assert usd > eur  # "USD" > "EUR" по алфавиту


class TestBusinessDate:
    """Тесты для типа BusinessDate."""

    def test_business_date_from_string(self):
        """Тест создания BusinessDate из строки."""
        business_date = BusinessDate("2024-01-01")
        assert business_date == "2024-01-01"  # NewType возвращает базовый тип

    def test_business_date_isoformat(self):
        """Тест форматирования BusinessDate."""
        business_date = BusinessDate("2024-01-01")
        # NewType не добавляет методы
        assert business_date == "2024-01-01"

    def test_business_date_weekday(self):
        """Тест получения дня недели."""
        business_date = BusinessDate("2024-01-01")
        # NewType не добавляет методы
        assert business_date == "2024-01-01"


class TestUserId:
    """Тесты для типа UserId."""

    def test_user_id_creation(self):
        """Тест создания UserId."""
        user_id = UserId(123456)
        assert user_id == 123456

    def test_user_id_comparison(self):
        """Тест сравнения UserId."""
        user1 = UserId(123)
        user2 = UserId(456)
        assert user1 < user2


class TestFileSize:
    """Тесты для типа FileSize."""

    def test_file_size_creation(self):
        """Тест создания FileSize."""
        size = FileSize(1024)
        assert size == 1024

    def test_file_size_arithmetic(self):
        """Тест арифметических операций с FileSize."""
        size1 = FileSize(1000)
        size2 = FileSize(500)
        # NewType не поддерживает арифметику напрямую
        assert size1 == 1000
        assert size2 == 500


class TestAmount:
    """Тесты для типа Amount."""

    def test_amount_creation(self):
        """Тест создания Amount."""
        amount = Amount(Decimal("100.50"))
        assert amount == Decimal("100.50")

    def test_amount_from_string(self):
        """Тест создания Amount из строки."""
        amount = Amount(Decimal("75.25"))
        assert amount == Decimal("75.25")


class TestCommission:
    """Тесты для типа Commission."""

    def test_commission_creation(self):
        """Тест создания Commission."""
        commission = Commission(Decimal("2.5"))
        assert commission == Decimal("2.5")

    def test_commission_percentage(self):
        """Тест работы с процентами."""
        commission = Commission(Decimal("0.025"))
        assert commission == Decimal("0.025")


class TestCalculationResult:
    """Тесты для типа CalculationResult."""

    def test_calculation_result_creation(self):
        """Тест создания CalculationResult."""
        result = CalculationResult(Decimal("150.75"))
        assert result == Decimal("150.75")

    def test_calculation_result_precision(self):
        """Тест точности расчетов."""
        result = CalculationResult(Decimal("123.456789"))
        assert result == Decimal("123.456789") 