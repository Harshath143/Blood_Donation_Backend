import asyncio
from datetime import date, timedelta
from sqlalchemy import select, and_, or_
from app.tasks.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.donor import Donor
from app.models.user import User
from app.integrations.email import send_donation_reminder
import structlog

logger = structlog.get_logger()

@celery_app.task(name="tasks.send_eligibility_reminders")
def send_eligibility_reminders():
    """
    Periodic task to identify donors who are newly eligible to donate again (56 days since last donation).
    """
    async def run_reminders():
        async with AsyncSessionLocal() as db:
            today = date.today()
            eligible_cutoff = today - timedelta(days=56)
            
            # Query active donors whose last donation date was >= 56 days ago
            stmt = (
                select(Donor, User)
                .join(User, Donor.user_id == User.id)
                .where(
                    and_(
                        Donor.is_active == True,
                        Donor.is_verified == True,
                        Donor.last_donation_date != None,
                        Donor.last_donation_date <= eligible_cutoff
                    )
                )
            )
            
            result = await db.execute(stmt)
            rows = result.all()
            
            logger.info("eligibility_reminders_scan", found=len(rows))
            
            for donor, user in rows:
                if user.email:
                    try:
                        await send_donation_reminder(
                            to_email=user.email,
                            donor_name=user.full_name,
                            blood_type=donor.blood_type,
                            last_donated=donor.last_donation_date.strftime('%Y-%m-%d')
                        )
                        logger.info("eligibility_reminder_sent", user_id=str(user.id))
                    except Exception as e:
                        logger.error("eligibility_reminder_failed", user_id=str(user.id), error=str(e))

    asyncio.run(run_reminders())
