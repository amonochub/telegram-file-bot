"""
Обработчик для получения курсов ЦБ.

Предоставляет простой интерфейс для получения курсов на сегодня/завтра
с использованием новой надёжной системы.
"""

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
            f"💱 <b>Курс ЦБ на {day_text}</b>\n\n"
            "📋 <b>Выберите валюту:</b>",
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


@router.message(F.text.regexp(r"^(курс|курсы|цб|cbr)$", flags="i"))
async def quick_rate_request(msg: Message, state: FSMContext):
    """Быстрый запрос курса по ключевым словам"""
    await rates_menu_start(msg, state) 