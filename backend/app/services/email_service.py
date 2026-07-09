import logging

from app.config import settings

logger = logging.getLogger("agentforge.email")


async def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email via SendGrid. Returns True on success, False on failure."""
    if not settings.sendgrid_api_key:
        logger.info("[email] No SendGrid key configured — would send to %s: %s", to_email, subject)
        return False
    try:
        import sendgrid
        from sendgrid.helpers.mail import Content, Email, Mail, To

        sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
        mail = Mail(
            from_email=Email(settings.from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/plain", body),
        )
        response = sg.client.mail.send.post(request_body=mail.get())
        logger.info("Email sent to %s: %s (status %s)", to_email, subject, response.status_code)
        return 200 <= response.status_code < 300
    except ImportError:
        logger.warning("sendgrid package not installed — install with: pip install sendgrid")
        return False
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False
