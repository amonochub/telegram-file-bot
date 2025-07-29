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


# --- Кэшированные курсы ЦБ ---
from app.services.rates_cache import get_rate as cached_cbr_rate


async def fetch_cbr_rate(currency: str, for_date: dt.date) -> decimal.Decimal | None:  # noqa: D401
    """Legacy-обёртка для тестов – фактически вызывает кэш.

    TODO: удалить после обновления тестов.
    """
    return await cached_cbr_rate(for_date, currency, requested_tomorrow=False)


async def safe_fetch_rate(currency: str, date: dt.date, requested_tomorrow: bool = False) -> decimal.Decimal | None:
    import aiohttp

    try:
        rate = await cached_cbr_rate(date, currency, requested_tomorrow=requested_tomorrow)
        if rate is None:
            log.warning("cbr_rate_not_found", currency=currency, date=str(date))
        return rate
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        log.error("cbr_fetch_failed", currency=currency, date=str(date), error=str(e))
        return None


def result_message(currency, rate, amount, commission_pct):
    rub_sum = (amount * rate).quantize(decimal.Decimal("0.01"))
    fee = (rub_sum * commission_pct / 100).quantize(decimal.Decimal("0.01"))
    total = (rub_sum + fee).quantize(decimal.Decimal("0.01"))
    return (
        f"Сумма в валюте: {amount} {currency}\n"
        f"Курс ЦБ: {rate} ₽ за {currency}\n"
        f"Сумма в рублях: {rub_sum} ₽\n"
        f"Вознаграждение агента: {fee} ₽\n"
        f"💵 Общая сумма в рублях: {total} ₽"
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
        ]
    ]
)


@router.message(F.text == "💰 Расчёт для клиента")
async def calc_menu_start(msg: Message, state: FSMContext):
    await state.set_state(CalcStates.choosing_day)
    await state.update_data(data=CalcData().__dict__)
    await msg.answer(
        "За какой день рассчитать оплату?\n\n👈 Выберите одну из кнопок ниже.",
        reply_markup=day_kb,
    )

# ----- Обработка дня -----


@router.callback_query(F.data.startswith("calc_"))
async def process_day(cb: CallbackQuery, state: FSMContext):
    pick = cb.data.split("_")[1]  # today / tomorrow
    data = (await state.get_data()) or {}
    data["for_tomorrow"] = pick == "tomorrow"
    await state.update_data(**data)
    await state.set_state(CalcStates.entering_amount)
    await cb.message.edit_text("Введите сумму в валюте (например 1000)")
    await cb.answer()


@router.callback_query(F.data.startswith("cur_"))
async def process_currency(cb: CallbackQuery, state: FSMContext):
    currency = cb.data.split("_")[1]
    
    # Проверяем поддерживаемые валюты
    supported_currencies = {"USD", "EUR", "CNY", "AED", "TRY"}
    if currency not in supported_currencies:
        await cb.answer(
            f"Курс {currency} не поддерживается ЦБ РФ 🙈\nВыберите другую валюту.",
            show_alert=True
        )
        return
    
    data = await state.get_data()
    data["currency"] = currency
    await state.update_data(**data)
    await state.set_state(CalcStates.entering_commission)
    await cb.message.edit_text(
        "Укажите размер вознаграждения агента в процентах (например 3.5)"
    )
    await cb.answer()


@router.message(CalcStates.entering_amount)
async def input_amount(msg: Message, state: FSMContext):
    try:
        amount = decimal.Decimal(msg.text.replace(",", "."))
        assert amount > 0
    except Exception:
        return await msg.reply("Введите положительное число. Попробуйте ещё раз 😊")
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
        return await msg.reply("Число должно быть ≥ 0. Попробуйте ещё раз.")
    data = await state.get_data()
    data["commission"] = pct
    await state.update_data(**data)

    if data.get("for_tomorrow"):
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        log.info("calc_tomorrow_request", tomorrow=str(tomorrow), currency=data["currency"])
        
        # Сначала пробуем получить завтрашний курс
        rate = await safe_fetch_rate(data["currency"], tomorrow, requested_tomorrow=True)
        if rate:
            log.info("calc_tomorrow_rate_found", rate=str(rate), currency=data["currency"])
            await msg.answer(
                result_message(data["currency"], rate, data["amount"], pct),
                reply_markup=main_menu(),
            )
            return await state.clear()
        
        # Если завтрашний курс недоступен, сообщаем об этом
        log.info("calc_tomorrow_rate_not_found", currency=data["currency"])
        await msg.answer(
            "Курс ЦБ на завтра пока не опубликован 🙈\n"
            "Я пришлю расчёт сразу, как только он появится!",
            reply_markup=main_menu(),
        )
        await state.set_state(CalcStates.waiting_tomorrow_rate)
        celery_app.send_task(
            "calc_tasks.wait_rate_and_notify",
            kwargs={
                "chat_id": msg.chat.id,
                "currency": data["currency"],
                "amount": str(data["amount"]),
                "commission": str(pct),
            },
        )
        return

    # Расчет для сегодня
    today = dt.date.today()
    rate = await safe_fetch_rate(data["currency"], today)
    if rate is None:
        # Если курс на сегодня недоступен, пробуем вчерашний
        yesterday = today - dt.timedelta(days=1)
        rate = await safe_fetch_rate(data["currency"], yesterday)
        if rate is None:
            await msg.answer("Курс пока не доступен. Попробуйте позже.")
            return await state.clear()
        await msg.answer("⚠️ Используется курс за последний рабочий день.")
    
    await msg.answer(
        result_message(data["currency"], rate, data["amount"], pct),
        reply_markup=main_menu(),
    )
    await state.clear()


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


@celery_app.task(name="calc_tasks.wait_rate_and_notify", bind=True, max_retries=None)
def wait_rate_and_notify(
    self, chat_id: int, currency: str, amount: str, commission: str
):
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
