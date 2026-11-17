from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import settings
from app.core.delivery import claim_for_sending, daily_limit_message, deliver_claimed, sent_last_24h
from app.api.routes.profile import load_profile
from app.core.openai_client import REFINEMENT_INSTRUCTIONS, AIUnavailableError, generate_email
from app.core.plans import QuotaExceeded, metered_ai_call
from app.core.rate_limit import RateLimiter
from app.core.unsubscribe import is_suppressed
from app.core.security import get_current_user_id, get_verified_user_id
from app.db.session import get_db
from app.models.models import MailboxCredential, ScheduledEmail, utcnow
from app.schemas.schemas import (
    EmailListItem,
    EmailUpdate,
    GenerateEmailRequest,
    RegenerateRequest,
    GenerateEmailResponse,
    ScheduleEmailRequest,
    ScheduledEmailOut,
)

router = APIRouter(prefix="/api/emails", tags=["emails"])

generate_limiter = RateLimiter("generate", settings.rate_limit_generate_per_minute)

EDITABLE_STATUSES = ("draft", "failed", "pending")

AI_UNAVAILABLE = HTTPException(
    status_code=503,
    detail="The AI service is temporarily unavailable. Please try again in a minute.",
)


# ── Generate & save as draft ──────────────────────────────────────────────────

@router.post("/generate", response_model=GenerateEmailResponse, status_code=201,
             dependencies=[Depends(generate_limiter)])
