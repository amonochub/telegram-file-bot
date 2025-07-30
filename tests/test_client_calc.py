"""Тесты для расчета комиссий клиента."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.handlers.client_calc import result_message


class TestClientCalculation:
    """Тесты для функций расчета комиссий."""

    def test_result_message_formatting(self):
        """Тест форматирования сообщения с результатом расчета."""
        # Тестовые данные
        amount = Decimal("1000")
        currency = "USD"
        rate = Decimal("90.50")
        rub_sum = Decimal("90500")
        commission_pct = Decimal("2.5")
        fee = Decimal("2262.50")
        total = Decimal("92762.50")
        
        result = result_message(amount, currency, rate, rub_sum, commission_pct, fee, total)
        
        # Проверяем, что все значения присутствуют в сообщении
        assert str(amount) in result
        assert currency in result
        assert str(rate) in result
        assert str(rub_sum) in result
        assert str(commission_pct) in result
        assert str(fee) in result
        assert str(total) in result
        
        # Проверяем структуру сообщения
        assert "✅ <b>Расчёт готов!</b>" in result
        assert "📊 <b>Детали перевода:</b>" in result
        assert "💰 <b>Комиссия агента:</b>" in result
        assert "💵 <b>Итого к оплате:" in result
        assert "📋 <b>Для клиента:</b>" in result

    def test_result_message_with_different_currencies(self):
        """Тест форматирования с разными валютами."""
        test_cases = [
            ("EUR", "95.20", "95200", "1.5", "1428.00", "96628.00"),
            ("CNY", "12.50", "12500", "3.0", "375.00", "12875.00"),
            ("AED", "24.60", "24600", "2.0", "492.00", "25092.00"),
        ]
        
        for currency, rate, rub_sum, commission_pct, fee, total in test_cases:
            result = result_message(
                Decimal("1000"), 
                currency, 
                Decimal(rate), 
                Decimal(rub_sum), 
                Decimal(commission_pct), 
                Decimal(fee), 
                Decimal(total)
            )
            
            assert currency in result
            assert rate in result
            assert total in result

    def test_result_message_with_zero_commission(self):
        """Тест форматирования с нулевой комиссией."""
        result = result_message(
            Decimal("1000"),
            "USD",
            Decimal("90.00"),
            Decimal("90000"),
            Decimal("0"),
            Decimal("0"),
            Decimal("90000")
        )
        
        assert "0%" in result
        assert "0 ₽" in result

    def test_result_message_with_high_commission(self):
        """Тест форматирования с высокой комиссией."""
        result = result_message(
            Decimal("1000"),
            "USD",
            Decimal("90.00"),
            Decimal("90000"),
            Decimal("10.0"),
            Decimal("9000"),
            Decimal("99000")
        )
        
        assert "10.0%" in result
        assert "9000 ₽" in result

    @pytest.mark.asyncio
    async def test_calculation_with_mocked_rate(self):
        """Тест расчета с замоканным курсом."""
        with patch('app.handlers.client_calc.get_rate') as mock_get_rate:
            mock_get_rate.return_value = Decimal("90.50")
            
            # Здесь можно добавить тест полного сценария расчета
            # Но для этого нужно эмулировать весь FSM процесс
            pass

    def test_result_message_edge_cases(self):
        """Тест граничных случаев форматирования."""
        # Очень большие числа
        result = result_message(
            Decimal("1000000"),
            "USD",
            Decimal("100.00"),
            Decimal("100000000"),
            Decimal("5.0"),
            Decimal("5000000"),
            Decimal("105000000")
        )
        
        assert "1000000 USD" in result
        assert "100000000 ₽" in result
        
        # Очень маленькие числа
        result = result_message(
            Decimal("0.01"),
            "USD",
            Decimal("90.00"),
            Decimal("0.90"),
            Decimal("1.0"),
            Decimal("0.01"),
            Decimal("0.91")
        )
        
        assert "0.01 USD" in result
        assert "0.90 ₽" in result

    def test_result_message_currency_symbols(self):
        """Тест отображения символов валют."""
        currencies = ["USD", "EUR", "CNY", "AED", "TRY"]
        
        for currency in currencies:
            result = result_message(
                Decimal("1000"),
                currency,
                Decimal("90.00"),
                Decimal("90000"),
                Decimal("2.0"),
                Decimal("1800"),
                Decimal("91800")
            )
            
            assert f"1000 {currency}" in result
            assert "90.00 ₽" in result  # Курс всегда в рублях
            assert "90000 ₽" in result
            assert "1800 ₽" in result
            assert "91800 ₽" in result 