import hashlib
import json
import uuid
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings


class TaskCache:
    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def detail_key(user_id: uuid.UUID, task_id: uuid.UUID) -> str:
        return f"task:{user_id}:{task_id}"

    @staticmethod
    def list_set_key(user_id: uuid.UUID) -> str:
        return f"task-list-keys:{user_id}"

    @staticmethod
    def list_key(user_id: uuid.UUID, params: dict[str, Any]) -> str:
        raw = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
        digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
        return f"tasks:{user_id}:{digest}"

    async def get(self, key: str) -> dict | None:
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except (RedisError, json.JSONDecodeError):
            return None

    async def set(self, key: str, value: dict, ttl: int) -> None:
        try:
            await self.redis.set(key, json.dumps(value, default=str), ex=ttl)
        except RedisError:
            pass

    async def set_list(self, user_id: uuid.UUID, key: str, value: dict) -> None:
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(
                    key, json.dumps(value, default=str), ex=settings.task_list_cache_ttl_seconds
                )
                pipe.sadd(self.list_set_key(user_id), key)
                pipe.expire(self.list_set_key(user_id), settings.task_list_cache_ttl_seconds + 30)
                await pipe.execute()
        except RedisError:
            pass

    async def invalidate(self, user_id: uuid.UUID, task_id: uuid.UUID | None = None) -> None:
        try:
            set_key = self.list_set_key(user_id)
            list_keys = await self.redis.smembers(set_key)
            keys = list(list_keys) + [set_key]
            if task_id:
                keys.append(self.detail_key(user_id, task_id))
            if keys:
                await self.redis.delete(*keys)
        except RedisError:
            pass
