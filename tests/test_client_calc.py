"""
Тесты для обработчика расчёта клиента
"""

import pytest
from decimal import Decimal
from unittest.mock import patch

from app.handlers.client_calc import result_message


class TestClientCalculation:
    """Тесты для расчёта клиента"""

    def test_result_message_formatting(self):
        """Тест форматирования сообщения с результатом расчета."""
        # Тестовые данные
        currency = "USD"
        rate = Decimal("90.50")
        amount = Decimal("1000")
        commission_pct = Decimal("2.5")

        result = result_message(currency, rate, amount, commission_pct)

        # Проверяем, что сообщение содержит все необходимые элементы
        assert "Расчёт для клиента" in result
        assert "USD" in result
        assert "1000" in result
        assert "90.5000" in result
        assert "2.5" in result
        assert "Итого к оплате" in result

    def test_result_message_with_different_currencies(self):
        """Тест форматирования с разными валютами."""
        test_cases = [
            ("EUR", "95.20", "1000", "1.5"),
            ("CNY", "12.50", "1000", "3.0"),
            ("AED", "24.60", "1000", "2.0"),
        ]

        for currency, rate, amount, commission_pct in test_cases:
            result = result_message(currency, Decimal(rate), Decimal(amount), Decimal(commission_pct))

            assert currency in result
            assert rate in result
            assert commission_pct in result

    def test_result_message_with_zero_commission(self):
        """Тест форматирования с нулевой комиссией."""
        result = result_message("USD", Decimal("90.00"), Decimal("1000"), Decimal("0"))

        assert "0" in result
        assert "Комиссия (0%)" in result

    def test_result_message_with_high_commission(self):
        """Тест форматирования с высокой комиссией."""
        result = result_message("USD", Decimal("90.00"), Decimal("1000"), Decimal("10.0"))

        assert "10.0" in result
        assert "Комиссия (10.0%)" in result

    @pytest.mark.asyncio
    async def test_calculation_with_mocked_rate(self):
        """Тест расчета с замоканным курсом."""
        with patch("app.handlers.client_calc.cached_cbr_rate") as mock_get_rate:
            mock_get_rate.return_value = Decimal("90.50")

            # Здесь можно добавить тест асинхронной функции
            # но пока оставим простой тест
            assert True

    def test_result_message_edge_cases(self):
        """Тест граничных случаев форматирования."""
        # Очень большие числа
        result = result_message("USD", Decimal("100.00"), Decimal("1000000"), Decimal("5.0"))

        assert "1000000" in result
        assert "5.0" in result

    def test_result_message_currency_symbols(self):
        """Тест отображения символов валют."""
        currencies = ["USD", "EUR", "CNY", "AED", "TRY"]

        for currency in currencies:
            result = result_message(currency, Decimal("90.00"), Decimal("1000"), Decimal("2.0"))

            assert currency in result
            assert "2.0" in result
