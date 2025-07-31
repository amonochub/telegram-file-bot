import json

# mypy: disallow-untyped-defs

from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as aioredis


class AutocompleteService:
    """Сервис умного автодополнения для валютных операций"""

    def __init__(self, redis_url: str) -> None:
        self.redis_url: str = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Устанавливает соединение с Redis."""
        self.redis = aioredis.from_url(self.redis_url)

    async def remember_company(self, company_name: str, user_id: int) -> None:
        if self.redis is None:
            await self.connect()
        assert self.redis is not None

        key = f"company_usage:{company_name.lower()}"
        await self.redis.zincrby("companies_frequency", 1, company_name)
        user_key = f"user_companies:{user_id}"
        await self.redis.zadd(user_key, {company_name: datetime.now().timestamp()})
        await self.redis.expire(user_key, 86400 * 90)

    async def get_company_suggestions(self, partial: str, user_id: int, limit: int = 10) -> List[str]:
        if self.redis is None:
            await self.connect()
        assert self.redis is not None

        partial_lower = partial.lower()
        user_key = f"user_companies:{user_id}"
        user_companies = await self.redis.zrevrange(user_key, 0, -1)  # type: ignore[misc]
        all_companies = await self.redis.zrevrange("companies_frequency", 0, 100)  # type: ignore[misc]
        suggestions = []
        for company in user_companies:
            if isinstance(company, bytes):
                company = company.decode("utf-8")
            if partial_lower in company.lower():
                suggestions.append(company)
        for company in all_companies:
            if isinstance(company, bytes):
                company = company.decode("utf-8")
            if partial_lower in company.lower() and company not in suggestions:
                suggestions.append(company)
        return suggestions[:limit]

    async def get_next_document_number(self, company1: str, company2: str, doctype: str) -> str:
        if self.redis is None:
            await self.connect()
        assert self.redis is not None

        key = f"doc_numbers:{company1.lower()}:{company2.lower()}:{doctype.lower()}"
        last_number = await self.redis.get(key)  # type: ignore[misc]
        if last_number:
            next_number = str(int(last_number) + 1)
        else:
            next_number = "1"
        await self.redis.set(key, next_number)  # type: ignore[misc]
        return next_number

    async def get_recent_counterparties(self, user_id: int, limit: int = 10) -> List[Dict]:
        if self.redis is None:
            await self.connect()
        assert self.redis is not None

        key = f"recent_counterparties:{user_id}"
        recent = await self.redis.lrange(key, 0, limit - 1)
        counterparties = []
        for item in recent:
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            try:
                counterparty = json.loads(item)
                counterparties.append(counterparty)
            except:
                continue
        return counterparties

    async def add_counterparty(self, user_id: int, company1: str, company2: str) -> None:
        if self.redis is None:
            await self.connect()
        assert self.redis is not None

        counterparty = {
            "company1": company1,
            "company2": company2,
            "timestamp": datetime.now().isoformat(),
            "display": f"{company1} ↔ {company2}",
        }
        key = f"recent_counterparties:{user_id}"
        await self.redis.lpush(key, json.dumps(counterparty, ensure_ascii=False))
        await self.redis.ltrim(key, 0, 9)
        await self.redis.expire(key, 86400 * 30)
