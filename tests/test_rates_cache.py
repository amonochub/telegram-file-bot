import datetime as dt
import decimal
from aioresponses import aioresponses
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from app.services.rates_cache import (
    get_rate, 
    CBR_URL,
    has_rate,
    add_subscriber,
    remove_subscriber,
    get_subscribers,
    is_subscriber,
    toggle_subscription
)


class _FakeRedis:  # минимальный мок Redis
    def __init__(self):
        self._store: dict[str, bytes] = {}

    async def get(self, key):  # noqa: D401
        return self._store.get(key)

    async def set(self, key, val, ex=None):  # noqa: D401
        if isinstance(val, str):
            val = val.encode()
        self._store[key] = val


@pytest.mark.asyncio
async def test_rate_cached(monkeypatch):
    fake_redis = _FakeRedis()

    async def fake_from_url(url, **kwargs):  # noqa: D401
        return fake_redis

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

    date = dt.date(2025, 1, 1)
    xml = """<?xml version=\"1.0\" encoding=\"windows-1251\"?>
    <ValCurs Date=\"01.01.2025\" name=\"Foreign Currency Market\">
      <Valute ID=\"R01235\">
        <NumCode>840</NumCode><CharCode>USD</CharCode><Nominal>1</Nominal><Name>US Dollar</Name><Value>90,00</Value>
      </Valute>
    </ValCurs>"""

    with aioresponses() as m:
        m.get(CBR_URL.format(for_date=date), body=xml)
        # первый вызов – обращение к сети
        rate1 = await get_rate(date, "USD")
        assert rate1 == decimal.Decimal("90.00")
        # второй вызов – кэш
        rate2 = await get_rate(date, "USD")
        assert rate2 == rate1
        # в aioresponses зарегистрирован только один запрос
        assert len(m.requests) == 1


