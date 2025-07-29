import datetime as dt
import decimal
from aioresponses import aioresponses
import pytest
from unittest.mock import patch, AsyncMock

from app.services.rates_cache import get_rate, CBR_URL


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
async def test_rate_cached():
    fake_redis = _FakeRedis()

    # Mock the aioredis module directly
    with patch('app.services.rates_cache.aioredis') as mock_aioredis:
        mock_aioredis.from_url = AsyncMock(return_value=fake_redis)
        
        # Test data
        cache_key = "cbr:2024-12-01"
        cached_rates = '{"USD": 90.50, "EUR": 99.25}'
        
        # Pre-populate cache
        await fake_redis.set(cache_key, cached_rates.encode())
        
        # Test retrieval
        with aioresponses() as m:
            # Shouldn't make HTTP request since cached
            rate = await get_rate(dt.date(2024, 12, 1), "USD")
            
            # Verify we got cached data
            assert rate == decimal.Decimal("90.50")
            
            # Verify no HTTP requests were made
            assert len(m.requests) == 0

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