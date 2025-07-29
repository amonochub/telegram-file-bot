from datetime import datetime, timedelta
from typing import Set

import redis.asyncio as aioredis
import structlog
from aiogram import Bot

import json

from app.utils.telegram_utils import escape_markdown

log = structlog.get_logger(__name__)


class CBRNotificationService:
    """Сервис уведомлений о курсах ЦБ"""

    def __init__(self, bot: Bot, redis_url: str):
        self.bot = bot
        self.redis_url = redis_url
        self.redis: aioredis.Redis | None = None
        self.subscribers: Set[int] = set()

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url)
        subscribers_data = await self.redis.smembers("cbr_subscribers")
        self.subscribers = {int(user_id) for user_id in subscribers_data}

    async def subscribe_user(self, user_id: int):
        self.subscribers.add(user_id)
        if self.redis is None:
            await self.connect()
        assert self.redis is not None
        await self.redis.sadd("cbr_subscribers", user_id)  # type: ignore[misc]

    async def unsubscribe_user(self, user_id: int):
        self.subscribers.discard(user_id)
        if self.redis is None:
            await self.connect()
        assert self.redis is not None
        await self.redis.srem("cbr_subscribers", user_id)  # type: ignore[misc]

    async def notify_all_rate_update(self, rates: dict):
        """Рассылает уведомление об изменении курсов.

        1. Берёт кэш вчерашнего дня.
        2. Считает разницу.
        3. Сохраняет новые курсы в Redis.
        """
        if self.redis is None:
            await self.connect()
        assert self.redis is not None

        yesterday_key = f"cbr:{(datetime.now().date() - timedelta(days=1)).isoformat()}"
        today_key = f"cbr:{datetime.now().date().isoformat()}"

        old_raw = await self.redis.get(yesterday_key)  # type: ignore[misc]
        old_rates = json.loads(old_raw) if old_raw else {}

        changes = []
        for cur, new_rate in rates.items():
            old_rate = old_rates.get(cur)
            if old_rate is None:
                continue
            diff = float(new_rate) - float(old_rate)
            changes.append(
                {
                    "currency": cur,
                    "old_rate": old_rate,
                    "new_rate": new_rate,
                    "change": diff,
                }
            )

        # сохраняем новый кэш
        await self.redis.set(today_key, json.dumps(rates, ensure_ascii=False), ex=60 * 60 * 12)  # type: ignore[misc]

        if not changes:
            return
        timestamp = datetime.now().strftime("%H:%M")
        message = f"🚨 **КУРСЫ ЦБ НА ЗАВТРА ОПУБЛИКОВАНЫ!** {timestamp}\n\n"
        for change in changes:
            currency = change["currency"]
            old_rate = change["old_rate"]
            new_rate = change["new_rate"]
            diff = change["change"]
            if diff > 0:
                trend = "📈"
                direction = f"+{diff:.4f}"
            else:
                trend = "📉"
                direction = f"{diff:.4f}"
            message += (
                f"{trend} **{currency}**: {old_rate} → **{new_rate}** ({direction})\n"
            )
        message += f"\n⏰ *Обновлено в {timestamp}*"
        failed_users = []
        for user_id in self.subscribers:
            try:
                await self.bot.send_message(
                    user_id, escape_markdown(message), parse_mode="Markdown"
                )
            except Exception as e:
                log.warning("cbr_notify_failed", user_id=user_id, error=str(e))
                failed_users.append(user_id)
        for user_id in failed_users:
            await self.unsubscribe_user(user_id)
        log.info("cbr_notify_sent", count=len(self.subscribers) - len(failed_users))
