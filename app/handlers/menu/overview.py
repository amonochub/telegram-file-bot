"""
Обработчики для обзора папок
"""

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.constants.messages import OVERVIEW_MENU_TEXT, LOG_BROWSE_MENU_TRIGGERED
from app.keyboards.menu import main_menu
from app.utils.logging_context import log_handler_call, log_handler_error
from app.utils.navigation import navigate_to_menu

router = Router()
log = structlog.get_logger()


@router.message(F.text == OVERVIEW_MENU_TEXT)
async def browse_menu(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки "📂 Обзор папок"

    Args:
        message: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    try:
        # Логируем вызов с контекстом
        log_handler_call("browse_menu", message, menu_text=message.text)

        # Сохраняем в историю навигации
        await navigate_to_menu(state, "overview", action="browse_folders")

        # Очищаем состояние FSM
        await state.clear()

        # Вызываем основной обработчик
        from ..browse import files_command

        await files_command(message)

    except Exception as e:
        # Логируем ошибку с контекстом
        log_handler_error("browse_menu", message, e)

        # Отправляем пользователю понятное сообщение
        try:
            await message.answer(
                "❌ Произошла ошибка при открытии обзора папок. Попробуйте позже.", reply_markup=main_menu()
            )
        except Exception as send_error:
            # Логируем ошибку отправки сообщения
            log_handler_error("browse_menu_send_error", message, send_error)
