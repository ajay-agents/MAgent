"""Transactional email from MailFlow itself (not from a user's Gmail): verification and password reset."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.config import settings

logger = logging.getLogger("mailflow.system_mail")


def send_system_email(to: str, subject: str, body: str) -> None:
    if not settings.system_mail_enabled:
        # Development: no mail server configured, so make the message (and its link) visible in the log
        logger.warning("System email not configured; would send to %s:\n  Subject: %s\n  %s",
                       to, subject, body.replace("\n", "\n  "))
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid()
    msg.set_content(body)

    context = ssl.create_default_context()
    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20, context=context)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
            server.starttls(context=context)
        with server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError):
        # Runs as a background task: log loudly; the user can request the email again
        logger.exception("Failed to send system email to %s", to)
