"""Кэширование курсов ЦБ в Redis.

Формат ключа: ``cbr:<ISO-date>``
Значение: JSON-словарь {"USD": 90.12, ...}
"""

from __future__ import annotations

import datetime as dt
import decimal
import json
import xml.etree.ElementTree as ET
from typing import Final, Optional, List, Dict, Any

import aiohttp
import asyncio
import redis.asyncio as aioredis
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

CBR_URL: Final[str] = "https://www.cbr.ru/scripts/XML_daily.asp?date_req={for_date}"
ISO2CBR: Final[dict[str, str]] = {"USD": "R01235", "EUR": "R01239", "CNY": "R01375", "AED": "R01230", "TRY": "R01700J"}
TTL: Final[int] = 60 * 60 * 12  # 12 часов

# Коэффициент для пересчета официального курса в курс покупки
# Курс покупки обычно выше официального курса (банк платит больше за валюту)
BUY_RATE_COEFFICIENT: Final[float] = 1.0  # используем официальный курс без наценки


async def _get_redis():
    """Ленивая инициализация Redis-клиента."""
    if not hasattr(_get_redis, "_redis"):
        _get_redis._redis = aioredis.from_url(settings.redis_url)  # type: ignore[attr-defined]
    return _get_redis._redis  # type: ignore[attr-defined]


async def has_rate(date: dt.date) -> bool:
    """
    Проверяет, есть ли данные на указанную дату.
    
    Args:
        date: Дата для проверки
        
    Returns:
        True если данные есть, False если нет
    """
    try:
        redis_client = await _get_redis()
        key = f"cbr:{date.isoformat()}"
        
        # Проверяем кэш
        cached_data = await redis_client.get(key)
        if cached_data:
            if isinstance(cached_data, bytes):
                cached_data = cached_data.decode()
            rates = json.loads(cached_data)
            if rates and len(rates) > 0:
                log.info("cbr_rate_exists_in_cache", date=str(date), currencies=list(rates.keys()))
                return True
        
        # Если в кэше нет, пробуем запросить из API
        rates, real_date = await _fetch_rates_from_api(date)
        if rates and len(rates) > 0:
            # Сохраняем в кэш
            await redis_client.set(key, json.dumps(rates, ensure_ascii=False), ex=TTL)
            log.info("cbr_rate_exists_in_api", date=str(date), real_date=str(real_date), currencies=list(rates.keys()))
            return True
        
        log.info("cbr_rate_not_exists", date=str(date))
        return False
        
    except Exception as e:
        log.error("cbr_has_rate_error", date=str(date), error=str(e))
        return False


async def _fetch_rates_from_api(date: dt.date) -> tuple[dict[str, float], dt.date]:
    """
    Запрашивает курсы валют с сайта ЦБ для указанной даты.
    
    Args:
        date: Дата для запроса
        
    Returns:
        Кортеж (словарь курсов, реальная дата из ответа)
    """
    # Для выходных дней запрашиваем последний рабочий день
    weekday = date.weekday()  # 0=понедельник, 6=воскресенье
    if weekday >= 5:  # суббота или воскресенье
        days_to_subtract = weekday - 4  # 5->1, 6->2
        actual_date = date - dt.timedelta(days=days_to_subtract)
        log.info("cbr_weekend_adjustment", original_date=str(date), adjusted_date=str(actual_date), weekday=weekday)
    else:
        actual_date = date

    # сетевой запрос - используем правильный формат даты DD/MM/YYYY
    date_req = actual_date.strftime("%d/%m/%Y")
    url = CBR_URL.format(for_date=date_req)
    log.info("cbr_request", url=url, requested_date=str(date), actual_date=str(actual_date))
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    log.warning("cbr_http_fail", status=resp.status, url=url)
                    return {}, date
                xml_text = await resp.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        log.error("cbr_http_exc", url=url, error=str(e))
        return {}, date

    rates, real_date = await _parse_rates(xml_text)
    log.info(
        "cbr_parsed_rates", real_date=str(real_date), currencies_found=list(rates.keys())
    )

    return rates, real_date


async def save_pending_calc(user_id: int, date: dt.date, currency: str, amount: decimal.Decimal, commission: decimal.Decimal) -> bool:
    """
    Сохраняет отложенный расчёт в Redis.
    
    Args:
        user_id: ID пользователя
        date: Дата для расчёта
        currency: Валюта
        amount: Сумма
        commission: Комиссия в процентах
        
    Returns:
        True если сохранено успешно, False если ошибка
    """
    try:
        redis_client = await _get_redis()
        key = f"pending_calc:{user_id}:{date.isoformat()}"
        
        data = {
            "user_id": user_id,
            "date": date.isoformat(),
            "currency": currency,
            "amount": str(amount),
            "commission": str(commission),
            "created_at": dt.datetime.now().isoformat()
        }
        
        # Сохраняем с TTL 24 часа
        await redis_client.set(key, json.dumps(data, ensure_ascii=False), ex=60*60*24)
        
        log.info("cbr_pending_calc_saved", user_id=user_id, date=str(date), currency=currency)
        return True
        
    except Exception as e:
        log.error("cbr_save_pending_calc_error", user_id=user_id, date=str(date), error=str(e))
        return False


