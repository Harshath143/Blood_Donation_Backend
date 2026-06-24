from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis
from app.database import get_db
from app.dependencies import get_redis

router = APIRouter()

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Heartbeat and health check for database and cache layers.
    """
    db_alive = False
    redis_alive = False

    try:
        await db.execute(text("SELECT 1"))
        db_alive = True
    except Exception:
        pass

    try:
        await redis.ping()
        redis_alive = True
    except Exception:
        pass

    status_code = 200 if (db_alive and redis_alive) else 503
    return {
        "status": "healthy" if status_code == 200 else "unhealthy",
        "database": "online" if db_alive else "offline",
        "redis": "online" if redis_alive else "offline"
    }
