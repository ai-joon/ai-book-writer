"""Redis cache for responses and rate limiting"""

import json
import os
from typing import Any, Optional

import redis.asyncio as redis_async
from redis.asyncio import Redis


class RedisCache:
    """Redis cache wrapper with JSON serialization"""

    def __init__(self):
        self.redis: Optional[Redis] = None
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    async def connect(self) -> None:
        """Connect to Redis"""
        self.redis = await redis_async.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        await self.redis.ping()

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None

        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = 3600
    ) -> None:
        """Set value in cache with optional TTL"""
        if not self.redis:
            return

        if not isinstance(value, str):
            value = json.dumps(value)

        if ttl:
            await self.redis.setex(key, ttl, value)
        else:
            await self.redis.set(key, value)

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        if self.redis:
            await self.redis.delete(key)

    async def increment(
        self,
        key: str,
        amount: int = 1,
        ttl: Optional[int] = None
    ) -> int:
        """Increment counter, useful for rate limiting"""
        if not self.redis:
            return 0

        value = await self.redis.incrby(key, amount)
        if ttl and value == amount:  # First increment
            await self.redis.expire(key, ttl)
        return value

    async def get_ttl(self, key: str) -> int:
        """Get TTL for a key"""
        if not self.redis:
            return -1
        return await self.redis.ttl(key)

    def cache_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments"""
        parts = [prefix] + [str(arg) for arg in args if arg is not None]
        return ":".join(parts)


# Global cache instance
cache = RedisCache()
