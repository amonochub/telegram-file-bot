"""
Middleware для проверки разрешенных пользователей
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)


class UserCheckMiddleware(BaseMiddleware):
    """Middleware для проверки разрешенных пользователей"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем user_id из события
        if not hasattr(event, 'from_user'):
            return await handler(event, data)
        user_id = event.from_user.id

        # Проверяем, разрешен ли доступ пользователю
        if not settings.is_user_allowed(user_id):
            logger.warning("access_denied", user_id=user_id, allowed_users=settings.allowed_user_ids)

            # Отправляем сообщение об отказе в доступе
            if isinstance(event, Message):
                await event.answer("❌ Доступ запрещен. Обратитесь к администратору для получения доступа.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Доступ запрещен", show_alert=True)
            return

        # Если доступ разрешен, продолжаем обработку
        logger.debug("access_granted", user_id=user_id, allowed_users=settings.allowed_user_ids)

        return await handler(event, data)
