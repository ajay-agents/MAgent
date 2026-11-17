"""Campaigns: CSV import, background generation, staggered launch, follow-ups and reply handling.

Generation runs in the scheduler's background worker, not in the request: a free-tier AI provider
manages only a few emails per minute. All progress lives in the database, so the worker resumes
after a restart.
"""

import csv
import io
import logging
from datetime import datetime, timedelta

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.api.routes.profile import load_profile
from app.core.openai_client import AIUnavailableError, generate_email, providers_configured
from app.core.plans import QuotaExceeded, get_plan, metered_ai_call
from app.core.unsubscribe import suppressed_set
from app.models.models import Campaign, CampaignRecipient, ScheduledEmail, utcnow

logger = logging.getLogger("mailflow.campaigns")

GENERATE_PER_TICK = 4
UNSENT = ("draft", "pending")

# CSV header aliases (compared lower-cased, spaces/underscores removed)
_EMAIL_COLS   = {"email", "emailaddress", "mail", "e-mail"}
_NAME_COLS    = {"name", "fullname", "contactname"}
_FIRST_COLS   = {"firstname", "first", "givenname"}
_LAST_COLS    = {"lastname", "last", "surname", "familyname"}
_COMPANY_COLS = {"company", "organization", "organisation", "companyname", "org"}
_ROLE_COLS    = {"title", "role", "jobtitle", "position", "designation"}
_NOTES_COLS   = {"notes", "note", "context", "personalization", "personalisation", "about", "details"}


# ── CSV import ────────────────────────────────────────────────────────────────

def _norm(header: str) -> str:
    return header.strip().lower().replace(" ", "").replace("_", "")


