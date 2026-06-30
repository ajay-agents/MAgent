from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import ScheduledEmail
from app.schemas.schemas import GenerateEmailRequest, GenerateEmailResponse
from app.core.security import get_current_user_id
from app.core.openai_client import generate_email

router = APIRouter(prefix="/api/emails", tags=["emails"])

VALID_PURPOSES = {"cold_outreach", "follow_up", "job_application", "networking", "partnership", "thank_you"}
VALID_TONES = {"professional", "friendly", "formal", "casual", "persuasive"}
VALID_LENGTHS = {"short", "medium", "long"}


@router.post("/generate", response_model=GenerateEmailResponse)
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
            recipient_email=payload.recipient_email,
            context=payload.context,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Email generation failed: {str(e)}")

    # Save as draft so it can be scheduled later
    draft = ScheduledEmail(
        user_id=user_id,
        purpose=payload.purpose,
        tone=payload.tone,
        length=payload.length,
        sender_name=payload.sender_name,
        recipient_name=payload.recipient_name,
        recipient_email=payload.recipient_email,
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

    return GenerateEmailResponse(
        subject=result["subject"],
        body=result["body"],
        ai_model=result["ai_model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
        estimated_cost_usd=result["estimated_cost_usd"],
    )
