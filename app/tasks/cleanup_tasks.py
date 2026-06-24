import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, update, and_
from app.tasks.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.blood_request import BloodRequest
import structlog

logger = structlog.get_logger()

@celery_app.task(name="tasks.cleanup_expired_requests")
def cleanup_expired_requests():
    """
    Periodic task to identify open blood requests where the required_by date has passed and mark them as expired.
    """
    async def run_cleanup():
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            
            stmt = (
                update(BloodRequest)
                .where(
                    and_(
                        BloodRequest.status == "searching",
                        BloodRequest.required_by < now
                    )
                )
                .values(status="expired")
            )
            
            result = await db.execute(stmt)
            await db.commit()
            
            logger.info("expired_requests_cleanup", updated_count=result.rowcount)

    asyncio.run(run_cleanup())
