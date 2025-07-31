"""
Обработчики для курсов Центрального Банка
"""

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import settings
from app.constants.messages import (
    CBR_RATES_MENU_TEXT,
    LOG_CBR_RATES_MENU_TRIGGERED,
)
from app.keyboards.menu import main_menu
from app.services.cbr_rate_service import get_cbr_service

router = Router()
log = structlog.get_logger()


@router.message(F.text == CBR_RATES_MENU_TEXT)
async def cbr_rates_menu(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки "📈 Курсы ЦБ"
    Показывает меню для получения курсов на сегодня/завтра

    Args:
        message: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    log.info(LOG_CBR_RATES_MENU_TRIGGERED, text=message.text, user_id=message.from_user.id)
    await state.clear()

    try:
        # Перенаправляем на новый обработчик курсов ЦБ
        from app.handlers.cbr_rates import rates_menu_start

        await rates_menu_start(message, state)

    except Exception as e:
        log.error("cbr_rates_menu_error", user_id=message.from_user.id, error=str(e))
        await message.answer(
            "❌ Произошла ошибка при работе с курсами ЦБ.\n" "Попробуйте позже или обратитесь к администратору.",
            reply_markup=main_menu(),
        )
