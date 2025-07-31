"""
Обработчик для получения курсов ЦБ.

Предоставляет простой интерфейс для получения курсов на сегодня/завтра
с использованием новой надёжной системы.
"""

import re
import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.filters import Command

from app.keyboards.menu import main_menu
from app.services.cbr_rate_service import get_cbr_service

log = structlog.get_logger(__name__)

router = Router()


class RateStates(StatesGroup):
    choosing_day = State()
    choosing_currency = State()


# ----- Клавиатуры -----

day_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📅 Сегодня", callback_data="rate_today")],
        [InlineKeyboardButton(text="📅 Завтра", callback_data="rate_tomorrow")],
    ]
)

currency_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇸 USD", callback_data="rate_USD"),
            InlineKeyboardButton(text="🇪🇺 EUR", callback_data="rate_EUR"),
        ],
        [
            InlineKeyboardButton(text="🇨🇳 CNY", callback_data="rate_CNY"),
            InlineKeyboardButton(text="🇦🇪 AED", callback_data="rate_AED"),
        ],
        [
            InlineKeyboardButton(text="🇹🇷 TRY", callback_data="rate_TRY"),
        ],
    ]
)


@router.message(F.text == "💱 Курсы ЦБ")
async def rates_menu_start(msg: Message, state: FSMContext):
    """Начало работы с курсами ЦБ"""
    await state.set_state(RateStates.choosing_day)
    await msg.answer(
        "💱 <b>Курсы ЦБ РФ</b>\n\n"
        "📋 <b>Выберите день:</b>\n"
        "• <b>Сегодня</b> - актуальный курс на сегодня\n"
        "• <b>Завтра</b> - курс на завтра (если доступен)\n\n"
        "🔔 <b>Если курс на завтра недоступен, я пришлю уведомление, когда он появится!</b>",
        parse_mode="HTML",
        reply_markup=day_kb,
    )


@router.callback_query(F.data.startswith("rate_"))
async def process_rate_request(cb: CallbackQuery, state: FSMContext):
    """Обработка выбора дня или валюты"""
    data_parts = cb.data.split("_")

    if len(data_parts) == 2:
        # Выбор дня
        day_type = data_parts[1]  # today или tomorrow

        await state.update_data(day_type=day_type)
        await state.set_state(RateStates.choosing_currency)

        day_text = "завтра" if day_type == "tomorrow" else "сегодня"
        await cb.message.edit_text(
            f"💱 <b>Курс ЦБ на {day_text}</b>\n\n" "📋 <b>Выберите валюту:</b>",
            parse_mode="HTML",
            reply_markup=currency_kb,
        )

    elif len(data_parts) == 2 and data_parts[1] in ["USD", "EUR", "CNY", "AED", "TRY"]:
        # Выбор валюты
        currency = data_parts[1]
        state_data = await state.get_data()
        day_type = state_data.get("day_type", "today")

        # Получаем сервис курсов ЦБ
        cbr_service = await get_cbr_service(cb.bot)

        if day_type == "tomorrow":
            # Обработка завтрашнего курса
            result = await cbr_service.process_tomorrow_rate(cb.from_user.id, currency)
        else:
            # Обработка сегодняшнего курса
            result = await cbr_service.process_today_rate(cb.from_user.id, currency)

        # Отправляем результат
        await cb.message.edit_text(
            result["message"],
            parse_mode="HTML",
            reply_markup=main_menu(),
        )

        # Очищаем состояние
        await state.clear()

    await cb.answer()


@router.message(F.text.regexp(r"^(USD|EUR|CNY|AED|TRY)$"))
async def direct_currency_input(msg: Message, state: FSMContext):
    """Прямой ввод валюты (если пользователь ввёл код валюты)"""
    currency = msg.text.upper()

    # Проверяем, что мы в процессе выбора валюты
    current_state = await state.get_state()
    if current_state != RateStates.choosing_currency.state:
        return

    state_data = await state.get_data()
    day_type = state_data.get("day_type", "today")

    # Получаем сервис курсов ЦБ
    cbr_service = await get_cbr_service(msg.bot)

    if day_type == "tomorrow":
        # Обработка завтрашнего курса
        result = await cbr_service.process_tomorrow_rate(msg.from_user.id, currency)
    else:
        # Обработка сегодняшнего курса
        result = await cbr_service.process_today_rate(msg.from_user.id, currency)

    # Отправляем результат
    await msg.answer(
        result["message"],
        parse_mode="HTML",
        reply_markup=main_menu(),
    )

    # Очищаем состояние
    await state.clear()


