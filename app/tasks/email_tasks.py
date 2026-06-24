import asyncio
from app.tasks.celery_app import celery_app
from app.integrations.email import send_email

@celery_app.task(name="tasks.send_email_task")
def send_email_task(to_email: str, subject: str, template: str, context: dict):
    """Celery worker task to execute async email delivery."""
    try:
        asyncio.run(send_email(
            to_email=to_email,
            subject=subject,
            template=template,
            context=context
        ))
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("celery_email_task_failed", to=to_email, error=str(e))
