import asyncio
import datetime as dt
import decimal
import xml.etree.ElementTree as ET
from dataclasses import dataclass

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
from celery import Celery

log = structlog.get_logger(__name__)

# --- Настройки ---
from app.config import settings
from app.keyboards.menu import main_menu

router = Router()

celery_app = Celery("calc_tasks", broker=settings.redis_url, backend=settings.redis_url)

# (legacy constants retained for compatibility purposes)
CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp?date_req={for_date}"


# --- Новый надёжный сервис курсов ЦБ ---
from app.services.cbr_rate_service import get_cbr_service


# --- Legacy функции для обратной совместимости ---
from app.services.rates_cache import get_rate as cached_cbr_rate


async def fetch_cbr_rate(currency: str, for_date: dt.date) -> decimal.Decimal | None:  # noqa: D401
    """Legacy-обёртка для тестов – фактически вызывает кэш.

    TODO: удалить после обновления тестов.
    """
    return await cached_cbr_rate(for_date, currency, requested_tomorrow=False)


async def safe_fetch_rate(currency: str, date: dt.date, requested_tomorrow: bool = False) -> decimal.Decimal | None:
    """Legacy-функция для обратной совместимости"""
    try:
        rate = await cached_cbr_rate(date, currency, requested_tomorrow=requested_tomorrow)
        if rate is None:
            log.warning("cbr_rate_not_found", currency=currency, date=str(date))
        return rate
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        log.error("cbr_fetch_failed", currency=currency, date=str(date), error=str(e))
        return None


def result_message(currency, rate, amount, commission_pct):
    """Формирует сообщение с результатом расчёта"""
    rub_sum = (amount * rate).quantize(decimal.Decimal("0.01"))
    commission_amount = (rub_sum * commission_pct / 100).quantize(decimal.Decimal("0.01"))
    total = rub_sum + commission_amount
    
    return (
        f"💰 <b>Расчёт для клиента</b>\n\n"
        f"💱 <b>Валюта:</b> {currency}\n"
        f"💵 <b>Сумма:</b> {amount} {currency}\n"
        f"📊 <b>Курс ЦБ:</b> {rate:.4f} ₽\n"
        f"💸 <b>Сумма в рублях:</b> {rub_sum} ₽\n"
        f"💼 <b>Комиссия ({commission_pct}%):</b> {commission_amount} ₽\n"
        f"🎯 <b>Итого к оплате:</b> {total} ₽"
    )


class CalcStates(StatesGroup):
    choosing_day = State()
    entering_amount = State()
    choosing_currency = State()
    entering_commission = State()
    waiting_tomorrow_rate = State()


@dataclass
class CalcData:
    for_tomorrow: bool = False
    currency: str | None = None
    amount: decimal.Decimal | None = None
    commission: decimal.Decimal | None = None


# локальное меню не требуется – используем общее `main_menu()`

# ----- Выбор дня оплаты -----

day_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Сегодня", callback_data="calc_today")],
        [InlineKeyboardButton(text="Завтра", callback_data="calc_tomorrow")],
    ]
)

# ----- Выбор валюты -----

currency_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🇪🇺 EUR", callback_data="cur_EUR"),
            InlineKeyboardButton(text="🇺🇸 USD", callback_data="cur_USD"),
            InlineKeyboardButton(text="🇨🇳 CNY", callback_data="cur_CNY"),
            InlineKeyboardButton(text="🇦🇪 AED", callback_data="cur_AED"),
        ],
        [
            InlineKeyboardButton(text="🇹🇷 TRY", callback_data="cur_TRY"),
        ],
    ]
)


@router.message(F.text == "💰 Расчёт для клиента")
async def calc_menu_start(msg: Message, state: FSMContext):
    await state.set_state(CalcStates.choosing_day)
    await msg.answer(
        "💰 <b>Расчёт для клиента</b>\n\n"
        "📋 <b>Как это работает:</b>\n"
        "• Выберите день (сегодня/завтра)\n"
        "• Выберите валюту\n"
        "• Укажите процент комиссии\n"
        "• Получите готовый расчёт!\n\n"
        "👈 Выберите одну из кнопок ниже:",
        parse_mode="HTML",
        reply_markup=day_kb,
    )


# ----- Обработка дня -----


@router.callback_query(F.data.startswith("calc_"))
async def process_day(cb: CallbackQuery, state: FSMContext):
    pick = cb.data.split("_")[1]
    data = await state.get_data()
    data["for_tomorrow"] = pick == "tomorrow"
    await state.update_data(**data)
    await state.set_state(CalcStates.entering_amount)
    await cb.message.edit_text("Введите сумму в валюте (например: 1000)")
    await cb.answer()


@router.callback_query(F.data.startswith("cur_"))
async def process_currency(cb: CallbackQuery, state: FSMContext):
    currency = cb.data.split("_")[1]

    # Проверяем поддерживаемые валюты
    supported_currencies = {"USD", "EUR", "CNY", "AED", "TRY"}
    if currency not in supported_currencies:
        await cb.answer(f"Курс {currency} не поддерживается ЦБ РФ 🙈\nВыберите другую валюту.", show_alert=True)
        return

    data = await state.get_data()
    data["currency"] = currency
    await state.update_data(**data)
    await state.set_state(CalcStates.entering_commission)
    await cb.message.edit_text("Укажите размер вознаграждения агента в процентах (например 3.5)")
    await cb.answer()


