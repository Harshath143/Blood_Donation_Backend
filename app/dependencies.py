from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis, from_url
from app.config import get_settings
from app.database import get_db
from app.core.security import verify_token
from app.models.user import User

settings = get_settings()
security = HTTPBearer()

# Redis connection pool
redis_pool = None

async def get_redis() -> AsyncGenerator[Redis, None]:
    """Provides a thread-safe Redis client session."""
    global redis_pool
    if redis_pool is None:
        redis_pool = from_url(settings.REDIS_URL)
    
    async with Redis(connection_pool=redis_pool.connection_pool) as client:
        yield client


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Verifies JWT token and retrieves the current authenticated user."""
    payload = await verify_token(token.credentials, redis)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    # Load user from db
    user = await db.get(User, user_id)
    if not user or user.is_deleted or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """Enforces role-based access control (RBAC)."""
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this resource"
            )
        return current_user


async def rate_limit_auth(request: Request, redis: Redis = Depends(get_redis)):
    from app.core.rate_limiter import RedisRateLimiter
    ip = request.client.host if request.client else "unknown"
    limiter = RedisRateLimiter(redis)
    await limiter.check_rate_limit(
        f"rate_limit:auth:{ip}",
        limit=settings.AUTH_RATE_LIMIT_PER_MINUTE,
        period_seconds=60
    )


async def rate_limit_standard(request: Request, redis: Redis = Depends(get_redis)):
    from app.core.rate_limiter import RedisRateLimiter
    ip = request.client.host if request.client else "unknown"
    limiter = RedisRateLimiter(redis)
    await limiter.check_rate_limit(
        f"rate_limit:standard:{ip}",
        limit=settings.RATE_LIMIT_PER_MINUTE,
        period_seconds=60
    )


async def rate_limit_emergency(request: Request, redis: Redis = Depends(get_redis)):
    from app.core.rate_limiter import RedisRateLimiter
    ip = request.client.host if request.client else "unknown"
    limiter = RedisRateLimiter(redis)
    await limiter.check_rate_limit(
        f"rate_limit:emergency:{ip}",
        limit=settings.EMERGENCY_RATE_LIMIT_PER_MINUTE,
        period_seconds=60
    )

