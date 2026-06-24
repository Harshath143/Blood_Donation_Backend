import asyncio
from uuid import UUID
from app.tasks.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.websocket.manager import ws_manager
import structlog

logger = structlog.get_logger()

@celery_app.task(name="tasks.trigger_matching_task")
def trigger_matching_task(request_id: str):
    """
    Celery worker task to run the donor matching engine asynchronously.
    """
    async def run_matching():
        from app.services.notification_service import NotificationService
        from app.services.matching_service import MatchingService
        
        async with AsyncSessionLocal() as db:
            try:
                notif_service = NotificationService(db, ws_manager)
                matching_service = MatchingService(db, ws_manager, notif_service)
                result = await matching_service.find_and_notify_donors(UUID(request_id))
                logger.info("celery_matching_success", request_id=request_id, result=result)
            except Exception as e:
                logger.error("celery_matching_failed", request_id=request_id, error=str(e), exc_info=True)
                await db.rollback()

    asyncio.run(run_matching())

