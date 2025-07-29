"""
Тесты для расчета курсов валют
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.handlers.client_calc import safe_fetch_rate


@pytest.mark.asyncio
async def test_tomorrow_rate_not_available():
    """Тест проверяет, что при недоступности завтрашнего курса возвращается None"""
    
    with patch('app.handlers.client_calc.cached_cbr_rate') as mock_cached_rate:
        # Симулируем отсутствие завтрашнего курса
        mock_cached_rate.return_value = None
        
        import datetime as dt
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        
        result = await safe_fetch_rate("USD", tomorrow, requested_tomorrow=True)
        
        assert result is None
        mock_cached_rate.assert_called_once_with(tomorrow, "USD", requested_tomorrow=True)


@pytest.mark.asyncio
async def test_tomorrow_rate_available():
    """Тест проверяет, что при доступности завтрашнего курса он возвращается"""
    
    with patch('app.handlers.client_calc.cached_cbr_rate') as mock_cached_rate:
        # Симулируем наличие завтрашнего курса
        mock_cached_rate.return_value = 95.50
        
        import datetime as dt
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        
        result = await safe_fetch_rate("USD", tomorrow, requested_tomorrow=True)
        
        assert result == 95.50
        mock_cached_rate.assert_called_once_with(tomorrow, "USD", requested_tomorrow=True) 