import logging
import smtplib

from datetime import timedelta

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.config import settings
from app.core import campaigns, unsubscribe
from app.core.encryption import decrypt_password
from app.core.google_oauth import GoogleApiError, GoogleAuthError, send_via_gmail_api
from app.core.smtp_sender import new_message_id, send_email
from app.models.models import MailboxCredential, ScheduledEmail, utcnow

logger = logging.getLogger("mailflow.delivery")


class DailyLimitReached(Exception):
    pass


def sent_last_24h(db: Session, user_id: int) -> int:
    since = utcnow() - timedelta(hours=24)
    return (db.query(func.count(ScheduledEmail.id))
            .filter(ScheduledEmail.user_id == user_id, ScheduledEmail.status.in_(("sent", "sending")),
                    ScheduledEmail.sent_at >= since).scalar())


def daily_limit_message(db: Session, user_id: int) -> str:
    return (f"You've sent {settings.daily_send_limit} emails in the last 24 hours, the safe daily limit for Gmail. "
            "Scheduled emails will keep going out automatically as the limit frees up.")


def claim_for_sending(db: Session, email_id: int, from_statuses: tuple[str, ...],
                      clear_schedule: bool = False) -> bool:
    """Atomically move an email to 'sending'. Returns False if another worker/request got it first."""
    values = {"status": "sending", "error_message": None, "sent_at": utcnow()}
    if clear_schedule:
        values["scheduled_at"] = None
    result = db.execute(
        update(ScheduledEmail)
        .where(ScheduledEmail.id == email_id, ScheduledEmail.status.in_(from_statuses))
        .values(**values)
    )
    db.commit()
    return result.rowcount == 1


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, GoogleAuthError):
        return "Google access for this Gmail account was revoked or expired. Reconnect Gmail in Settings."
    if isinstance(exc, GoogleApiError):
        return "Gmail couldn't send this email right now. Please try again."
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "Gmail rejected the login. Check the Gmail address and App Password in Settings."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "The recipient address was rejected by the mail server."
    if isinstance(exc, (smtplib.SMTPException, OSError)):
        return "Could not reach Gmail's mail server. Please try again."
    return "Sending failed due to an unexpected error."


def send_with_credential(cred: MailboxCredential, to_email: str, subject: str, body: str,
                         message_id: str, in_reply_to: str | None = None,
                         extra_headers: dict[str, str] | None = None) -> None:
    secret = decrypt_password(cred.encrypted_secret, settings.fernet_key)
    if cred.provider == "google":
        send_via_gmail_api(secret, cred.gmail_address, to_email, subject, body, message_id, in_reply_to,
                           extra_headers)
    else:
        send_email(gmail_address=cred.gmail_address, app_password=secret,
                   to_email=to_email, subject=subject, body=body,
                   message_id=message_id, in_reply_to=in_reply_to, extra_headers=extra_headers)


def _thread_parent_id(db: Session, email: ScheduledEmail) -> str | None:
    """Message-ID of the previous sent step for the same campaign recipient, so follow-ups thread."""
    if not email.campaign_recipient_id or not email.step:
        return None
    parent = (
        db.query(ScheduledEmail.message_id)
        .filter(ScheduledEmail.campaign_recipient_id == email.campaign_recipient_id,
                ScheduledEmail.step < email.step, ScheduledEmail.status == "sent",
                ScheduledEmail.message_id.isnot(None))
        .order_by(ScheduledEmail.step.desc())
        .first()
    )
    return parent[0] if parent else None


def deliver_claimed(db: Session, email: ScheduledEmail) -> bool:
    """Send an email already claimed via claim_for_sending. Commits the final status."""
    db.refresh(email)
    cred = db.query(MailboxCredential).filter(MailboxCredential.user_id == email.user_id).first()
    if not cred:
        email.status = "failed"
        email.sent_at = None
        email.error_message = "No Gmail account configured. Add your credentials in Settings."
        db.commit()
        return False

    # Last line of defence: checked at send time, so it covers anything queued before the opt-out
    if unsubscribe.is_suppressed(db, email.user_id, email.recipient_email):
        email.status = "failed"
        email.sent_at = None
        email.error_message = "Not sent: this address unsubscribed or is on your do-not-contact list."
        campaigns.on_email_suppressed(db, email)
        db.commit()
        return False

    body, headers = email.body, None
    if email.campaign_id:
        # Added at send time (not stored in the draft) so edits can never remove the opt-out
        footer, headers = unsubscribe.compliance_footer(db, email.user_id, email.recipient_email)
        body = email.body.rstrip() + "\n" + footer

    message_id = new_message_id(cred.gmail_address)
    try:
        send_with_credential(cred, email.recipient_email, email.subject, body,
                             message_id, _thread_parent_id(db, email), headers)
    except Exception as exc:
        logger.warning("Send failed for email id=%s: %s: %s", email.id, type(exc).__name__, exc)
        email.status = "failed"
        email.sent_at = None
        email.error_message = _friendly_error(exc)
        campaigns.on_email_failed(db, email)
        db.commit()
        return False

    email.status = "sent"
    email.sent_at = utcnow()
    email.message_id = message_id
    campaigns.on_email_sent(db, email)
    db.commit()
    logger.info("Sent email id=%s", email.id)
    return True


def recover_interrupted_sends(db: Session) -> int:
    """Emails stuck in 'sending' after a crash may or may not have gone out — never resend them blindly."""
    result = db.execute(
        update(ScheduledEmail)
        .where(ScheduledEmail.status == "sending")
        .values(status="failed",
                error_message="Sending was interrupted. Check your Gmail Sent folder before retrying.")
    )
    db.commit()
    return result.rowcount