async def get_all_pending() -> List[Dict[str, Any]]:
    """
    Получает все отложенные расчёты из Redis.
    
    Returns:
        Список отложенных расчётов
    """
    try:
        redis_client = await _get_redis()
        pattern = "pending_calc:*"
        
        # Получаем все ключи отложенных расчётов
        keys = await redis_client.keys(pattern)
        
        pending_calcs = []
        for key in keys:
            try:
                data = await redis_client.get(key)
                if data:
                    calc_data = json.loads(data)
                    pending_calcs.append(calc_data)
            except Exception as e:
                log.error("cbr_get_pending_calc_error", key=key, error=str(e))
        
        log.info("cbr_get_all_pending", count=len(pending_calcs))
        return pending_calcs
        
    except Exception as e:
        log.error("cbr_get_all_pending_error", error=str(e))
        return []


async def remove_pending(user_id: int, date: dt.date) -> bool:
    """
    Удаляет отложенный расчёт из Redis.
    
    Args:
        user_id: ID пользователя
        date: Дата расчёта
        
    Returns:
        True если удалено успешно, False если ошибка
    """
    try:
        redis_client = await _get_redis()
        key = f"pending_calc:{user_id}:{date.isoformat()}"
        
        result = await redis_client.delete(key)
        
        if result > 0:
            log.info("cbr_pending_calc_removed", user_id=user_id, date=str(date))
            return True
        else:
            log.warning("cbr_pending_calc_not_found", user_id=user_id, date=str(date))
            return False
            
    except Exception as e:
        log.error("cbr_remove_pending_error", user_id=user_id, date=str(date), error=str(e))
        return False


async def _parse_rates(xml_text: str) -> tuple[dict[str, float], dt.date]:
    """Разбирает XML-ответ ЦБ в словарь курсов и возвращает реальную дату."""
    tree = ET.fromstring(xml_text)
    result: dict[str, float] = {}

    # Извлекаем реальную дату из XML
    date_str = tree.get("Date", "")
    if date_str:
        try:
            # Парсим дату в формате "26.07.2025"
            day, month, year = date_str.split(".")
            real_date = dt.date(int(year), int(month), int(day))
        except (ValueError, AttributeError):
            real_date = dt.date.today()
    else:
        real_date = dt.date.today()

    log.info("cbr_parsing_xml", date_str=date_str, real_date=str(real_date))

    # Пробуем найти все валюты по кодам
    for iso, cbr_id in ISO2CBR.items():
        valute = tree.find(f".//Valute[@ID='{cbr_id}']")
        if valute is None:
            log.warning("cbr_valute_not_found", iso=iso, cbr_id=cbr_id)
            continue
        try:
            value_elem = valute.find("Value")
            nominal_elem = valute.find("Nominal")
            if value_elem is None or nominal_elem is None:
                log.warning("cbr_missing_elements", iso=iso, cbr_id=cbr_id)
                continue
            value = value_elem.text.replace(",", ".")  # type: ignore[assignment]
            nominal = int(nominal_elem.text)  # type: ignore[arg-type]
            result[iso] = float(decimal.Decimal(value) / nominal)
            log.info("cbr_rate_parsed", iso=iso, rate=result[iso])
        except Exception as e:
            log.error("cbr_parse_error", iso=iso, cbr_id=cbr_id, error=str(e))

    # Если не нашли TRY, пробуем найти по началу кода
    if "TRY" not in result:
        for valute in tree.findall(".//Valute"):
            valute_id = valute.get("ID", "")
            if valute_id.startswith("R01700"):  # TRY может иметь разные суффиксы
                char_code_elem = valute.find("CharCode")
                if char_code_elem is not None and char_code_elem.text == "TRY":
                    try:
                        value_elem = valute.find("Value")
                        nominal_elem = valute.find("Nominal")
                        if value_elem is None or nominal_elem is None:
                            continue
                        value = value_elem.text.replace(",", ".")  # type: ignore[assignment]
                        nominal = int(nominal_elem.text)  # type: ignore[arg-type]
                        result["TRY"] = float(decimal.Decimal(value) / nominal)
                        log.info("cbr_try_found", rate=result["TRY"])
                        break
                    except Exception as e:
                        log.error("cbr_try_parse_error", error=str(e))

    log.info("cbr_parsing_complete", currencies_found=list(result.keys()), total_rates=len(result))
    return result, real_date


