"""
Надёжный сервис для работы с курсами ЦБ.

Ключевые принципы:
1. НИКОГДА не подставляем вчерашние курсы вместо завтрашних
2. Только точная дата - никаких fallback на прошлые даты
3. Чёткое разделение логики для сегодня/завтра
4. Подписка на уведомления для завтрашних курсов
"""

import asyncio
import datetime as dt
from datetime import date, timedelta
from typing import Optional, Dict, Any
import decimal
import structlog

from app.services.rates_cache import get_rate as cached_cbr_rate
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
                requested_date, 
                currency, 
                cache_only=False,
                requested_tomorrow=requested_tomorrow
            )
            
            if rate is not None:
                log.info(
                    "cbr_rate_found_exact", 
                    date=str(requested_date), 
                    currency=currency, 
                    rate=str(rate)
                )
                return rate
            
            log.info(
                "cbr_rate_not_found", 
                date=str(requested_date), 
                currency=currency
            )
            return None
            
        except Exception as e:
            log.error(
                "cbr_rate_service_error", 
                date=str(requested_date), 
                currency=currency, 
                error=str(e)
            )
            return None
    
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
            return {
                "success": False,
                "rate": None,
                "message": message,
                "date": today,
                "currency": currency
            }
        
        message = (
            f"✅ <b>Курс ЦБ на сегодня ({today:%d.%m.%Y}):</b>\n"
            f"💱 <b>{currency}:</b> {rate:.4f} ₽"
        )
        
        return {
            "success": True,
            "rate": rate,
            "message": message,
            "date": today,
            "currency": currency
        }
    
    async def process_tomorrow_rate(self, user_id: int, currency: str) -> Dict[str, Any]:
        """
        Обработка курса за завтра.
        Если курс недоступен - подписывает на уведомление.
        """
        tomorrow = date.today() + timedelta(days=1)
        rate = await self.get_cbr_rate(tomorrow, currency)
        
        if rate is not None:
            message = (
                f"✅ <b>Курс ЦБ на завтра ({tomorrow:%d.%m.%Y}):</b>\n"
                f"💱 <b>{currency}:</b> {rate:.4f} ₽"
            )
            
            return {
                "success": True,
                "rate": rate,
                "message": message,
                "date": tomorrow,
                "currency": currency
            }
        
        # Курс недоступен - подписываем на уведомление
        subscription_key = f"{user_id}:{currency}:{tomorrow.isoformat()}"
        
        message = (
            "⏳ <b>Курс ЦБ на завтра ещё не опубликован.</b>\n\n"
            "📅 <b>Обычно он появляется после 17:00.</b>\n"
            "🔔 <b>Я пришлю вам уведомление, как только курс появится!</b>"
        )
        
        # Запускаем фоновую задачу для мониторинга
        if subscription_key not in self._subscription_tasks:
            task = asyncio.create_task(
                self._monitor_tomorrow_rate(user_id, currency, tomorrow, subscription_key)
            )
            self._subscription_tasks[subscription_key] = task
            
            log.info(
                "cbr_tomorrow_subscription_started",
                user_id=user_id,
                currency=currency,
                date=str(tomorrow)
            )
        
        return {
            "success": False,
            "rate": None,
            "message": message,
            "date": tomorrow,
            "currency": currency,
            "subscription_started": True
        }
    
    async def _monitor_tomorrow_rate(
        self, 
        user_id: int, 
        currency: str, 
        tomorrow: date, 
        subscription_key: str,
        max_hours: int = 15
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
                    
                    await self.bot.send_message(user_id, message, parse_mode="HTML")
                    
                    log.info(
                        "cbr_tomorrow_rate_found",
                        user_id=user_id,
                        currency=currency,
                        date=str(tomorrow),
                        rate=str(rate),
                        checks_made=check_num + 1
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
                    max_checks=max_checks
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
                    error=str(e)
                )
                await asyncio.sleep(180)
        
        # Превышено время ожидания
        timeout_message = (
            f"⚠️ <b>Курс ЦБ на завтра ({tomorrow:%d.%m.%Y}) не появился за {max_hours} часов.</b>\n\n"
            "🔄 <b>Попробуйте запросить курс позже или обратитесь к официальному сайту ЦБ.</b>"
        )
        
        try:
            await self.bot.send_message(user_id, timeout_message, parse_mode="HTML")
        except Exception as e:
            log.error("cbr_timeout_notification_failed", user_id=user_id, error=str(e))
        
        # Удаляем задачу из словаря
        if subscription_key in self._subscription_tasks:
            del self._subscription_tasks[subscription_key]
        
        log.info(
            "cbr_monitor_timeout",
            user_id=user_id,
            currency=currency,
            date=str(tomorrow),
            max_hours=max_hours
        )
    
    async def cancel_subscription(self, user_id: int, currency: str, date: date):
        """Отменяет подписку на уведомление о курсе"""
        subscription_key = f"{user_id}:{currency}:{date.isoformat()}"
        
        if subscription_key in self._subscription_tasks:
            task = self._subscription_tasks[subscription_key]
            task.cancel()
            del self._subscription_tasks[subscription_key]
            
            log.info(
                "cbr_subscription_cancelled",
                user_id=user_id,
                currency=currency,
                date=str(date)
            )
    
    async def cleanup(self):
        """Очистка ресурсов при завершении работы"""
        for task in self._subscription_tasks.values():
            task.cancel()
        
        self._subscription_tasks.clear()
        log.info("cbr_service_cleanup_complete")


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