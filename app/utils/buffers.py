import pickle

import redis.asyncio as redis

from app.config import settings

redis_client = redis.from_url(settings.redis_url)


async def add_file(user_id: int, file_info):
    key = f"buffer:{user_id}"
    # Проверка размера буфера
    current_size = await redis_client.llen(key)
    if current_size >= settings.max_buffer_size:
        raise Exception(f"Буфер переполнен (макс. {settings.max_buffer_size})")
    await redis_client.rpush(key, pickle.dumps(file_info))
    await redis_client.expire(key, settings.cache_ttl)


async def get_batch(user_id: int):
    key = f"buffer:{user_id}"
    data = await redis_client.lrange(key, 0, -1)
    return [pickle.loads(x) for x in data]


async def flush_batch(user_id: int):
    key = f"buffer:{user_id}"
    data = await get_batch(user_id)
    await redis_client.delete(key)
    return data


async def get_size(user_id: int):
    key = f"buffer:{user_id}"
    return await redis_client.llen(key)


async def set_ttl(user_id: int, ttl: int):
    key = f"buffer:{user_id}"
    await redis_client.expire(key, ttl)
