import hashlib

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError


class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(self, identity: str, scope: str, limit: int, window: int) -> None:
        key = f"rate-limit:{scope}:{identity}"
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, window, nx=True)
                count, _ = await pipe.execute()
            if count > limit:
                ttl = await self.redis.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests",
                    headers={"Retry-After": str(max(ttl, 1))},
                )
        except RedisError:
            return


def client_identity(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def private_identity(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()