async def get_rate(
    date: dt.date,
    currency: str,
    *,
    cache_only: bool = False,
    requested_tomorrow: bool = False,
) -> Optional[decimal.Decimal]:
    """Возвращает курс ``currency`` на ``date``.

    1. Пытается взять из Redis по запрошенной дате.
    2. Если не найден, пробует найти по ближайшим датам (вчера, позавчера).
    3. При промахе и ``cache_only=False`` запрашивает ЦБ, кладёт кэш и возвращает.
    4. Если промах и ``cache_only=True`` – возвращает ``None`` без обращения к сети.
    """
    redis = await _get_redis()

    # Для выходных дней запрашиваем последний рабочий день
    # Если сегодня воскресенье (6) или суббота (5), запрашиваем пятницу
    # НО если запрашиваем завтрашний курс, не применяем weekend-adjustment
    weekday = date.weekday()  # 0=понедельник, 6=воскресенье
    if weekday >= 5 and not requested_tomorrow:  # суббота или воскресенье, но не завтра
        days_to_subtract = weekday - 4  # 5->1, 6->2
        actual_date = date - dt.timedelta(days=days_to_subtract)
        log.info("cbr_weekend_adjustment", original_date=str(date), adjusted_date=str(actual_date), weekday=weekday)
    else:
        actual_date = date

    # Пробуем найти в кэше по запрошенной дате
    key = f"cbr:{actual_date.isoformat()}"
    cached = await redis.get(key)  # type: ignore[misc]
    if cached:
        if isinstance(cached, bytes):
            cached = cached.decode()
        try:
            rates: dict[str, float] = json.loads(cached)
            if currency in rates:
                # Возвращаем официальный курс ЦБ без наценки
                official_rate = decimal.Decimal(str(rates[currency]))
                log.info("cbr_rate_found_cache", currency=currency, official_rate=str(official_rate))
                return official_rate
        except Exception as e:  # noqa: BLE001
            log.warning("cbr_cache_parse_error", error=str(e))

    if cache_only:
        return None

    # сетевой запрос - используем правильный формат даты DD/MM/YYYY
    date_req = actual_date.strftime("%d/%m/%Y")
    url = CBR_URL.format(for_date=date_req)
    log.info("cbr_request", url=url, requested_date=str(date), actual_date=str(actual_date))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    log.warning("cbr_http_fail", status=resp.status, url=url)
                    return None
                xml_text = await resp.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:  # type: ignore[name-defined]
        log.error("cbr_http_exc", url=url, error=str(e))
        return None

    rates, real_date = await _parse_rates(xml_text)
    log.info(
        "cbr_parsed_rates", real_date=str(real_date), currencies_found=list(rates.keys()), requested_currency=currency
    )

    if not rates:
        log.warning("cbr_no_rates_found")
        #  ⬇⬇ Paste fallback cache‑loop here
        for days_back in range(1, 8):  # Пробуем последние 7 дней
            check_date = actual_date - dt.timedelta(days=days_back)
            check_key = f"cbr:{check_date.isoformat()}"
            cached = await redis.get(check_key)  # type: ignore[misc]
            if cached:
                if isinstance(cached, bytes):
                    cached = cached.decode()
                try:
                    rates = json.loads(cached)
                    if currency in rates:
                        # Возвращаем официальный курс ЦБ без наценки
                        official_rate = decimal.Decimal(str(rates[currency]))
                        log.info(
                            "cbr_rate_found_previous_day",
                            requested_date=str(date),
                            found_date=str(check_date),
                            currency=currency,
                            official_rate=str(official_rate),
                        )
                        return official_rate
                except Exception as e:  # noqa: BLE001
                    log.warning("cbr_cache_parse_error", error=str(e))
        return None

    # сохраняем кэш по реальной дате из ЦБ (сохраняем официальные курсы)
    real_key = f"cbr:{real_date.isoformat()}"
    await redis.set(real_key, json.dumps(rates, ensure_ascii=False), ex=TTL)  # type: ignore[misc]
    log.info("cbr_cache_saved", key=real_key, rates_count=len(rates))

    if currency in rates:
        # Возвращаем официальный курс ЦБ без наценки
        official_rate = decimal.Decimal(str(rates[currency]))

        log.info("cbr_rate_found", currency=currency, official_rate=str(official_rate), date=str(real_date))
        return official_rate

    log.warning("cbr_currency_not_found", currency=currency, available_currencies=list(rates.keys()))
    return None
