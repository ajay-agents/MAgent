import sys
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.core.encryption import decrypt_password
from app.core.openai_client import generate_email
from app.core.security import get_current_user_id
from app.core.smtp_sender import send_email
from app.db.session import get_db
from app.models.models import MailboxCredential, ScheduledEmail
from app.schemas.schemas import (
    EmailListItem,
    GenerateEmailRequest,
    GenerateEmailResponse,
    ScheduleEmailRequest,
    ScheduledEmailOut,
)

router = APIRouter(prefix="/api/emails", tags=["emails"])

VALID_PURPOSES = {"cold_outreach", "follow_up", "job_application", "networking", "partnership", "thank_you"}
VALID_TONES    = {"professional", "friendly", "formal", "casual", "persuasive"}
VALID_LENGTHS  = {"short", "medium", "long"}


# ── Generate & save as draft ──────────────────────────────────────────────────

@router.post("/generate", response_model=GenerateEmailResponse, status_code=201)
def generate(
    payload: GenerateEmailRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if payload.purpose not in VALID_PURPOSES:
        raise HTTPException(status_code=400, detail=f"purpose must be one of: {', '.join(sorted(VALID_PURPOSES))}")
    if payload.tone not in VALID_TONES:
        raise HTTPException(status_code=400, detail=f"tone must be one of: {', '.join(sorted(VALID_TONES))}")
    if payload.length not in VALID_LENGTHS:
        raise HTTPException(status_code=400, detail=f"length must be one of: {', '.join(sorted(VALID_LENGTHS))}")

    try:
        result = generate_email(
            purpose=payload.purpose,
            tone=payload.tone,
            length=payload.length,
            sender_name=payload.sender_name,
            recipient_name=payload.recipient_name,
            recipient_email=str(payload.recipient_email),
            context=payload.context,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Email generation failed: {e}")

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
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    q = db.query(ScheduledEmail).filter(ScheduledEmail.user_id == user_id)
    if status:
        q = q.filter(ScheduledEmail.status == status)
    return q.order_by(ScheduledEmail.created_at.desc()).all()


# ── Get single email ──────────────────────────────────────────────────────────

@router.get("/{email_id}", response_model=ScheduledEmailOut)
def get_email(
    email_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    return email


# ── Schedule a draft ──────────────────────────────────────────────────────────

@router.post("/{email_id}/schedule", response_model=ScheduledEmailOut)
def schedule_email(
    email_id: int,
    payload: ScheduleEmailRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    if email.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Only draft or failed emails can be scheduled. Current status: {email.status}",
        )
    email.scheduled_at = payload.scheduled_at
    email.status = "pending"
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
    email.status = "draft"
    email.scheduled_at = None
    db.commit()
    db.refresh(email)
    return email


# ── Send immediately ──────────────────────────────────────────────────────────

@router.post("/{email_id}/send", response_model=ScheduledEmailOut)
def send_now(
    email_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    email = _get_owned_email(email_id, user_id, db)
    if email.status == "sent":
        raise HTTPException(status_code=400, detail="Email has already been sent.")
    if email.status == "pending":
        # Cancel the scheduled send and send immediately instead
        email.scheduled_at = None

    cred = db.query(MailboxCredential).filter(MailboxCredential.user_id == user_id).first()
    if not cred:
        raise HTTPException(
            status_code=400,
            detail="No Gmail account configured. Add your credentials in Settings first.",
        )

    try:
        password = decrypt_password(cred.encrypted_app_password, settings.fernet_key)
        send_email(
            gmail_address=cred.gmail_address,
            app_password=password,
            to_email=email.recipient_email,
            subject=email.subject,
            body=email.body,
        )
    except Exception as exc:
        email.status = "failed"
        db.commit()
        print(f"[Send] Failed id={email_id}: {exc}", file=sys.stderr)
        raise HTTPException(status_code=502, detail=f"SMTP send failed: {exc}")

    email.status = "sent"
    email.sent_at = datetime.utcnow()
    db.commit()
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
    if email.status == "pending":
        email.scheduled_at = None  # cancel schedule automatically
    email.status = "deleted"
    email.deleted_at = datetime.utcnow()
    db.commit()
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
    db.delete(email)
    db.commit()


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_owned_email(email_id: int, user_id: int, db: Session) -> ScheduledEmail:
    email = db.query(ScheduledEmail).filter(
        ScheduledEmail.id == email_id,
        ScheduledEmail.user_id == user_id,
    ).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email