@router.message(F.text.regexp(r"^(курс|курсы|цб|cbr)$", flags=re.IGNORECASE))
async def quick_rate_request(msg: Message, state: FSMContext):
    """Быстрый запрос курса по ключевым словам"""
    await rates_menu_start(msg, state)


@router.message(Command("cbr_subscribe"))
async def cmd_cbr_subscribe(message: Message) -> None:
    """
    Обработчик команды /cbr_subscribe - переключает подписку на курсы ЦБ
    """
    try:
        user_id = message.from_user.id

        # Переключаем подписку
        cbr_service = await get_cbr_service(message.bot)
        result = await cbr_service.toggle_subscription(user_id)

        # Отправляем результат пользователю
        await message.answer(result["message"], parse_mode="HTML", reply_markup=main_menu())

        log.info("cbr_subscription_toggled", user_id=user_id, action=result["action"], subscribed=result["subscribed"])

    except Exception as e:
        log.error("cbr_subscribe_error", user_id=message.from_user.id, error=str(e))
        await message.answer(
            "❌ <b>Произошла ошибка при изменении подписки.</b>\n\n"
            "🔄 <b>Попробуйте позже или обратитесь к администратору.</b>",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )


@router.callback_query(F.data == "cbr_subscribe")
async def cbr_subscribe_callback(callback: CallbackQuery) -> None:
    """
    Обработчик callback для подписки на курсы ЦБ
    """
    try:
        user_id = callback.from_user.id

        # Переключаем подписку
        cbr_service = await get_cbr_service(callback.bot)
        result = await cbr_service.toggle_subscription(user_id)

        # Отправляем результат пользователю
        await callback.message.edit_text(result["message"], parse_mode="HTML")

        log.info(
            "cbr_subscription_toggled_callback",
            user_id=user_id,
            action=result["action"],
            subscribed=result["subscribed"],
        )

    except Exception as e:
        log.error("cbr_subscribe_callback_error", user_id=callback.from_user.id, error=str(e))
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка при изменении подписки.</b>\n\n"
            "🔄 <b>Попробуйте позже или обратитесь к администратору.</b>",
            parse_mode="HTML",
        )
    finally:
        await callback.answer()


@router.message(Command("cbr_status"))
async def cmd_cbr_status(message: Message) -> None:
    """
    Обработчик команды /cbr_status - показывает статус подписки
    """
    try:
        user_id = message.from_user.id

        # Проверяем статус подписки
        cbr_service = await get_cbr_service(message.bot)
        is_subscribed = await cbr_service.is_subscriber(user_id)

        if is_subscribed:
            status_message = (
                "✅ <b>Вы подписаны на уведомления о курсах ЦБ</b>\n\n"
                "📅 <b>Вы будете получать уведомления о появлении новых курсов.</b>\n\n"
                "🔔 <b>Для отписки используйте команду /cbr_subscribe</b>"
            )
        else:
            status_message = (
                "❌ <b>Вы не подписаны на уведомления о курсах ЦБ</b>\n\n"
                "📅 <b>Для подписки используйте команду /cbr_subscribe</b>\n\n"
                "🔔 <b>После подписки вы будете получать уведомления о появлении новых курсов.</b>"
            )

        await message.answer(status_message, parse_mode="HTML", reply_markup=main_menu())

        log.info("cbr_status_checked", user_id=user_id, is_subscribed=is_subscribed)

    except Exception as e:
        log.error("cbr_status_error", user_id=message.from_user.id, error=str(e))
        await message.answer(
            "❌ <b>Произошла ошибка при проверке статуса подписки.</b>\n\n"
            "🔄 <b>Попробуйте позже или обратитесь к администратору.</b>",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
