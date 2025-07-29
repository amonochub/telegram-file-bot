"""
Middleware для глобальной обработки ошибок
"""

import structlog
from aiogram.types import Message, CallbackQuery


# Создаем базовый класс для middleware, если он недоступен
class BaseMiddleware:
    """Базовый класс для middleware"""

    async def __call__(self, handler, event, data):
        return await handler(event, data)


log = structlog.get_logger()


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware для обработки ошибок в обработчиках"""

    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            # Получаем user_id безопасно
            user_id = "unknown"
            chat_id = "unknown"

            if hasattr(event, "from_user") and event.from_user:
                user_id = getattr(event.from_user, "id", "unknown")

            if hasattr(event, "chat") and event.chat:
                chat_id = getattr(event.chat, "id", "unknown")
            elif hasattr(event, "message") and event.message and hasattr(event.message, "chat"):
                chat_id = getattr(event.message.chat, "id", "unknown")

            # Обрабатываем все ошибки как общие
            log.error(
                "Unexpected error in handler",
                error=str(e),
                error_type=type(e).__name__,
                user_id=user_id,
                chat_id=chat_id,
            )

            # Отправляем пользователю понятное сообщение
            if isinstance(event, (Message, CallbackQuery)):
                try:
                    if isinstance(event, Message):
                        await event.answer("❌ Произошла внутренняя ошибка. Обратитесь к администратору.")
                    else:
                        await event.message.answer("❌ Произошла внутренняя ошибка. Обратитесь к администратору.")
                except Exception:
                    pass  # Не можем отправить сообщение об ошибке

            return None
