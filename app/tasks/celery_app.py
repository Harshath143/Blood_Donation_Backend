from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "lifedrop_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.matching_tasks",
        "app.tasks.reminder_tasks",
        "app.tasks.cleanup_tasks"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    worker_prefetch_multiplier=1,
)