def generate(
    payload: GenerateEmailRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_verified_user_id),
):
    try:
        result = metered_ai_call(db, user_id, lambda: generate_email(
            purpose=payload.purpose,
            tone=payload.tone,
            length=payload.length,
            sender_name=payload.sender_name,
            recipient_name=payload.recipient_name,
            recipient_email=str(payload.recipient_email),
            context=payload.context,
            profile=load_profile(db, user_id),
        ))
    except QuotaExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc))
    except AIUnavailableError:
        raise AI_UNAVAILABLE

    draft = ScheduledEmail(
        user_id=user_id,
        purpose=payload.purpose,
        tone=payload.tone,
        length=payload.length,
        sender_name=payload.sender_name,
        recipient_name=payload.recipient_name,
        recipient_email=str(payload.recipient_email),
        context=payload.context,
        subject=result["subject"],
        body=result["body"],
        status="draft",
        ai_model=result["ai_model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
        estimated_cost_usd=result["estimated_cost_usd"],
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return GenerateEmailResponse(
        id=draft.id,
        subject=result["subject"],
        body=result["body"],
        ai_model=result["ai_model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
        estimated_cost_usd=result["estimated_cost_usd"],
    )


# ── List emails ───────────────────────────────────────────────────────────────

@router.get("", response_model=list[EmailListItem])
def list_emails(
    status: str | None = Query(default=None, description="Filter by status: draft, pending, sent, failed"),
    include_campaigns: bool = Query(default=True, description="false hides emails that belong to a campaign"),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    q = db.query(ScheduledEmail).filter(ScheduledEmail.user_id == user_id)
    if status:
        q = q.filter(ScheduledEmail.status == status)
    if not include_campaigns:
        q = q.filter(ScheduledEmail.campaign_id.is_(None))
    return q.order_by(ScheduledEmail.created_at.desc()).offset(offset).limit(limit).all()


# ── Get single email ──────────────────────────────────────────────────────────

@router.get("/{email_id}", response_model=ScheduledEmailOut)
def get_email(
    email_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    return email


# ── Edit by hand ──────────────────────────────────────────────────────────────

@router.patch("/{email_id}", response_model=ScheduledEmailOut)
def update_email(
    email_id: int,
    payload: EmailUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return email
    _require_editable(email)
    # Conditional on status so an edit can't land after the scheduler has started sending
    if not _transition(db, email_id, (email.status,), **changes, edited_at=utcnow()):
        raise HTTPException(status_code=409, detail="This email changed while you were editing. Reload and try again.")
    db.refresh(email)
    return email


# ── Regenerate / refine with AI ───────────────────────────────────────────────

@router.post("/{email_id}/regenerate", response_model=ScheduledEmailOut,
             dependencies=[Depends(generate_limiter)])
def regenerate_email(
    email_id: int,
    payload: RegenerateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_verified_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    _require_editable(email)

    instructions = [i for i in (REFINEMENT_INSTRUCTIONS.get(payload.refinement or ""),
                                (payload.instruction or "").strip()) if i]
    revision = (
        {"subject": email.subject, "body": email.body, "instruction": " ".join(instructions)}
        if instructions else None
    )
    profile = load_profile(db, user_id)
    try:
        result = metered_ai_call(db, user_id, lambda: generate_email(
            purpose=email.purpose,
            tone=email.tone,
            length=email.length,
            sender_name=email.sender_name,
            recipient_name=email.recipient_name,
            recipient_email=email.recipient_email,
            context=email.context,
            profile=profile,
            revision=revision,
        ))
    except QuotaExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc))
    except AIUnavailableError:
        raise AI_UNAVAILABLE

    # Token/cost fields accumulate so usage reflects every AI call made for this email
    updated = _transition(
        db, email_id, (email.status,),
        # Follow-ups keep their "Re: ..." subject so they stay in the same thread
        subject=email.subject if email.step else result["subject"],
        body=result["body"],
        ai_model=result["ai_model"],
        prompt_tokens=(email.prompt_tokens or 0) + result["prompt_tokens"],
        completion_tokens=(email.completion_tokens or 0) + result["completion_tokens"],
        total_tokens=(email.total_tokens or 0) + result["total_tokens"],
        estimated_cost_usd=round((email.estimated_cost_usd or 0) + result["estimated_cost_usd"], 8),
    )
    if not updated:
        raise HTTPException(status_code=409, detail="This email changed while regenerating. Reload and try again.")
    db.refresh(email)
    return email


# ── Schedule a draft ──────────────────────────────────────────────────────────

@router.post("/{email_id}/schedule", response_model=ScheduledEmailOut)
def schedule_email(
    email_id: int,
    payload: ScheduleEmailRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_verified_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    if email.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Only draft or failed emails can be scheduled. Current status: {email.status}",
        )
    email.scheduled_at = payload.scheduled_at
    email.status = "pending"
    email.error_message = None
    db.commit()
    db.refresh(email)
    return email


# ── Cancel a scheduled email ──────────────────────────────────────────────────

@router.delete("/{email_id}/schedule", response_model=ScheduledEmailOut)
def cancel_schedule(
    email_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    if email.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending emails can be unscheduled. Current status: {email.status}",
        )
    # Conditional update: the scheduler may have claimed it since we loaded it
    if not _transition(db, email_id, ("pending",), status="draft", scheduled_at=None):
        raise HTTPException(status_code=409, detail="This email is already being sent.")
    db.refresh(email)
    return email


# ── Send immediately ──────────────────────────────────────────────────────────

@router.post("/{email_id}/send", response_model=ScheduledEmailOut)
def send_now(
    email_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_verified_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    if email.status not in ("draft", "failed", "pending"):
        raise HTTPException(status_code=400, detail=f"Email cannot be sent. Current status: {email.status}")

    if not db.query(MailboxCredential).filter(MailboxCredential.user_id == user_id).first():
        raise HTTPException(
            status_code=400,
            detail="No Gmail account configured. Add your credentials in Settings first.",
        )
    if sent_last_24h(db, user_id) >= settings.daily_send_limit:
        raise HTTPException(status_code=429, detail=daily_limit_message(db, user_id))
    if is_suppressed(db, user_id, email.recipient_email):
        raise HTTPException(status_code=400, detail=f"{email.recipient_email} unsubscribed or is on your "
                                                    "do-not-contact list, so this email can't be sent.")

    # A pending email sent now is no longer scheduled
    if not claim_for_sending(db, email_id, ("draft", "failed", "pending"), clear_schedule=True):
        raise HTTPException(status_code=409, detail="This email is already being sent.")
    if not deliver_claimed(db, email):
        raise HTTPException(status_code=502, detail=email.error_message)
    db.refresh(email)
    return email


# ── Soft-delete (move to trash) ───────────────────────────────────────────────

@router.delete("/{email_id}", response_model=ScheduledEmailOut)
def delete_email(
    email_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    from_status = email.status
    values = {"status": "deleted", "deleted_at": utcnow()}
    if from_status == "pending":
        values["scheduled_at"] = None  # cancel schedule automatically
    if from_status == "sending" or not _transition(db, email_id, (from_status,), **values):
        raise HTTPException(status_code=409, detail="This email is being sent right now and can't be deleted.")
    db.refresh(email)
    return email


# ── Restore from trash ────────────────────────────────────────────────────────

@router.post("/{email_id}/restore", response_model=ScheduledEmailOut)
def restore_email(
    email_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    if email.status != "deleted":
        raise HTTPException(status_code=400, detail="Only deleted emails can be restored.")
    email.status = "draft"
    email.deleted_at = None
    db.commit()
    db.refresh(email)
    return email


# ── Permanent delete ──────────────────────────────────────────────────────────

@router.delete("/{email_id}/permanent", status_code=204)
def permanent_delete(
    email_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    if email.status == "sending":
        raise HTTPException(status_code=409, detail="This email is being sent right now and can't be deleted.")
    db.delete(email)
    db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_editable(email: ScheduledEmail) -> None:
    if email.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=400, detail=f"A {email.status} email can't be changed.")


def _transition(db: Session, email_id: int, from_statuses: tuple[str, ...], **values) -> bool:
    """Update an email only if it is still in one of from_statuses."""
    result = db.execute(
        update(ScheduledEmail)
        .where(ScheduledEmail.id == email_id, ScheduledEmail.status.in_(from_statuses))
        .values(**values)
    )
    db.commit()
    return result.rowcount == 1


def _get_owned_email(email_id: int, user_id: int, db: Session) -> ScheduledEmail:
    email = db.query(ScheduledEmail).filter(
        ScheduledEmail.id == email_id,
        ScheduledEmail.user_id == user_id,
    ).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email
