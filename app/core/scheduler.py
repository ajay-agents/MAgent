import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core import campaigns
from app.core.delivery import claim_for_sending, deliver_claimed, recover_interrupted_sends
from app.db.session import SessionLocal
from app.models.models import ScheduledEmail, utcnow

logger = logging.getLogger("mailflow.scheduler")

_scheduler = BackgroundScheduler(daemon=True)


def _check_and_send_pending_emails() -> None:
    db = SessionLocal()
    try:
        due_ids = [
            row.id for row in db.query(ScheduledEmail.id)
            .filter(ScheduledEmail.status == "pending", ScheduledEmail.scheduled_at <= utcnow(),
                    campaigns.sending_campaign_filter())
            .order_by(ScheduledEmail.scheduled_at)
            .limit(100)
            .all()
        ]
        for email_id in due_ids:
            # Claim + commit per email: a crash mid-batch can't resend what already went out,
            # and a concurrent "Send now" or second worker can't send the same email twice.
            if not claim_for_sending(db, email_id, ("pending",)):
                continue
            deliver_claimed(db, db.get(ScheduledEmail, email_id))
    except Exception:
        logger.exception("Scheduler run failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    db = SessionLocal()
    try:
        recovered = recover_interrupted_sends(db)
        if recovered:
            logger.warning("Marked %d interrupted send(s) as failed", recovered)
    finally:
        db.close()

    _scheduler.add_job(
        _check_and_send_pending_emails,
        trigger="interval",
        minutes=1,
        id="send_scheduled_emails",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        campaigns.run_worker_tick,
        trigger="interval",
        seconds=30,
        id="campaign_worker",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=True)
