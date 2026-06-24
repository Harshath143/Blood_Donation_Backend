import time
from redis.asyncio import Redis
from app.core.exceptions import RateLimitException

class RedisRateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_rate_limit(self, key: str, limit: int, period_seconds: int = 60):
        """
        Implements a sliding window rate limiting algorithm using Redis sorted sets (ZSET).
        Raises RateLimitException if the limit is exceeded.
        """
        now = time.time()
        clear_before = now - period_seconds
        
        # We use a pipeline for transaction execution
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, clear_before)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, period_seconds + 10)
            
            # Execute pipeline
            _, current_count, _, _ = await pipe.execute()
            
            if current_count >= limit:
                # If we exceed the limit, remove the timestamp we just added to not block future windows
                await self.redis.zrem(key, str(now))
                raise RateLimitException()