@router.message(CalcStates.entering_amount)
async def input_amount(msg: Message, state: FSMContext):
    try:
        amount = decimal.Decimal(msg.text.replace(",", "."))
        assert amount > 0
    except Exception:
        return await msg.reply(
            "❌ <b>Неверный формат числа!</b>\n\n"
            "📝 <b>Правильные примеры:</b>\n"
            "• 1000\n"
            "• 1500.50\n"
            "• 2,500\n\n"
            "💡 <b>Советы:</b>\n"
            "• Используйте точку или запятую для дробной части\n"
            "• Число должно быть больше нуля\n"
            "• Не используйте пробелы или спецсимволы\n\n"
            "Попробуйте ещё раз! 😊",
            parse_mode="HTML"
        )
    data = await state.get_data()
    data["amount"] = amount
    await state.update_data(**data)
    await state.set_state(CalcStates.choosing_currency)
    await msg.answer("Выберите валюту перевода", reply_markup=currency_kb)


@router.message(CalcStates.entering_commission)
async def input_commission(msg: Message, state: FSMContext):
    try:
        pct = decimal.Decimal(msg.text.replace(",", "."))
        assert pct >= 0
    except Exception:
        return await msg.reply(
            "❌ <b>Неверный процент комиссии!</b>\n\n"
            "📝 <b>Правильные примеры:</b>\n"
            "• 3.5 (3.5%)\n"
            "• 2 (2%)\n"
            "• 0 (без комиссии)\n\n"
            "💡 <b>Советы:</b>\n"
            "• Процент должен быть ≥ 0\n"
            "• Используйте точку для дробной части\n"
            "• Обычно комиссия 1-5%\n\n"
            "Попробуйте ещё раз! 😊",
            parse_mode="HTML"
        )
    
    data = await state.get_data()
    data["commission"] = pct
    await state.update_data(**data)

    # Получаем сервис курсов ЦБ
    cbr_service = await get_cbr_service(msg.bot)
    
    if data.get("for_tomorrow"):
        # Обработка завтрашнего курса с новой надёжной системой
        result = await cbr_service.process_tomorrow_rate(msg.chat.id, data["currency"])
        
        await msg.answer(result["message"], parse_mode="HTML", reply_markup=main_menu())
        
        if result["success"]:
            # Курс найден - показываем расчёт
            await msg.answer(
                result_message(data["currency"], result["rate"], data["amount"], pct),
                reply_markup=main_menu(),
            )
        # Если курс не найден, подписка уже запущена в process_tomorrow_rate
        
        return await state.clear()
    
    else:
        # Обработка сегодняшнего курса с новой надёжной системой
        result = await cbr_service.process_today_rate(msg.chat.id, data["currency"])
        
        if result["success"]:
            # Курс найден - показываем расчёт
            await msg.answer(
                result_message(data["currency"], result["rate"], data["amount"], pct),
                reply_markup=main_menu(),
            )
        else:
            # Курс не найден - показываем сообщение об ошибке
            await msg.answer(result["message"], parse_mode="HTML", reply_markup=main_menu())
        
        return await state.clear()


# Fallback для случаев, когда пользователь пропускает шаги
@router.message(F.text.regexp(r"^\d+[\d\s,.]*$"))
async def fallback_amount(msg: Message, state: FSMContext):
    """Обработчик для случаев, когда пользователь вводит сумму без выбора дня"""
    current = await state.get_state()
    if current is not None:  # внутри цепочки – игнорируем
        return

    # Если пользователь ввёл число без контекста, начинаем заново
    await state.set_state(CalcStates.choosing_day)
    await state.update_data(data=CalcData().__dict__)
    await msg.answer(
        "За какой день рассчитать оплату?\n\n👈 Выберите одну из кнопок ниже.",
        reply_markup=day_kb,
    )


# Legacy Celery task - оставляем для обратной совместимости
@celery_app.task(name="calc_tasks.wait_rate_and_notify", bind=True, max_retries=None)
def wait_rate_and_notify(self, chat_id: int, currency: str, amount: str, commission: str):
    """Legacy задача для обратной совместимости"""
    import asyncio

    loop = asyncio.get_event_loop()

    async def _run():
        amt = decimal.Decimal(amount)
        pct = decimal.Decimal(commission)
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        from aiogram import Bot

        bot = Bot(token=settings.bot_token)
        while True:
            rate = await cached_cbr_rate(tomorrow, currency, cache_only=True, requested_tomorrow=True)
            if rate:
                await bot.send_message(
                    chat_id,
                    result_message(currency, rate, amt, pct),
                    reply_markup=main_menu(),
                )
                break
            await asyncio.sleep(300)

    return loop.run_until_complete(_run())