def parse_csv(text: str) -> tuple[list[dict], list[dict]]:
    """Return (rows, skipped). Rows: {email, name, company, notes}. Skipped: {row, reason}."""
    text = text.lstrip("﻿")  # Excel's UTF-8 BOM
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("The CSV is empty.")

    cols = {_norm(h): h for h in reader.fieldnames if h}
    def pick(aliases):
        return next((cols[a] for a in aliases if a in cols), None)

    email_col = pick(_EMAIL_COLS)
    if not email_col:
        raise ValueError("The CSV needs an 'email' column.")
    name_col, first_col, last_col = pick(_NAME_COLS), pick(_FIRST_COLS), pick(_LAST_COLS)
    company_col, role_col, notes_col = pick(_COMPANY_COLS), pick(_ROLE_COLS), pick(_NOTES_COLS)

    rows, skipped, seen = [], [], set()
    for line_no, raw in enumerate(reader, start=2):  # row 1 is the header
        get = lambda col: (raw.get(col) or "").strip() if col else ""
        address = get(email_col)
        if not address and not any((v or "").strip() for v in raw.values() if isinstance(v, str)):
            continue  # blank line
        try:
            address = validate_email(address, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            skipped.append({"row": line_no, "reason": f"invalid email '{address[:60]}'"})
            continue
        if address in seen:
            skipped.append({"row": line_no, "reason": f"duplicate {address}"})
            continue
        seen.add(address)

        name = get(name_col) or " ".join(p for p in (get(first_col), get(last_col)) if p)
        if not name:
            name = address.split("@")[0].replace(".", " ").title()
        notes = "; ".join(p for p in (f"Role: {get(role_col)}" if get(role_col) else "", get(notes_col)) if p)
        rows.append({"email": address, "name": name[:100], "company": get(company_col)[:150] or None,
                     "notes": notes[:2000] or None})
    return rows, skipped


def add_recipients(db: Session, campaign: Campaign, rows: list[dict]) -> tuple[int, list[dict]]:
    existing = {e for (e,) in db.query(CampaignRecipient.email).filter(CampaignRecipient.campaign_id == campaign.id)}
    blocked = suppressed_set(db, campaign.user_id)
    plan = get_plan(db, campaign.user_id)
    room = plan.campaign_recipients - len(existing)
    added, skipped = 0, []
    for row in rows:
        if row["email"] in existing:
            skipped.append({"row": None, "reason": f"{row['email']} is already in this campaign"})
            continue
        if row["email"] in blocked:
            skipped.append({"row": None, "reason": f"{row['email']} unsubscribed or is on your do-not-contact list"})
            continue
        if added >= room:
            upsell = " Upgrade to Pro for up to 500." if plan.id == "free" else ""
            skipped.append({"row": None, "reason": f"the {plan.name} plan allows {plan.campaign_recipients} "
                                                   f"recipients per campaign; the rest were not added.{upsell}"})
            break
        db.add(CampaignRecipient(campaign_id=campaign.id, **row))
        existing.add(row["email"])
        added += 1
    db.commit()
    return added, skipped


# ── Prompt context ────────────────────────────────────────────────────────────

def recipient_context(campaign: Campaign, r: CampaignRecipient) -> str:
    parts = []
    if campaign.context:
        parts.append(campaign.context)
    about = "; ".join(p for p in (f"Company: {r.company}" if r.company else "", r.notes or "") if p)
    if about:
        parts.append(f"About {r.name}: {about}")
    return "\n".join(parts)


def followup_context(campaign: Campaign, r: CampaignRecipient, previous: list[ScheduledEmail]) -> str:
    history = "\n\n".join(
        f"Email {i + 1} (sent {p.sent_at:%d %b}):\nSubject: {p.subject}\n{p.body}" for i, p in enumerate(previous)
    )
    n = len(previous)
    return (
        f"{recipient_context(campaign, r)}\n\n"
        f"This is follow-up #{n} in a thread. {r.name} has NOT replied to the earlier email(s) below, so never "
        "claim or imply they said, asked, mentioned or wanted anything. "
        "Write a short, polite follow-up that adds one new angle or makes the ask easier. "
        "Don't repeat the first email, don't guilt-trip, don't say 'just bumping this', and don't propose a "
        "specific day or time for a meeting (the sender hasn't checked their calendar)."
        + (" This is the last follow-up, so close the loop gracefully." if n >= campaign.followup_count else "")
        + f"\n\nEarlier emails:\n{history}"
    )


# ── Background worker ─────────────────────────────────────────────────────────

def _generate(db: Session, campaign: Campaign, r: CampaignRecipient, purpose: str, context: str) -> dict:
    profile = load_profile(db, campaign.user_id)
    db.commit()  # don't hold a DB transaction open during the slow AI call
    # Never pad a campaign with canned mock emails when real providers are just rate-limited:
    # fail instead and let the next tick retry. Mock is used only when no provider is configured (dev/tests).
    return metered_ai_call(db, campaign.user_id, lambda: generate_email(
        purpose=purpose, tone=campaign.tone, length=campaign.length,
        sender_name=campaign.sender_name, recipient_name=r.name, recipient_email=r.email,
        context=context, profile=profile, allow_mock=not providers_configured(),
    ))


def _email_from_result(campaign: Campaign, r: CampaignRecipient, result: dict, context: str, step: int,
                       subject: str | None = None, status: str = "draft", **extra) -> ScheduledEmail:
    return ScheduledEmail(
        user_id=campaign.user_id, campaign_id=campaign.id, campaign_recipient_id=r.id, step=step,
        purpose=campaign.purpose if step == 0 else "follow_up", tone=campaign.tone, length=campaign.length,
        sender_name=campaign.sender_name, recipient_name=r.name, recipient_email=r.email, context=context,
        subject=subject or result["subject"], body=result["body"], status=status,
        ai_model=result["ai_model"], prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"], total_tokens=result["total_tokens"],
        estimated_cost_usd=result["estimated_cost_usd"], **extra,
    )


def _generate_initial_batch(db: Session, limit: int) -> int:
    queued = (
        db.query(CampaignRecipient, Campaign)
        .join(Campaign, Campaign.id == CampaignRecipient.campaign_id)
        .filter(CampaignRecipient.status == "queued")
        .order_by(CampaignRecipient.id).limit(limit).all()
    )
    done = 0
    for r, campaign in queued:
        context = recipient_context(campaign, r)
        try:
            result = _generate(db, campaign, r, campaign.purpose, context)
        except AIUnavailableError:
            raise
        except QuotaExceeded as exc:
            # Out of AI emails this month: park it with an explanation; "Write emails" retries later
            db.execute(update(CampaignRecipient).where(CampaignRecipient.id == r.id, CampaignRecipient.status == "queued")
                       .values(status="error", error_message=str(exc)[:500]))
            db.commit()
            continue
        except Exception as exc:
            logger.exception("Generation failed for recipient %s", r.id)
            db.execute(update(CampaignRecipient).where(CampaignRecipient.id == r.id, CampaignRecipient.status == "queued")
                       .values(status="error", error_message=f"Generation failed: {type(exc).__name__}"))
            db.commit()
            continue
        # The recipient may have been removed while we waited on the AI
        claimed = db.execute(update(CampaignRecipient)
                             .where(CampaignRecipient.id == r.id, CampaignRecipient.status == "queued")
                             .values(status="ready", error_message=None)).rowcount
        if claimed:
            db.add(_email_from_result(campaign, r, result, context, step=0))
            done += 1
        db.commit()
    return done


def _sent_steps(db: Session, recipient_id: int) -> list[ScheduledEmail]:
    return (db.query(ScheduledEmail)
            .filter(ScheduledEmail.campaign_recipient_id == recipient_id, ScheduledEmail.status == "sent")
            .order_by(ScheduledEmail.step).all())


def _owed_followups(db: Session, campaign_id: int | None = None, limit: int = 50):
    """(recipient, campaign) pairs that are mid-sequence with no follow-up waiting."""
    has_unsent = (db.query(ScheduledEmail.id)
                  .filter(ScheduledEmail.campaign_recipient_id == CampaignRecipient.id,
                          ScheduledEmail.status.in_(UNSENT + ("sending",)))
                  .exists())
    q = (db.query(CampaignRecipient, Campaign)
         .join(Campaign, Campaign.id == CampaignRecipient.campaign_id)
         .filter(CampaignRecipient.status == "contacted", Campaign.followup_count > 0,
                 Campaign.status.in_(("running", "paused")), ~has_unsent))
    if campaign_id:
        q = q.filter(Campaign.id == campaign_id)
    return q.order_by(CampaignRecipient.id).limit(limit).all()


def _generate_followup_batch(db: Session, limit: int) -> int:
    done = 0
    out_of_quota: set[int] = set()  # users skipped this tick, so they can't starve everyone else's follow-ups
    for r, campaign in _owed_followups(db, limit=200):
        if done >= limit:
            break
        if campaign.user_id in out_of_quota:
            continue
        if not get_plan(db, campaign.user_id).followups:  # downgraded after launch
            r.status, r.error_message = "completed", "Follow-ups stopped: they need the Pro plan."
            db.commit()
            continue
        sent = _sent_steps(db, r.id)
        if not sent or len(sent) > campaign.followup_count:
            continue
        step = sent[-1].step + 1
        context = followup_context(campaign, r, sent)
        send_at = max(sent[-1].sent_at + timedelta(days=campaign.followup_delay_days), utcnow())
        root_subject = sent[0].subject
        subject = root_subject if root_subject.lower().startswith("re:") else f"Re: {root_subject}"
        try:
            result = _generate(db, campaign, r, "follow_up", context)  # AIUnavailableError propagates: retry next tick
        except QuotaExceeded as exc:
            out_of_quota.add(campaign.user_id)
            r.error_message = f"Follow-up waiting: {exc}"[:500]
            db.commit()
            continue
        db.refresh(r)
        if r.status != "contacted":  # they replied (or were removed) while we waited on the AI
            continue
        r.error_message = None
        db.add(_email_from_result(campaign, r, result, context, step=step, subject=subject,
                                  status="pending", scheduled_at=send_at))
        db.commit()
        done += 1
    return done


def _complete_finished_campaigns(db: Session) -> None:
    for campaign in db.query(Campaign).filter(Campaign.status == "running").all():
        unsent = (db.query(func.count(ScheduledEmail.id))
                  .filter(ScheduledEmail.campaign_id == campaign.id,
                          ScheduledEmail.status.in_(("pending", "sending"))).scalar())
        queued = (db.query(func.count(CampaignRecipient.id))
                  .filter(CampaignRecipient.campaign_id == campaign.id,
                          CampaignRecipient.status == "queued").scalar())
        if not unsent and not queued and not _owed_followups(db, campaign.id, limit=1):
            campaign.status = "completed"
            logger.info("Campaign %s completed", campaign.id)
    db.commit()


def run_worker_tick() -> None:
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        made = _generate_initial_batch(db, GENERATE_PER_TICK)
        _generate_followup_batch(db, max(GENERATE_PER_TICK - made, 1))
    except AIUnavailableError:
        logger.warning("AI unavailable (likely rate-limited); campaign generation will retry next tick")
        db.rollback()
    except Exception:
        logger.exception("Campaign worker tick failed")
        db.rollback()
    try:
        _complete_finished_campaigns(db)
    except Exception:
        logger.exception("Campaign completion check failed")
        db.rollback()
    finally:
        db.close()


# ── Sending hooks (called by delivery inside its transaction) ────────────────

def on_email_sent(db: Session, email: ScheduledEmail) -> None:
    if not email.campaign_recipient_id:
        return
    r = db.get(CampaignRecipient, email.campaign_recipient_id)
    if not r or r.status in ("replied", "unsubscribed"):
        return
    campaign = db.get(Campaign, r.campaign_id)
    r.status = "completed" if email.step >= campaign.followup_count else "contacted"
    r.error_message = None


def on_email_suppressed(db: Session, email: ScheduledEmail) -> None:
    if email.campaign_recipient_id:
        r = db.get(CampaignRecipient, email.campaign_recipient_id)
        if r:
            r.status, r.error_message = "unsubscribed", None


def on_email_failed(db: Session, email: ScheduledEmail) -> None:
    if not email.campaign_recipient_id:
        return
    r = db.get(CampaignRecipient, email.campaign_recipient_id)
    if r and r.status not in ("replied", "unsubscribed"):
        r.status = "failed"
        r.error_message = email.error_message


# ── User actions ──────────────────────────────────────────────────────────────

def queue_generation(db: Session, campaign: Campaign) -> int:
    n = db.execute(update(CampaignRecipient)
                   .where(CampaignRecipient.campaign_id == campaign.id, CampaignRecipient.status.in_(("new", "error")))
                   .values(status="queued", error_message=None)).rowcount
    db.commit()
    return n


def launch(db: Session, campaign: Campaign, start_at: datetime) -> int:
    """Schedule every ready recipient's first email, `send_interval_minutes` apart."""
    rows = (db.query(CampaignRecipient, ScheduledEmail)
            .join(ScheduledEmail, (ScheduledEmail.campaign_recipient_id == CampaignRecipient.id)
                  & (ScheduledEmail.step == 0) & (ScheduledEmail.status == "draft"))
            .filter(CampaignRecipient.campaign_id == campaign.id, CampaignRecipient.status == "ready")
            .order_by(CampaignRecipient.id).all())
    for i, (r, email) in enumerate(rows):
        email.status = "pending"
        email.scheduled_at = start_at + timedelta(minutes=campaign.send_interval_minutes * i)
        r.status = "scheduled"
    campaign.status = "running"
    campaign.launched_at = utcnow()
    db.commit()
    return len(rows)


def pause(db: Session, campaign: Campaign) -> None:
    campaign.status = "paused"  # the scheduler skips pending emails of paused campaigns
    db.commit()


def resume(db: Session, campaign: Campaign) -> None:
    """Re-space overdue emails so resuming doesn't send a burst."""
    now = utcnow()
    overdue = (db.query(ScheduledEmail)
               .filter(ScheduledEmail.campaign_id == campaign.id, ScheduledEmail.status == "pending",
                       ScheduledEmail.scheduled_at <= now)
               .order_by(ScheduledEmail.scheduled_at).all())
    for i, email in enumerate(overdue):
        email.scheduled_at = now + timedelta(minutes=campaign.send_interval_minutes * i)
    campaign.status = "running"
    db.commit()


def _drop_unsent(db: Session, *conditions) -> None:
    db.execute(delete(ScheduledEmail).where(ScheduledEmail.status.in_(UNSENT), *conditions))


def mark_replied(db: Session, r: CampaignRecipient) -> None:
    """Stop the sequence: unsent follow-ups for this person are removed."""
    r.status = "replied"
    r.replied_at = utcnow()
    _drop_unsent(db, ScheduledEmail.campaign_recipient_id == r.id)
    db.commit()


def remove_recipient(db: Session, r: CampaignRecipient) -> None:
    _drop_unsent(db, ScheduledEmail.campaign_recipient_id == r.id)
    # Sent emails stay in the user's history, detached from the deleted recipient
    db.execute(update(ScheduledEmail).where(ScheduledEmail.campaign_recipient_id == r.id)
               .values(campaign_recipient_id=None))
    db.delete(r)
    db.commit()


def delete_campaign(db: Session, campaign: Campaign) -> None:
    _drop_unsent(db, ScheduledEmail.campaign_id == campaign.id)
    db.execute(update(ScheduledEmail).where(ScheduledEmail.campaign_id == campaign.id)
               .values(campaign_id=None, campaign_recipient_id=None))
    db.execute(delete(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))
    db.delete(campaign)
    db.commit()


def sending_campaign_filter():
    """Scheduler filter: one-off emails, or emails of campaigns that aren't paused."""
    paused = select(Campaign.id).where(Campaign.status == "paused")
    return or_(ScheduledEmail.campaign_id.is_(None), ScheduledEmail.campaign_id.notin_(paused))
