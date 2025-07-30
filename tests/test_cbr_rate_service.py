"""
Тесты для надёжной системы курсов ЦБ
"""

import pytest
import decimal
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.cbr_rate_service import CBRRateService, get_cbr_service, cleanup_cbr_service


@pytest.fixture
def mock_bot():
    """Мок для бота"""
    bot = AsyncMock()
    return bot


@pytest.fixture
def cbr_service(mock_bot):
    """Создание экземпляра сервиса курсов ЦБ"""
    service = CBRRateService(mock_bot)
    return service


@pytest.fixture(autouse=True)
def cleanup():
    """Очистка глобального сервиса после каждого теста"""
    yield
    import asyncio
    try:
        asyncio.run(cleanup_cbr_service())
    except:
        pass


class TestCBRRateService:
    """Тесты для сервиса курсов ЦБ"""
    
    @pytest.mark.asyncio
    async def test_get_cbr_rate_success(self, cbr_service):
        """Тест успешного получения курса"""
        # Мокаем cached_cbr_rate
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.services.cbr_rate_service.cached_cbr_rate", AsyncMock(return_value=decimal.Decimal("90.50")))
            
            result = await cbr_service.get_cbr_rate(date(2025, 1, 1), "USD")
            
            assert result == decimal.Decimal("90.50")
    
    @pytest.mark.asyncio
    async def test_get_cbr_rate_not_found(self, cbr_service):
        """Тест когда курс не найден"""
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.services.cbr_rate_service.cached_cbr_rate", AsyncMock(return_value=None))
            
            result = await cbr_service.get_cbr_rate(date(2025, 1, 1), "USD")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_process_today_rate_success(self, cbr_service):
        """Тест успешной обработки сегодняшнего курса"""
        today = date.today()
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.services.cbr_rate_service.cached_cbr_rate", AsyncMock(return_value=decimal.Decimal("90.50")))
            
            result = await cbr_service.process_today_rate(123, "USD")
            
            assert result["success"] is True
            assert result["rate"] == decimal.Decimal("90.50")
            assert result["currency"] == "USD"
            assert result["date"] == today
            assert "Курс ЦБ на сегодня" in result["message"]
    
    @pytest.mark.asyncio
    async def test_process_today_rate_not_found(self, cbr_service):
        """Тест когда сегодняшний курс недоступен"""
        today = date.today()
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.services.cbr_rate_service.cached_cbr_rate", AsyncMock(return_value=None))
            
            result = await cbr_service.process_today_rate(123, "USD")
            
            assert result["success"] is False
            assert result["rate"] is None
            assert result["currency"] == "USD"
            assert result["date"] == today
            assert "ещё не опубликован" in result["message"]
    
    @pytest.mark.asyncio
    async def test_process_tomorrow_rate_success(self, cbr_service):
        """Тест успешной обработки завтрашнего курса"""
        tomorrow = date.today() + timedelta(days=1)
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.services.cbr_rate_service.cached_cbr_rate", AsyncMock(return_value=decimal.Decimal("91.00")))
            
            result = await cbr_service.process_tomorrow_rate(123, "USD")
            
            assert result["success"] is True
            assert result["rate"] == decimal.Decimal("91.00")
            assert result["currency"] == "USD"
            assert result["date"] == tomorrow
            assert "Курс ЦБ на завтра" in result["message"]
    
    @pytest.mark.asyncio
    async def test_process_tomorrow_rate_not_found(self, cbr_service):
        """Тест когда завтрашний курс недоступен - запускается подписка"""
        tomorrow = date.today() + timedelta(days=1)
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.services.cbr_rate_service.cached_cbr_rate", AsyncMock(return_value=None))
            m.setattr("asyncio.create_task", MagicMock())
            
            result = await cbr_service.process_tomorrow_rate(123, "USD")
            
            assert result["success"] is False
            assert result["rate"] is None
            assert result["currency"] == "USD"
            assert result["date"] == tomorrow
            assert result["subscription_started"] is True
            assert "ещё не опубликован" in result["message"]
    
    @pytest.mark.asyncio
    async def test_monitor_tomorrow_rate_found(self, cbr_service, mock_bot):
        """Тест мониторинга завтрашнего курса - курс найден"""
        tomorrow = date.today() + timedelta(days=1)
        subscription_key = f"123:USD:{tomorrow.isoformat()}"
        
        with pytest.MonkeyPatch().context() as m:
            # Первая проверка - курс не найден
            # Вторая проверка - курс найден
            m.setattr("app.services.cbr_rate_service.cached_cbr_rate", 
                     AsyncMock(side_effect=[None, decimal.Decimal("91.00")]))
            
            await cbr_service._monitor_tomorrow_rate(123, "USD", tomorrow, subscription_key, max_hours=0.1)
            
            # Проверяем, что бот отправил сообщение
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert "Курс ЦБ на завтра" in call_args[0][1]
            assert "91.00" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_monitor_tomorrow_rate_timeout(self, cbr_service, mock_bot):
        """Тест мониторинга завтрашнего курса - превышено время ожидания"""
        tomorrow = date.today() + timedelta(days=1)
        subscription_key = f"123:USD:{tomorrow.isoformat()}"
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.services.cbr_rate_service.cached_cbr_rate", AsyncMock(return_value=None))
            
            await cbr_service._monitor_tomorrow_rate(123, "USD", tomorrow, subscription_key, max_hours=0.01)
            
            # Проверяем, что бот отправил сообщение о таймауте
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert "не появился" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_cancel_subscription(self, cbr_service):
        """Тест отмены подписки"""
        tomorrow = date.today() + timedelta(days=1)
        subscription_key = f"123:USD:{tomorrow.isoformat()}"
        
        # Создаем мок-задачу
        mock_task = MagicMock()
        cbr_service._subscription_tasks[subscription_key] = mock_task
        
        await cbr_service.cancel_subscription(123, "USD", tomorrow)
        
        # Проверяем, что задача была отменена
        mock_task.cancel.assert_called_once()
        assert subscription_key not in cbr_service._subscription_tasks
    
    @pytest.mark.asyncio
    async def test_cleanup(self, cbr_service):
        """Тест очистки ресурсов"""
        # Создаем несколько мок-задач
        mock_task1 = MagicMock()
        mock_task2 = MagicMock()
        cbr_service._subscription_tasks["task1"] = mock_task1
        cbr_service._subscription_tasks["task2"] = mock_task2
        
        await cbr_service.cleanup()
        
        # Проверяем, что все задачи были отменены
        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()
        assert len(cbr_service._subscription_tasks) == 0


class TestGlobalService:
    """Тесты для глобального сервиса"""
    
    @pytest.mark.asyncio
    async def test_get_cbr_service_singleton(self, mock_bot):
        """Тест что get_cbr_service возвращает синглтон"""
        service1 = await get_cbr_service(mock_bot)
        service2 = await get_cbr_service(mock_bot)
        
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_cleanup_cbr_service(self, mock_bot):
        """Тест очистки глобального сервиса"""
        service = await get_cbr_service(mock_bot)
        
        # Создаем мок-задачу
        mock_task = MagicMock()
        service._subscription_tasks["test"] = mock_task
        
        await cleanup_cbr_service()
        
        # Проверяем, что задача была отменена
        mock_task.cancel.assert_called_once() 