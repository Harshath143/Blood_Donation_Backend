from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification
from app.models.donor import Donor
from app.models.user import User
from app.models.blood_request import BloodRequest
from app.tasks.email_tasks import send_email_task
import structlog

logger = structlog.get_logger()


class NotificationService:

    def __init__(self, db: AsyncSession, ws_manager):
        self.db = db
        self.ws_manager = ws_manager

    async def notify_donor(
        self,
        donor: Donor,
        request: BloodRequest,
        channels: list[str]
    ):
        title = f"🩸 Urgent: {request.blood_type_needed} blood needed at {request.hospital_name}"
        body = f"Hello, {request.patient_name} needs {request.blood_type_needed} blood units ({request.units_needed} units) by {request.required_by.strftime('%Y-%m-%d %H:%M')}. Can you help?"
        
        # Load user to get email/phone details
        user = await self.db.get(User, donor.user_id)
        if not user:
            logger.error("donor_user_not_found", donor_id=str(donor.id), user_id=str(donor.user_id))
            return

        # 1. Store in-app notification
        if "in_app" in channels:
            notif = Notification(
                user_id=donor.user_id,
                type="blood_request_alert",
                title=title,
                body=body,
                data={
                    "request_id": str(request.id),
                    "blood_type": request.blood_type_needed,
                    "units": request.units_needed,
                    "hospital": request.hospital_name,
                    "city": request.city,
                    "urgency": request.urgency_level
                },
                channels=["in_app"]
            )
            self.db.add(notif)
            await self.db.flush()

            # Push WebSocket payload
            await self.ws_manager.send_to_user(
                str(donor.user_id),
                {
                    "event": "new_notification",
                    "notification_id": str(notif.id),
                    "type": "blood_request_alert",
                    "title": title,
                    "body": body,
                    "data": notif.data
                }
            )

        # 2. Fire out-of-band email dispatch Celery task
        if "email" in channels and user.email:
            # We delay the Celery task
            accept_url = f"https://lifedrop.netlify.app/requests/{request.id}/accept?donor_id={donor.id}"
            decline_url = f"https://lifedrop.netlify.app/requests/{request.id}/decline?donor_id={donor.id}"
            
            # send_email_task arguments matching our celery tasks signatures
            send_email_task.delay(
                to_email=user.email,
                subject=title,
                template="blood_request_alert",
                context={
                    "donor_name": user.full_name,
                    "blood_type": request.blood_type_needed,
                    "hospital": request.hospital_name,
                    "city": request.city,
                    "units": request.units_needed,
                    "urgency": request.urgency_level,
                    "required_by": request.required_by.strftime('%Y-%m-%d %H:%M'),
                    "request_id": str(request.id),
                    "accept_url": accept_url,
                    "decline_url": decline_url
                }
            )

    async def notify_no_match(self, request: BloodRequest):
        """Notify the requester that no compatible donors were found within maximum range."""
        title = "🩸 LifeDrop: No matches found"
        body = f"We searched up to 100km but could not find matching donors for request {request.request_number} yet. We will continue checking."
        
        # Load user
        user = await self.db.get(User, request.requester_id)
        if not user:
            return

        notif = Notification(
            user_id=request.requester_id,
            type="no_match",
            title=title,
            body=body,
            data={"request_id": str(request.id)},
            channels=["in_app"]
        )
        self.db.add(notif)
        await self.db.flush()

        await self.ws_manager.send_to_user(
            str(request.requester_id),
            {
                "event": "new_notification",
                "notification_id": str(notif.id),
                "type": "no_match",
                "title": title,
                "body": body,
                "data": notif.data
            }
        )

        if user.email:
            send_email_task.delay(
                to_email=user.email,
                subject=title,
                template="emergency_alert", # fallback template
                context={
                    "alert_title": title,
                    "alert_body": body,
                    "action_url": "https://lifedrop.netlify.app/dashboard"
                }
            )
