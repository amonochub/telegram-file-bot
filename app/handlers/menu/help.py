"""
Обработчики для справки и помощи
"""

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.constants.messages import HELP_MENU_TEXT, HELP_TEXT, LOG_HELP_BUTTON_TRIGGERED
from app.keyboards.menu import main_menu

router = Router()
log = structlog.get_logger()


@router.message(F.text == HELP_MENU_TEXT)
async def help_button(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки "ℹ️ Помощь"

    Args:
        message: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    log.info(LOG_HELP_BUTTON_TRIGGERED, text=message.text, user_id=message.from_user.id)
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=main_menu())
