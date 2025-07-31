"""
Надёжный сервис для работы с курсами ЦБ.

Ключевые принципы:
1. НИКОГДА не подставляем вчерашние курсы вместо завтрашних
2. Только точная дата - никаких fallback на прошлые даты
3. Чёткое разделение логики для сегодня/завтра
4. Подписка на уведомления для завтрашних курсов
5. Отложенные расчёты при недоступности курса
"""

import asyncio
import datetime as dt
from datetime import date, timedelta
from typing import Optional, Dict, Any
import decimal
import structlog

from app.utils.types import BusinessDate, CurrencyCode

from app.services.rates_cache import (
    get_rate as cached_cbr_rate,
    has_rate,
    save_pending_calc,
    get_all_pending,
    remove_pending,
    add_subscriber,
    remove_subscriber,
    get_subscribers,
    is_subscriber,
    toggle_subscription,
)
from app.services.cbr_notifier import CBRNotificationService
from app.config import settings

log = structlog.get_logger(__name__)


class CBRRateService:
    """Надёжный сервис для работы с курсами ЦБ"""

    def __init__(self, bot=None, redis_url: str = None):
        self.bot = bot
        self.redis_url = redis_url or settings.redis_url
        self.notifier = CBRNotificationService(bot, self.redis_url) if bot else None
        self._subscription_tasks: Dict[str, asyncio.Task] = {}

    async def get_cbr_rate(self, requested_date: date, currency: str) -> Optional[decimal.Decimal]:
        """
        Возвращает официальный курс ЦБ за нужную дату.
        Только если он реально есть на сайте/в кэше!
        Если нет — возвращает None.
        """
        try:
            # Определяем, запрашиваем ли мы завтрашний курс
            tomorrow = date.today() + timedelta(days=1)
            requested_tomorrow = requested_date == tomorrow

            rate = await cached_cbr_rate(
                requested_date, currency, cache_only=False, requested_tomorrow=requested_tomorrow
            )

            if rate is not None:
                log.info("cbr_rate_found_exact", date=str(requested_date), currency=currency, rate=str(rate))
                return rate

            log.info("cbr_rate_not_found", date=str(requested_date), currency=currency)
            return None

        except Exception as e:
            log.error("cbr_rate_service_error", date=str(requested_date), currency=currency, error=str(e))
            return None

    async def save_pending_calc(
        self, user_id: int, date: BusinessDate, currency: CurrencyCode, amount: decimal.Decimal, commission: decimal.Decimal
    ) -> bool:
        """
        Сохраняет отложенный расчёт.

        Args:
            user_id: ID пользователя
            date: Дата для расчёта
            currency: Валюта
            amount: Сумма
            commission: Комиссия в процентах

        Returns:
            True если сохранено успешно
        """
        try:
            result = await save_pending_calc(user_id, date, currency, amount, commission)
            if result:
                log.info(
                    "cbr_pending_calc_saved",
                    user_id=user_id,
                    date=str(date),
                    currency=currency,
                    amount=str(amount),
                    commission=str(commission),
                )
            return result
        except Exception as e:
            log.error("cbr_save_pending_calc_error", user_id=user_id, date=str(date), error=str(e))
            return False

    async def process_pending_calcs(self, rates: Dict[str, decimal.Decimal], target_date: date) -> None:
        """
        Обрабатывает все отложенные расчёты для указанной даты.

        Args:
            rates: Словарь курсов валют
            target_date: Дата, для которой обрабатываются расчёты
        """
        if not self.bot:
            log.error("cbr_process_pending_calcs_no_bot")
            return

        try:
            pending_calcs = await get_all_pending()

            for calc_data in pending_calcs:
                try:
                    calc_date = date.fromisoformat(calc_data["date"])

                    # Обрабатываем только расчёты для целевой даты
                    if calc_date != target_date:
                        continue

                    user_id = calc_data["user_id"]
                    currency = calc_data["currency"]
                    amount = decimal.Decimal(calc_data["amount"])
                    commission = decimal.Decimal(calc_data["commission"])

                    # Проверяем, есть ли курс для этой валюты
                    if currency in rates:
                        rate = rates[currency]

                        # Выполняем расчёт
                        result_message = self._format_calc_result(currency, amount, rate, commission)

                        # Отправляем результат пользователю
                        await self.send_message_safe(user_id, result_message, parse_mode="HTML")

                        # Удаляем отложенный расчёт
                        await remove_pending(user_id, target_date)

                        log.info(
                            "cbr_pending_calc_processed",
                            user_id=user_id,
                            date=str(target_date),
                            currency=currency,
                            rate=str(rate),
                        )
                    else:
                        # Курс для валюты не найден
                        error_message = (
                            f"⚠️ <b>Курс {currency} на {target_date:%d.%m.%Y} не найден.</b>\n\n"
                            "🔄 <b>Расчёт выполнить не удалось.</b>\n"
                            "📅 <b>Попробуйте запросить расчёт позже.</b>"
                        )

                        await self.send_message_safe(user_id, error_message, parse_mode="HTML")

                        # Удаляем отложенный расчёт
                        await remove_pending(user_id, target_date)

                        log.warning(
                            "cbr_pending_calc_currency_not_found",
                            user_id=user_id,
                            date=str(target_date),
                            currency=currency,
                        )

                except Exception as e:
                    log.error("cbr_process_pending_calc_error", calc_data=calc_data, error=str(e))

        except Exception as e:
            log.error("cbr_process_pending_calcs_error", error=str(e))

    def _format_calc_result(
        self, currency: str, amount: decimal.Decimal, rate: decimal.Decimal, commission: decimal.Decimal
    ) -> str:
        """
        Форматирует результат расчёта.

        Args:
            currency: Валюта
            amount: Сумма
            rate: Курс
            commission: Комиссия в процентах

        Returns:
            Отформатированное сообщение с результатом
        """
        rub_sum = (amount * rate).quantize(decimal.Decimal("0.01"))
        commission_amount = (rub_sum * commission / 100).quantize(decimal.Decimal("0.01"))
        total = rub_sum + commission_amount

        return (
            f"💰 <b>Расчёт для клиента (отложенный)</b>\n\n"
            f"💱 <b>Валюта:</b> {currency}\n"
            f"💵 <b>Сумма:</b> {amount} {currency}\n"
            f"📊 <b>Курс ЦБ:</b> {rate:.4f} ₽\n"
            f"💸 <b>Сумма в рублях:</b> {rub_sum} ₽\n"
            f"💼 <b>Комиссия ({commission}%):</b> {commission_amount} ₽\n"
            f"🎯 <b>Итого к оплате:</b> {total} ₽"
        )

    async def process_today_rate(self, user_id: int, currency: str) -> Dict[str, Any]:
        """
        Обработка курса за сегодня.
        Возвращает словарь с результатом и сообщением для пользователя.
        """
        today = date.today()
        rate = await self.get_cbr_rate(today, currency)

        if rate is None:
            message = (
                "⏳ <b>Курс ЦБ на сегодня ещё не опубликован.</b>\n\n"
                "📅 <b>Обычно курс появляется после 11:30.</b>\n"
                "🔄 <b>Попробуйте позже или запросите курс на завтра.</b>"
            )
            return {"success": False, "rate": None, "message": message, "date": today, "currency": currency}

        message = f"✅ <b>Курс ЦБ на сегодня ({today:%d.%m.%Y}):</b>\n" f"💱 <b>{currency}:</b> {rate:.4f} ₽"

        return {"success": True, "rate": rate, "message": message, "date": today, "currency": currency}

    async def process_tomorrow_rate(self, user_id: int, currency: str) -> Dict[str, Any]:
        """
        Обработка курса за завтра.
        Если курс недоступен - подписывает на уведомление.
        """
        tomorrow = date.today() + timedelta(days=1)
        rate = await self.get_cbr_rate(tomorrow, currency)

        if rate is not None:
            message = f"✅ <b>Курс ЦБ на завтра ({tomorrow:%d.%m.%Y}):</b>\n" f"💱 <b>{currency}:</b> {rate:.4f} ₽"

            return {"success": True, "rate": rate, "message": message, "date": tomorrow, "currency": currency}

        # Курс недоступен - подписываем на уведомление
        subscription_key = f"{user_id}:{currency}:{tomorrow.isoformat()}"

        message = (
            "⏳ <b>Курс ЦБ на завтра ещё не опубликован.</b>\n\n"
            "📅 <b>Обычно он появляется после 17:00.</b>\n"
            "🔔 <b>Я пришлю вам уведомление, как только курс появится!</b>"
        )

        # Запускаем фоновую задачу для мониторинга
        if subscription_key not in self._subscription_tasks:
            task = asyncio.create_task(self._monitor_tomorrow_rate(user_id, currency, tomorrow, subscription_key))
            self._subscription_tasks[subscription_key] = task

            log.info("cbr_tomorrow_subscription_started", user_id=user_id, currency=currency, date=str(tomorrow))

        return {
            "success": False,
            "rate": None,
            "message": message,
            "date": tomorrow,
            "currency": currency,
            "subscription_started": True,
        }

    async def _monitor_tomorrow_rate(
        self, user_id: int, currency: str, tomorrow: date, subscription_key: str, max_hours: int = 15
    ):
        """
        Фоновая задача для мониторинга появления завтрашнего курса.
        Проверяет каждые 3 минуты в течение max_hours часов.
        """
        if not self.bot:
            log.error("cbr_monitor_no_bot", user_id=user_id)
            return

        max_checks = int((max_hours * 60) / 3)  # каждые 3 минуты

        for check_num in range(max_checks):
            try:
                rate = await self.get_cbr_rate(tomorrow, currency)

                if rate is not None:
                    # Курс появился!
                    message = (
                        f"✅ <b>Курс ЦБ на завтра ({tomorrow:%d.%m.%Y}) опубликован:</b>\n"
                        f"💱 <b>{currency}:</b> {rate:.4f} ₽"
                    )

                    # Отправляем сообщение пользователю, который запросил курс
                    await self.send_message_safe(user_id, message, parse_mode="HTML")

                    # Уведомляем всех подписчиков о появлении курса
                    general_message = (
                        f"🚨 <b>КУРС ЦБ НА ЗАВТРА ОПУБЛИКОВАН!</b>\n\n"
                        f"📅 <b>Дата:</b> {tomorrow:%d.%m.%Y}\n"
                        f"💱 <b>{currency}:</b> {rate:.4f} ₽\n\n"
                        f"⏰ <b>Время публикации:</b> {dt.datetime.now().strftime('%H:%M')}"
                    )

                    await self.notify_all_subscribers(general_message, parse_mode="HTML")

                    # Обрабатываем отложенные расчёты для этой даты
                    rates = {currency: rate}
                    await self.process_pending_calcs(rates, tomorrow)

                    log.info(
                        "cbr_tomorrow_rate_found",
                        user_id=user_id,
                        currency=currency,
                        date=str(tomorrow),
                        rate=str(rate),
                        checks_made=check_num + 1,
                    )

                    # Удаляем задачу из словаря
                    if subscription_key in self._subscription_tasks:
                        del self._subscription_tasks[subscription_key]

                    return

                log.debug(
                    "cbr_monitor_check",
                    user_id=user_id,
                    currency=currency,
                    date=str(tomorrow),
                    check_num=check_num + 1,
                    max_checks=max_checks,
                )

                # Ждём 3 минуты перед следующей проверкой
                await asyncio.sleep(180)

            except Exception as e:
                log.error(
                    "cbr_monitor_error",
                    user_id=user_id,
                    currency=currency,
                    date=str(tomorrow),
                    check_num=check_num + 1,
                    error=str(e),
                )
                await asyncio.sleep(180)

        # Превышено время ожидания
        timeout_message = (
            f"⚠️ <b>Курс ЦБ на завтра ({tomorrow:%d.%m.%Y}) не появился за {max_hours} часов.</b>\n\n"
            "🔄 <b>Попробуйте запросить курс позже или обратитесь к официальному сайту ЦБ.</b>"
        )

        await self.send_message_safe(user_id, timeout_message, parse_mode="HTML")

        # Удаляем задачу из словаря
        if subscription_key in self._subscription_tasks:
            del self._subscription_tasks[subscription_key]

        log.info("cbr_monitor_timeout", user_id=user_id, currency=currency, date=str(tomorrow), max_hours=max_hours)

    async def cancel_subscription(self, user_id: int, currency: str, date: date):
        """Отменяет подписку на уведомление о курсе"""
        subscription_key = f"{user_id}:{currency}:{date.isoformat()}"

        if subscription_key in self._subscription_tasks:
            task = self._subscription_tasks[subscription_key]
            task.cancel()
            del self._subscription_tasks[subscription_key]

            log.info("cbr_subscription_cancelled", user_id=user_id, currency=currency, date=str(date))

    async def cleanup(self):
        """Очистка ресурсов при завершении работы"""
        for task in self._subscription_tasks.values():
            task.cancel()

        self._subscription_tasks.clear()
        log.info("cbr_service_cleanup_complete")

    async def add_subscriber(self, user_id: int) -> bool:
        """
        Добавляет пользователя в список подписчиков.

        Args:
            user_id: ID пользователя

        Returns:
            True если добавлен успешно
        """
        try:
            result = await add_subscriber(user_id)
            if result:
                log.info("cbr_service_subscriber_added", user_id=user_id)
            return result
        except Exception as e:
            log.error("cbr_service_add_subscriber_error", user_id=user_id, error=str(e))
            return False

    async def remove_subscriber(self, user_id: int) -> bool:
        """
        Удаляет пользователя из списка подписчиков.

        Args:
            user_id: ID пользователя

        Returns:
            True если удалён успешно
        """
        try:
            result = await remove_subscriber(user_id)
            if result:
                log.info("cbr_service_subscriber_removed", user_id=user_id)
            return result
        except Exception as e:
            log.error("cbr_service_remove_subscriber_error", user_id=user_id, error=str(e))
            return False

    async def is_subscriber(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь подписчиком.

        Args:
            user_id: ID пользователя

        Returns:
            True если пользователь подписан
        """
        try:
            return await is_subscriber(user_id)
        except Exception as e:
            log.error("cbr_service_check_subscriber_error", user_id=user_id, error=str(e))
            return False

    async def toggle_subscription(self, user_id: int) -> Dict[str, Any]:
        """
        Переключает подписку пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь с результатом операции
        """
        try:
            result = await toggle_subscription(user_id)
            log.info("cbr_service_toggle_subscription", user_id=user_id, action=result["action"])
            return result
        except Exception as e:
            log.error("cbr_service_toggle_subscription_error", user_id=user_id, error=str(e))
            return {
                "subscribed": False,
                "action": "error",
                "message": "❌ <b>Произошла ошибка при изменении подписки.</b>",
            }

    async def send_message_safe(self, user_id: int, message: str, **kwargs) -> bool:
        """
        Безопасная отправка сообщения с обработкой ошибок.

        Args:
            user_id: ID пользователя
            message: Текст сообщения
            **kwargs: Дополнительные параметры для send_message

        Returns:
            True если сообщение отправлено успешно, False если ошибка
        """
        if not self.bot:
            log.error("cbr_send_message_no_bot", user_id=user_id)
            return False

        try:
            await self.bot.send_message(user_id, message, **kwargs)
            return True
        except Exception as e:
            log.error("cbr_send_message_error", user_id=user_id, error=str(e))

            # Если пользователь заблокировал бота или удалил его
            if "bot was blocked" in str(e).lower() or "user not found" in str(e).lower():
                log.warning("cbr_user_blocked_or_deleted", user_id=user_id)
                # Удаляем пользователя из подписчиков
                await self.remove_subscriber(user_id)

            return False

    async def notify_all_subscribers(self, message: str, **kwargs) -> Dict[str, int]:
        """
        Отправляет уведомление всем подписчикам.

        Args:
            message: Текст сообщения
            **kwargs: Дополнительные параметры для send_message

        Returns:
            Словарь с результатами: {"sent": int, "failed": int, "total": int}
        """
        try:
            subscribers = await get_subscribers()
            sent = 0
            failed = 0

            for user_id in subscribers:
                if await self.send_message_safe(user_id, message, **kwargs):
                    sent += 1
                else:
                    failed += 1

            result = {"sent": sent, "failed": failed, "total": len(subscribers)}

            log.info("cbr_notify_all_subscribers", **result)
            return result

        except Exception as e:
            log.error("cbr_notify_all_subscribers_error", error=str(e))
            return {"sent": 0, "failed": 0, "total": 0}


# Глобальный экземпляр сервиса
_cbr_service: Optional[CBRRateService] = None


async def get_cbr_service(bot=None) -> CBRRateService:
    """Получение глобального экземпляра сервиса курсов ЦБ"""
    global _cbr_service

    if _cbr_service is None:
        _cbr_service = CBRRateService(bot)

    return _cbr_service


async def cleanup_cbr_service():
    """Очистка глобального сервиса курсов ЦБ"""
    global _cbr_service

    if _cbr_service is not None:
        await _cbr_service.cleanup()
        _cbr_service = None
