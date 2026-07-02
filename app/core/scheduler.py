import sys
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.core.encryption import decrypt_password
from app.core.smtp_sender import send_email
from app.db.session import SessionLocal
from app.models.models import MailboxCredential, ScheduledEmail

_scheduler = BackgroundScheduler(daemon=True)


def _check_and_send_pending_emails() -> None:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        pending = (
            db.query(ScheduledEmail)
            .filter(
                ScheduledEmail.status == "pending",
                ScheduledEmail.scheduled_at <= now,
            )
            .all()
        )

        for email in pending:
            try:
                cred = (
                    db.query(MailboxCredential)
                    .filter(MailboxCredential.user_id == email.user_id)
                    .first()
                )
                if not cred:
                    email.status = "failed"
                    continue

                password = decrypt_password(cred.encrypted_app_password, settings.fernet_key)
                send_email(
                    gmail_address=cred.gmail_address,
                    app_password=password,
                    to_email=email.recipient_email,
                    subject=email.subject,
                    body=email.body,
                )
                email.status = "sent"
                email.sent_at = datetime.utcnow()

            except Exception as exc:
                email.status = "failed"
                print(
                    f"[Scheduler] Failed to send email id={email.id}: {exc}",
                    file=sys.stderr,
                )

        db.commit()
    finally:
        db.close()


def start_scheduler() -> None:
    _scheduler.add_job(
        _check_and_send_pending_emails,
        trigger="interval",
        minutes=1,
        id="send_scheduled_emails",
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
