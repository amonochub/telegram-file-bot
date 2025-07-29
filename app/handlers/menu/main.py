"""
Обработчики для главного меню и неизвестных команд
"""
import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.constants.messages import (
    MAIN_MENU_TEXT, 
    MAIN_MENU_WELCOME,
    UNKNOWN_COMMAND_TEXT,
    LOG_MAIN_MENU_BUTTON_TRIGGERED,
    LOG_UNHANDLED_MESSAGE
)
from app.keyboards.menu import main_menu

router = Router()
log = structlog.get_logger()


@router.message(F.text == MAIN_MENU_TEXT)
async def main_menu_button(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки "🏠 Главное меню"
    Возвращает пользователя в главное меню
    
    Args:
        message: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    log.info(LOG_MAIN_MENU_BUTTON_TRIGGERED, text=message.text, user_id=message.from_user.id)
    await state.clear()
    
    from ..start import cmd_start
    await cmd_start(message, state)