class TestDateValidation:
    """Тесты валидации дат в rates_cache"""
    
    @pytest.mark.asyncio
    async def test_has_rate_date_mismatch_future(self):
        """Тест: has_rate возвращает False если запрашиваем будущую дату, а получаем прошлую"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis, \
             patch('app.services.rates_cache._fetch_rates_from_api') as mock_fetch:
            
            # Мокаем Redis - нет данных в кэше
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis
            
            # Мокаем API - возвращаем данные за сегодня, а запрашиваем завтра
            today = dt.date.today()
            tomorrow = today + dt.timedelta(days=1)
            mock_fetch.return_value = ({"USD": 100.0}, today)  # API вернул сегодняшние данные
            
            result = await has_rate(tomorrow)
            
            assert result is False
            mock_fetch.assert_called_once_with(tomorrow)
    
    @pytest.mark.asyncio
    async def test_has_rate_date_mismatch_old(self):
        """Тест: has_rate возвращает False если получаем старые данные"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis, \
             patch('app.services.rates_cache._fetch_rates_from_api') as mock_fetch:
            
            # Мокаем Redis - нет данных в кэше
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis
            
            # Мокаем API - возвращаем данные за вчера, а запрашиваем сегодня
            today = dt.date.today()
            yesterday = today - dt.timedelta(days=1)
            mock_fetch.return_value = ({"USD": 100.0}, yesterday)  # API вернул вчерашние данные
            
            result = await has_rate(today)
            
            assert result is False
            mock_fetch.assert_called_once_with(today)
    
    @pytest.mark.asyncio
    async def test_has_rate_date_match(self):
        """Тест: has_rate возвращает True если даты совпадают"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis, \
             patch('app.services.rates_cache._fetch_rates_from_api') as mock_fetch:
            
            # Мокаем Redis - нет данных в кэше
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis
            
            # Мокаем API - возвращаем данные за запрашиваемую дату
            today = dt.date.today()
            mock_fetch.return_value = ({"USD": 100.0}, today)  # API вернул данные за сегодня
            
            result = await has_rate(today)
            
            assert result is True
            mock_fetch.assert_called_once_with(today)
    
    @pytest.mark.asyncio
    async def test_get_rate_date_mismatch_future(self):
        """Тест: get_rate возвращает None если запрашиваем будущую дату, а получаем прошлую"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis:
            
            # Мокаем Redis - нет данных в кэше
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis
            
            # Запрашиваем завтрашний курс с cache_only=True
            today = dt.date.today()
            tomorrow = today + dt.timedelta(days=1)
            
            result = await get_rate(tomorrow, "USD", cache_only=True)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_rate_date_match(self):
        """Тест: get_rate возвращает курс если даты совпадают"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis:
            
            # Мокаем Redis - есть данные в кэше
            mock_redis = AsyncMock()
            cached_data = '{"USD": 100.0}'
            mock_redis.get.return_value = cached_data.encode()
            mock_get_redis.return_value = mock_redis
            
            # Запрашиваем сегодняшний курс
            today = dt.date.today()
            
            result = await get_rate(today, "USD", cache_only=True)
            
            assert result == Decimal("100.0")


class TestSubscriberManagement:
    """Тесты управления подписчиками"""
    
    @pytest.mark.asyncio
    async def test_add_subscriber_success(self):
        """Тест успешного добавления подписчика"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.sadd.return_value = 1  # Добавлен новый элемент
            mock_get_redis.return_value = mock_redis
            
            result = await add_subscriber(123)
            
            assert result is True
            mock_redis.sadd.assert_called_once_with("cbr_subscribers", 123)
    
    @pytest.mark.asyncio
    async def test_add_subscriber_already_exists(self):
        """Тест добавления уже существующего подписчика"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.sadd.return_value = 0  # Элемент уже существует
            mock_get_redis.return_value = mock_redis
            
            result = await add_subscriber(123)
            
            assert result is True  # Операция считается успешной
            mock_redis.sadd.assert_called_once_with("cbr_subscribers", 123)
    
    @pytest.mark.asyncio
    async def test_remove_subscriber_success(self):
        """Тест успешного удаления подписчика"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.srem.return_value = 1  # Удалён элемент
            mock_get_redis.return_value = mock_redis
            
            result = await remove_subscriber(123)
            
            assert result is True
            mock_redis.srem.assert_called_once_with("cbr_subscribers", 123)
    
    @pytest.mark.asyncio
    async def test_get_subscribers_success(self):
        """Тест получения списка подписчиков"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.smembers.return_value = {b"123", b"456"}  # Redis возвращает bytes
            mock_get_redis.return_value = mock_redis
            
            result = await get_subscribers()
            
            assert result == [123, 456]
            mock_redis.smembers.assert_called_once_with("cbr_subscribers")
    
    @pytest.mark.asyncio
    async def test_is_subscriber_true(self):
        """Тест проверки подписки - пользователь подписан"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.sismember.return_value = True
            mock_get_redis.return_value = mock_redis
            
            result = await is_subscriber(123)
            
            assert result is True
            mock_redis.sismember.assert_called_once_with("cbr_subscribers", 123)
    
    @pytest.mark.asyncio
    async def test_is_subscriber_false(self):
        """Тест проверки подписки - пользователь не подписан"""
        with patch('app.services.rates_cache._get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.sismember.return_value = False
            mock_get_redis.return_value = mock_redis
            
            result = await is_subscriber(123)
            
            assert result is False
            mock_redis.sismember.assert_called_once_with("cbr_subscribers", 123)
    
    @pytest.mark.asyncio
    async def test_toggle_subscription_subscribe(self):
        """Тест переключения подписки - подписка"""
        with patch('app.services.rates_cache.is_subscriber') as mock_is_sub, \
             patch('app.services.rates_cache.add_subscriber') as mock_add:
            
            mock_is_sub.return_value = False  # Пользователь не подписан
            mock_add.return_value = True  # Добавление успешно
            
            result = await toggle_subscription(123)
            
            assert result["subscribed"] is True
            assert result["action"] == "subscribed"
            mock_is_sub.assert_called_once_with(123)
            mock_add.assert_called_once_with(123)
    
    @pytest.mark.asyncio
    async def test_toggle_subscription_unsubscribe(self):
        """Тест переключения подписки - отписка"""
        with patch('app.services.rates_cache.is_subscriber') as mock_is_sub, \
             patch('app.services.rates_cache.remove_subscriber') as mock_remove:
            
            mock_is_sub.return_value = True  # Пользователь подписан
            mock_remove.return_value = True  # Удаление успешно
            
            result = await toggle_subscription(123)
            
            assert result["subscribed"] is False
            assert result["action"] == "unsubscribed"
            mock_is_sub.assert_called_once_with(123)
            mock_remove.assert_called_once_with(123) 