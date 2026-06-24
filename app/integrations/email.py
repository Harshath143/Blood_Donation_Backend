import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from app.config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()

jinja_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent.parent.parent / "templates/email"),
    autoescape=select_autoescape(["html"])
)


async def send_email(
    to_email: str,
    subject: str,
    template: str,
    context: dict
) -> bool:
    """
    Send a single HTML email using SMTP.
    Returns True on success, False on failure (non-raising).
    """
    try:
        html_body = jinja_env.get_template(f"{template}.html").render(
            **context,
            app_name=settings.APP_NAME,
            support_email=settings.FROM_EMAIL
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS,
            timeout=15
        )

        logger.info("email_sent", to=to_email, template=template)
        return True

    except Exception as e:
        logger.error("email_failed", to=to_email, template=template, error=str(e))
        return False


# Convenience wrappers — called from Celery tasks

async def send_welcome_email(to_email: str, name: str):
    await send_email(to_email, "Welcome to LifeDrop 🩸", "welcome", {"name": name})

async def send_blood_request_alert(
    to_email: str,
    donor_name: str,
    blood_type: str,
    hospital: str,
    city: str,
    units: int,
    urgency: str,
    required_by: str,
    request_id: str,
    accept_url: str,
    decline_url: str
):
    await send_email(
        to_email,
        f"🩸 Urgent: {blood_type} blood needed at {hospital}",
        "blood_request_alert",
        {
            "donor_name": donor_name,
            "blood_type": blood_type,
            "hospital": hospital,
            "city": city,
            "units": units,
            "urgency": urgency.upper(),
            "required_by": required_by,
            "request_id": request_id,
            "accept_url": accept_url,
            "decline_url": decline_url
        }
    )

async def send_donation_reminder(
    to_email: str,
    donor_name: str,
    blood_type: str,
    last_donated: str
):
    await send_email(
        to_email,
        "You're eligible to donate again! 🩸",
        "donation_reminder",
        {
            "donor_name": donor_name,
            "blood_type": blood_type,
            "last_donated": last_donated,
            "donate_url": "https://lifedrop.in/donate"
        }
    )
