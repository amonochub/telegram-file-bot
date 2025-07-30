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
    CBR_SUBSCRIBE_SUCCESS,
    CBR_UNSUBSCRIBE_SUCCESS,
    LOG_CBR_RATES_MENU_TRIGGERED,
)
from app.keyboards.menu import main_menu
from app.services.cbr_notifier import CBRNotificationService

router = Router()
log = structlog.get_logger()


@router.message(F.text == CBR_RATES_MENU_TEXT)
async def cbr_rates_menu(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки "📈 Курсы ЦБ"
    Переключает подписку на уведомления о курсах ЦБ

    Args:
        message: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    log.info(LOG_CBR_RATES_MENU_TRIGGERED, text=message.text, user_id=message.from_user.id)
    await state.clear()

    try:
        service = CBRNotificationService(message.bot, settings.redis_url)
        await service.connect()
        user_id = message.from_user.id

        if user_id in service.subscribers:
            await service.unsubscribe_user(user_id)
            log.info("cbr_user_unsubscribed", user_id=user_id)
            await message.answer(
                "✅ Вы отписались от уведомлений о курсах ЦБ.\nБольше не будете получать уведомления о новых курсах.",
                reply_markup=main_menu(),
            )
        else:
            await service.subscribe_user(user_id)
            log.info("cbr_user_subscribed", user_id=user_id)
            await message.answer(
                "✅ Вы подписались на уведомления о курсах ЦБ!\n\n"
                "Теперь вы будете получать уведомления сразу, как только ЦБ опубликует новые курсы валют.\n"
                "Уведомления приходят обычно после 11:00 по московскому времени.",
                reply_markup=main_menu(),
            )
    except Exception as e:
        log.error("cbr_subscription_error", user_id=message.from_user.id, error=str(e))
        await message.answer(
            "❌ Произошла ошибка при работе с подпиской на курсы ЦБ.\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=main_menu(),
        )
