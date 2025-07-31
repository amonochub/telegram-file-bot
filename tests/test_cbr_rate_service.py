"""
Тесты для надёжной системы курсов ЦБ
"""

import pytest
import asyncio
import decimal
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch

from app.services.cbr_rate_service import CBRRateService, get_cbr_service, cleanup_cbr_service


@pytest.fixture
def mock_rates_cache():
    """Мок для rates_cache функций"""
    return {
        "get_rate": AsyncMock(),
        "has_rate": AsyncMock(),
        "save_pending_calc": AsyncMock(),
        "get_all_pending": AsyncMock(),
        "remove_pending": AsyncMock(),
        "add_subscriber": AsyncMock(),
        "remove_subscriber": AsyncMock(),
        "get_subscribers": AsyncMock(),
        "is_subscriber": AsyncMock(),
        "toggle_subscription": AsyncMock(),
    }


@pytest.fixture
def mock_bot():
    """Мок для бота"""
    return MagicMock()


@pytest.fixture
def service(mock_bot):
    """Создаёт экземпляр CBRRateService с мок-ботом"""
    return CBRRateService(bot=mock_bot)


class TestCBRRateService:
    """Тесты для CBRRateService"""

    @pytest.fixture
    def service(self):
        """Создаёт экземпляр сервиса для тестов"""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        return CBRRateService(bot=bot)

    @pytest.fixture
    def mock_rates_cache(self, monkeypatch):
        """Мокает функции rates_cache"""
        mock_get_rate = AsyncMock()
        mock_has_rate = AsyncMock()
        mock_save_pending = AsyncMock()
        mock_get_all_pending = AsyncMock()
        mock_remove_pending = AsyncMock()

        monkeypatch.setattr("app.services.cbr_rate_service.cached_cbr_rate", mock_get_rate)
        monkeypatch.setattr("app.services.cbr_rate_service.has_rate", mock_has_rate)
        monkeypatch.setattr("app.services.cbr_rate_service.save_pending_calc", mock_save_pending)
        monkeypatch.setattr("app.services.cbr_rate_service.get_all_pending", mock_get_all_pending)
        monkeypatch.setattr("app.services.cbr_rate_service.remove_pending", mock_remove_pending)

        return {
            "get_rate": mock_get_rate,
            "has_rate": mock_has_rate,
            "save_pending": mock_save_pending,
            "get_all_pending": mock_get_all_pending,
            "remove_pending": mock_remove_pending,
        }

    @pytest.mark.asyncio
    async def test_get_cbr_rate_success(self, service, mock_rates_cache):
        """Тест успешного получения курса"""
        test_date = date.today()
        mock_rates_cache["get_rate"].return_value = decimal.Decimal("95.1234")

        result = await service.get_cbr_rate(test_date, "EUR")

        assert result == decimal.Decimal("95.1234")
        mock_rates_cache["get_rate"].assert_called_once_with(
            test_date, "EUR", cache_only=False, requested_tomorrow=False
        )

    @pytest.mark.asyncio
    async def test_get_cbr_rate_not_found(self, service, mock_rates_cache):
        """Тест когда курс не найден"""
        test_date = date.today()
        mock_rates_cache["get_rate"].return_value = None

        result = await service.get_cbr_rate(test_date, "EUR")

        assert result is None

    @pytest.mark.asyncio
    async def test_process_today_rate_success(self, service, mock_rates_cache):
        """Тест успешной обработки сегодняшнего курса"""
        mock_rates_cache["get_rate"].return_value = decimal.Decimal("95.1234")

        result = await service.process_today_rate(123, "EUR")

        assert result["success"] is True
        assert result["rate"] == decimal.Decimal("95.1234")
        assert "95.1234" in result["message"]

    @pytest.mark.asyncio
    async def test_process_today_rate_not_found(self, service, mock_rates_cache):
        """Тест когда сегодняшний курс не найден"""
        mock_rates_cache["get_rate"].return_value = None

        result = await service.process_today_rate(123, "EUR")

        assert result["success"] is False
        assert result["rate"] is None
        assert "не опубликован" in result["message"]

    @pytest.mark.asyncio
    async def test_process_tomorrow_rate_success(self, service, mock_rates_cache):
        """Тест успешной обработки завтрашнего курса"""
        mock_rates_cache["get_rate"].return_value = decimal.Decimal("95.1234")

        result = await service.process_tomorrow_rate(123, "EUR")

        assert result["success"] is True
        assert result["rate"] == decimal.Decimal("95.1234")
        assert "95.1234" in result["message"]

    @pytest.mark.asyncio
    async def test_process_tomorrow_rate_not_found(self, service, mock_rates_cache):
        """Тест когда завтрашний курс не найден"""
        mock_rates_cache["get_rate"].return_value = None

        result = await service.process_tomorrow_rate(123, "EUR")

        assert result["success"] is False
        assert result["rate"] is None
        assert "не опубликован" in result["message"]
        assert result["subscription_started"] is True

    @pytest.mark.asyncio
    async def test_save_pending_calc_success(self, service, mock_rates_cache):
        """Тест успешного сохранения отложенного расчёта"""
        mock_rates_cache["save_pending"].return_value = True
        test_date = date.today() + timedelta(days=1)

        result = await service.save_pending_calc(123, test_date, "EUR", decimal.Decimal("1000"), decimal.Decimal("5"))

        assert result is True
        mock_rates_cache["save_pending"].assert_called_once_with(
            123, test_date, "EUR", decimal.Decimal("1000"), decimal.Decimal("5")
        )

    @pytest.mark.asyncio
    async def test_save_pending_calc_failure(self, service, mock_rates_cache):
        """Тест неудачного сохранения отложенного расчёта"""
        mock_rates_cache["save_pending"].return_value = False
        test_date = date.today() + timedelta(days=1)

        result = await service.save_pending_calc(123, test_date, "EUR", decimal.Decimal("1000"), decimal.Decimal("5"))

        assert result is False

    @pytest.mark.asyncio
    async def test_process_pending_calcs_success(self, service, mock_rates_cache):
        """Тест успешной обработки отложенных расчётов"""
        test_date = date.today() + timedelta(days=1)
        mock_rates_cache["get_all_pending"].return_value = [
            {
                "user_id": 123,
                "date": test_date.isoformat(),
                "currency": "EUR",
                "amount": "1000",
                "commission": "5",
                "created_at": "2025-01-01T12:00:00",
            }
        ]
        mock_rates_cache["remove_pending"].return_value = True

        rates = {"EUR": decimal.Decimal("95.1234")}
        await service.process_pending_calcs(rates, test_date)

        # Проверяем, что сообщение было отправлено
        service.bot.send_message.assert_called_once()
        call_args = service.bot.send_message.call_args
        assert call_args[0][0] == 123  # user_id
        assert "Расчёт для клиента (отложенный)" in call_args[0][1]  # message

        # Проверяем, что отложенный расчёт был удалён
        mock_rates_cache["remove_pending"].assert_called_once_with(123, test_date)

    @pytest.mark.asyncio
    async def test_process_pending_calcs_currency_not_found(self, service, mock_rates_cache):
        """Тест обработки отложенных расчётов когда валюта не найдена"""
        test_date = date.today() + timedelta(days=1)
        mock_rates_cache["get_all_pending"].return_value = [
            {
                "user_id": 123,
                "date": test_date.isoformat(),
                "currency": "USD",
                "amount": "1000",
                "commission": "5",
                "created_at": "2025-01-01T12:00:00",
            }
        ]
        mock_rates_cache["remove_pending"].return_value = True

        rates = {"EUR": decimal.Decimal("95.1234")}  # USD нет в rates
        await service.process_pending_calcs(rates, test_date)

        # Проверяем, что сообщение об ошибке было отправлено
        service.bot.send_message.assert_called_once()
        call_args = service.bot.send_message.call_args
        assert call_args[0][0] == 123  # user_id
        assert "не найден" in call_args[0][1]  # error message

        # Проверяем, что отложенный расчёт был удалён
        mock_rates_cache["remove_pending"].assert_called_once_with(123, test_date)

    def test_format_calc_result(self, service):
        """Тест форматирования результата расчёта"""
        result = service._format_calc_result(
            "EUR", decimal.Decimal("1000"), decimal.Decimal("95.1234"), decimal.Decimal("5")
        )

        assert "EUR" in result
        assert "1000" in result
        assert "95.1234" in result
        assert "5%" in result
        assert "Расчёт для клиента (отложенный)" in result

    @pytest.mark.asyncio
    async def test_monitor_tomorrow_rate_found(self, service, mock_rates_cache):
        """Тест мониторинга когда курс найден"""
        tomorrow = date.today() + timedelta(days=1)
        mock_rates_cache["get_rate"].return_value = decimal.Decimal("95.1234")
        mock_rates_cache["get_all_pending"].return_value = []

        # Запускаем мониторинг
        task = asyncio.create_task(service._monitor_tomorrow_rate(123, "EUR", tomorrow, "test_key", max_hours=0.1))

        # Ждём завершения
        await asyncio.sleep(0.2)

        # Проверяем, что сообщение было отправлено
        service.bot.send_message.assert_called()

        # Очищаем задачу
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_monitor_tomorrow_rate_timeout(self, service, mock_rates_cache):
        """Тест мониторинга с таймаутом"""
        tomorrow = date.today() + timedelta(days=1)
        mock_rates_cache["get_rate"].return_value = None  # Курс не найден

        # Запускаем мониторинг с коротким таймаутом
        task = asyncio.create_task(service._monitor_tomorrow_rate(123, "EUR", tomorrow, "test_key", max_hours=0.01))

        # Ждём завершения (увеличиваем время ожидания)
        await asyncio.sleep(0.5)

        # Проверяем, что сообщение о таймауте было отправлено
        service.bot.send_message.assert_called()
        call_args = service.bot.send_message.call_args
        assert "не появился" in call_args[0][1]  # timeout message

        # Очищаем задачу
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, service):
        """Тест отмены подписки"""
        # Создаём мок-задачу
        mock_task = MagicMock()
        test_date = date.today()
        subscription_key = f"123:EUR:{test_date.isoformat()}"
        service._subscription_tasks[subscription_key] = mock_task

        await service.cancel_subscription(123, "EUR", test_date)

        # Проверяем, что задача была отменена и удалена
        mock_task.cancel.assert_called_once()
        assert subscription_key not in service._subscription_tasks

    @pytest.mark.asyncio
    async def test_cleanup(self, service):
        """Тест очистки ресурсов"""
        # Создаём мок-задачи
        mock_task1 = MagicMock()
        mock_task2 = MagicMock()
        service._subscription_tasks["key1"] = mock_task1
        service._subscription_tasks["key2"] = mock_task2

        await service.cleanup()

        # Проверяем, что все задачи были отменены и удалены
        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()
        assert len(service._subscription_tasks) == 0

    @pytest.mark.asyncio
    async def test_send_message_safe_success(self, service):
        """Тест успешной отправки сообщения"""
        service.bot.send_message.return_value = None

        result = await service.send_message_safe(123, "test message")

        assert result is True
        service.bot.send_message.assert_called_once_with(123, "test message")

    @pytest.mark.asyncio
    async def test_send_message_safe_bot_blocked(self, service):
        """Тест отправки сообщения заблокированному пользователю"""
        service.bot.send_message.side_effect = Exception("bot was blocked by the user")

        result = await service.send_message_safe(123, "test message")

        assert result is False
        service.bot.send_message.assert_called_once_with(123, "test message")

    @pytest.mark.asyncio
    async def test_send_message_safe_no_bot(self):
        """Тест отправки сообщения без бота"""
        service = CBRRateService(bot=None)

        result = await service.send_message_safe(123, "test message")

        assert result is False

    @pytest.mark.asyncio
    async def test_notify_all_subscribers_success(self, service):
        """Тест уведомления всех подписчиков"""
        with patch("app.services.cbr_rate_service.get_subscribers") as mock_get_subscribers:
            mock_get_subscribers.return_value = [123, 456]
            service.bot.send_message.return_value = None

            result = await service.notify_all_subscribers("test message")

            assert result["sent"] == 2
            assert result["failed"] == 0
            assert result["total"] == 2
            assert service.bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_notify_all_subscribers_partial_failure(self, service):
        """Тест частичного сбоя при уведомлении подписчиков"""
        with patch("app.services.cbr_rate_service.get_subscribers") as mock_get_subscribers:
            mock_get_subscribers.return_value = [123, 456, 789]
            service.bot.send_message.side_effect = [
                None,  # 123 - успех
                Exception("bot was blocked"),  # 456 - сбой
                None,  # 789 - успех
            ]

            result = await service.notify_all_subscribers("test message")

            assert result["sent"] == 2
            assert result["failed"] == 1
            assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_add_subscriber_success(self, service, mock_rates_cache):
        """Тест успешного добавления подписчика"""
        with patch("app.services.cbr_rate_service.add_subscriber") as mock_add:
            mock_add.return_value = True

            result = await service.add_subscriber(123)

            assert result is True
            mock_add.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_remove_subscriber_success(self, service, mock_rates_cache):
        """Тест успешного удаления подписчика"""
        with patch("app.services.cbr_rate_service.remove_subscriber") as mock_remove:
            mock_remove.return_value = True

            result = await service.remove_subscriber(123)

            assert result is True
            mock_remove.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_is_subscriber_success(self, service, mock_rates_cache):
        """Тест проверки подписки"""
        with patch("app.services.cbr_rate_service.is_subscriber") as mock_is_sub:
            mock_is_sub.return_value = True

            result = await service.is_subscriber(123)

            assert result is True
            mock_is_sub.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_toggle_subscription_subscribe(self, service, mock_rates_cache):
        """Тест переключения подписки - подписка"""
        with patch("app.services.cbr_rate_service.toggle_subscription") as mock_toggle:
            mock_toggle.return_value = {"subscribed": True, "action": "subscribed", "message": "✅ Подписка активна"}

            result = await service.toggle_subscription(123)

            assert result["subscribed"] is True
            assert result["action"] == "subscribed"
            mock_toggle.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_toggle_subscription_unsubscribe(self, service, mock_rates_cache):
        """Тест переключения подписки - отписка"""
        with patch("app.services.cbr_rate_service.toggle_subscription") as mock_toggle:
            mock_toggle.return_value = {
                "subscribed": False,
                "action": "unsubscribed",
                "message": "❌ Отписка выполнена",
            }

            result = await service.toggle_subscription(123)

            assert result["subscribed"] is False
            assert result["action"] == "unsubscribed"
            mock_toggle.assert_called_once_with(123)


class TestGlobalService:
    """Тесты для глобальных функций сервиса"""

    @pytest.mark.asyncio
    async def test_get_cbr_service_singleton(self):
        """Тест что get_cbr_service возвращает синглтон"""
        # Очищаем глобальный сервис
        await cleanup_cbr_service()

        service1 = await get_cbr_service()
        service2 = await get_cbr_service()

        assert service1 is service2

    @pytest.mark.asyncio
    async def test_cleanup_cbr_service(self):
        """Тест очистки глобального сервиса"""
        service = await get_cbr_service()
        assert service is not None

        await cleanup_cbr_service()

        # Создаём новый сервис
        new_service = await get_cbr_service()
        assert new_service is not service
