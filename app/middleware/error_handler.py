"""
Middleware для глобальной обработки ошибок
"""

import structlog
from aiogram.types import Message, CallbackQuery

from app.utils.exceptions import (
    FileValidationError,
    CBRServiceError,
    YandexDiskError,
    OCRProcessingError,
    UserNotAllowedError,
    RateNotFoundError,
    CalculationError,
)


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
        except FileValidationError as e:
            await self._handle_file_validation_error(event, e)
        except CBRServiceError as e:
            await self._handle_cbr_service_error(event, e)
        except YandexDiskError as e:
            await self._handle_yandex_disk_error(event, e)
        except OCRProcessingError as e:
            await self._handle_ocr_error(event, e)
        except UserNotAllowedError as e:
            await self._handle_user_not_allowed_error(event, e)
        except RateNotFoundError as e:
            await self._handle_rate_not_found_error(event, e)
        except CalculationError as e:
            await self._handle_calculation_error(event, e)
        except Exception as e:
            await self._handle_generic_error(event, e)

    async def _handle_file_validation_error(self, event, error):
        """Обработка ошибок валидации файлов"""
        user_id = self._get_user_id(event)
        chat_id = self._get_chat_id(event)

        log.warning(
            "File validation error",
            error=str(error),
            user_id=user_id,
            chat_id=chat_id,
        )

        await self._send_error_message(event, f"❌ Ошибка файла: {error}")

    async def _handle_cbr_service_error(self, event, error):
        """Обработка ошибок сервиса ЦБ"""
        user_id = self._get_user_id(event)
        chat_id = self._get_chat_id(event)

        log.error(
            "CBR service error",
            error=str(error),
            user_id=user_id,
            chat_id=chat_id,
        )

        await self._send_error_message(event, "❌ Ошибка получения курса валют. Попробуйте позже.")

    async def _handle_yandex_disk_error(self, event, error):
        """Обработка ошибок Яндекс.Диска"""
        user_id = self._get_user_id(event)
        chat_id = self._get_chat_id(event)

        log.error(
            "Yandex.Disk error",
            error=str(error),
            user_id=user_id,
            chat_id=chat_id,
        )

        await self._send_error_message(event, "❌ Ошибка работы с Яндекс.Диском. Попробуйте позже.")

    async def _handle_ocr_error(self, event, error):
        """Обработка ошибок OCR"""
        user_id = self._get_user_id(event)
        chat_id = self._get_chat_id(event)

        log.error(
            "OCR processing error",
            error=str(error),
            user_id=user_id,
            chat_id=chat_id,
        )

        await self._send_error_message(event, "❌ Ошибка обработки документа. Попробуйте другой файл.")

    async def _handle_user_not_allowed_error(self, event, error):
        """Обработка ошибок доступа пользователя"""
        user_id = self._get_user_id(event)
        chat_id = self._get_chat_id(event)

        log.warning(
            "User not allowed",
            user_id=user_id,
            chat_id=chat_id,
        )

        await self._send_error_message(event, "❌ У вас нет доступа к этому боту.")

    async def _handle_rate_not_found_error(self, event, error):
        """Обработка ошибок отсутствия курса"""
        user_id = self._get_user_id(event)
        chat_id = self._get_chat_id(event)

        log.info(
            "Rate not found",
            error=str(error),
            user_id=user_id,
            chat_id=chat_id,
        )

        await self._send_error_message(event, "❌ Курс валюты не найден. Попробуйте позже.")

    async def _handle_calculation_error(self, event, error):
        """Обработка ошибок расчетов"""
        user_id = self._get_user_id(event)
        chat_id = self._get_chat_id(event)

        log.error(
            "Calculation error",
            error=str(error),
            user_id=user_id,
            chat_id=chat_id,
        )

        await self._send_error_message(event, "❌ Ошибка в расчетах. Проверьте введенные данные.")

    async def _handle_generic_error(self, event, error):
        """Обработка общих ошибок"""
        user_id = self._get_user_id(event)
        chat_id = self._get_chat_id(event)

        log.error(
            "Unexpected error in handler",
            error=str(error),
            error_type=type(error).__name__,
            user_id=user_id,
            chat_id=chat_id,
        )

        await self._send_error_message(event, "❌ Произошла внутренняя ошибка. Обратитесь к администратору.")

    def _get_user_id(self, event):
        """Безопасное получение user_id"""
        if hasattr(event, "from_user") and event.from_user:
            return getattr(event.from_user, "id", "unknown")
        return "unknown"

    def _get_chat_id(self, event):
        """Безопасное получение chat_id"""
        if hasattr(event, "chat") and event.chat:
            return getattr(event.chat, "id", "unknown")
        elif hasattr(event, "message") and event.message and hasattr(event.message, "chat"):
            return getattr(event.message.chat, "id", "unknown")
        return "unknown"

    async def _send_error_message(self, event, message):
        """Безопасная отправка сообщения об ошибке"""
        try:
            if isinstance(event, Message):
                await event.answer(message)
            elif isinstance(event, CallbackQuery):
                await event.message.answer(message)
        except Exception:
            pass  # Не можем отправить сообщение об ошибке
