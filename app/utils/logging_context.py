"""
Утилиты для контекстного логирования
"""

import structlog
from typing import Any, Dict, Optional
from aiogram.types import Message, CallbackQuery


def get_user_context(event):
    common = {
        "user_id": getattr(event.from_user, "id", None),
        "username": getattr(event.from_user, "username", None),
        "first_name": getattr(event.from_user, "first_name", None),
    }

    # Проверяем наличие атрибутов для определения типа события
    if hasattr(event, "message_id") and hasattr(event, "text"):
        # Это Message
        return {
            **common,
            "chat_id": getattr(event.chat, "id", None),
            "chat_type": getattr(event.chat, "type", None),
            "message_id": getattr(event, "message_id", None),
            "text": getattr(event, "text", None),
            "message_type": "message",
        }
    elif hasattr(event, "data") and hasattr(event, "message"):
        # Это CallbackQuery
        msg = getattr(event, "message", None)
        chat = getattr(msg, "chat", None) if msg else None

        return {
            **common,
            "chat_id": getattr(chat, "id", None) if chat else None,
            "chat_type": getattr(chat, "type", None) if chat else None,
            "message_id": getattr(msg, "message_id", None) if msg else None,
            "callback_data": getattr(event, "data", None),
            "message_type": "callback",
        }
    return common


def log_handler_call(handler_name: str, event: Message | CallbackQuery, **kwargs) -> None:
    """
    Логирует вызов обработчика с контекстом

    Args:
        handler_name: Название обработчика
        event: Событие Telegram
        **kwargs: Дополнительные параметры для логирования
    """
    log = structlog.get_logger()
    context = get_user_context(event)
    context.update(kwargs)

    log.info(f"{handler_name} called", **context)


def log_handler_error(handler_name: str, event: Message | CallbackQuery, error: Exception, **kwargs) -> None:
    """
    Логирует ошибку в обработчике с контекстом

    Args:
        handler_name: Название обработчика
        event: Событие Telegram
        error: Исключение
        **kwargs: Дополнительные параметры для логирования
    """
    log = structlog.get_logger()
    context = get_user_context(event)
    context.update({"error": str(error), "error_type": type(error).__name__, **kwargs})

    log.error(f"{handler_name} error", **context)
