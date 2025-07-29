"""
Обработчики для расчёта вознаграждения агента
"""

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.constants.messages import CLIENT_CALC_MENU_TEXT, LOG_CLIENT_CALC_MENU_TRIGGERED

router = Router()
log = structlog.get_logger()


@router.message(F.text == CLIENT_CALC_MENU_TEXT)
async def client_calc_menu(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки "💰 Расчёт для клиента"

    Args:
        message: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    log.info(LOG_CLIENT_CALC_MENU_TRIGGERED, text=message.text, user_id=message.from_user.id)
    await state.clear()

    from ..client_calc import calc_menu_start

    await calc_menu_start(message, state)
