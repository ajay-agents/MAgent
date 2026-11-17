from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import campaigns as svc
from app.core import plans
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.models import Campaign, CampaignRecipient, MailboxCredential, ScheduledEmail, utcnow
from app.schemas.schemas import (
    CampaignCreate,
    CampaignLaunch,
    CampaignOut,
    CampaignRecipientOut,
    CampaignStats,
    CsvUpload,
)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _owned(db: Session, campaign_id: int, user_id: int) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _owned_recipient(db: Session, campaign: Campaign, recipient_id: int) -> CampaignRecipient:
    r = db.query(CampaignRecipient).filter(CampaignRecipient.id == recipient_id,
                                           CampaignRecipient.campaign_id == campaign.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")
    return r


def _stats(db: Session, campaign_ids: list[int]) -> dict[int, CampaignStats]:
    counts: dict[int, dict] = defaultdict(dict)
    for cid, status, n in (db.query(CampaignRecipient.campaign_id, CampaignRecipient.status, func.count())
                           .filter(CampaignRecipient.campaign_id.in_(campaign_ids))
                           .group_by(CampaignRecipient.campaign_id, CampaignRecipient.status)):
        counts[cid][status] = n
        counts[cid]["recipients"] = counts[cid].get("recipients", 0) + n
    for cid, n in (db.query(ScheduledEmail.campaign_id, func.count())
                   .filter(ScheduledEmail.campaign_id.in_(campaign_ids), ScheduledEmail.status == "sent")
                   .group_by(ScheduledEmail.campaign_id)):
        counts[cid]["emails_sent"] = n
    return {cid: CampaignStats(**counts.get(cid, {})) for cid in campaign_ids}


def _out(db: Session, campaign: Campaign) -> CampaignOut:
    out = CampaignOut.model_validate(campaign)
    out.stats = _stats(db, [campaign.id])[campaign.id]
    return out


def _require_status(campaign: Campaign, *allowed: str) -> None:
    if campaign.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Not possible while the campaign is {campaign.status}.")


# ── Campaign CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    items = db.query(Campaign).filter(Campaign.user_id == user_id).order_by(Campaign.created_at.desc()).all()
    stats = _stats(db, [c.id for c in items])
    return [CampaignOut.model_validate(c).model_copy(update={"stats": stats[c.id]}) for c in items]


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db),
                    user_id: int = Depends(get_current_user_id)):
    campaign = Campaign(user_id=user_id, **payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _out(db, campaign)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return _out(db, _owned(db, campaign_id, user_id))


@router.put("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, payload: CampaignCreate, db: Session = Depends(get_db),
                    user_id: int = Depends(get_current_user_id)):
    """Edit the shared settings. Only affects emails generated afterwards."""
    campaign = _owned(db, campaign_id, user_id)
    _require_status(campaign, "draft")
    for k, v in payload.model_dump().items():
        setattr(campaign, k, v)
    db.commit()
    return _out(db, campaign)


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Removes the campaign and its unsent emails. Already-sent emails stay in Sent."""
    svc.delete_campaign(db, _owned(db, campaign_id, user_id))


# ── Recipients ────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/recipients/csv")
def import_csv(campaign_id: int, payload: CsvUpload, db: Session = Depends(get_db),
               user_id: int = Depends(get_current_user_id)):
    campaign = _owned(db, campaign_id, user_id)
    _require_status(campaign, "draft")
    try:
        rows, skipped = svc.parse_csv(payload.csv)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    added, more_skipped = svc.add_recipients(db, campaign, rows)
    return {"added": added, "skipped": skipped + more_skipped}


@router.get("/{campaign_id}/recipients", response_model=list[CampaignRecipientOut])
def list_recipients(campaign_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    campaign = _owned(db, campaign_id, user_id)
    recipients = (db.query(CampaignRecipient).filter(CampaignRecipient.campaign_id == campaign.id)
                  .order_by(CampaignRecipient.id).all())
    emails = defaultdict(list)
    for e in (db.query(ScheduledEmail)
              .filter(ScheduledEmail.campaign_id == campaign.id, ScheduledEmail.campaign_recipient_id.isnot(None),
                      ScheduledEmail.status != "deleted")
              .order_by(ScheduledEmail.step)):
        emails[e.campaign_recipient_id].append(e)
    return [CampaignRecipientOut.model_validate(r).model_copy(update={"emails": emails[r.id]}) for r in recipients]


@router.delete("/{campaign_id}/recipients/{recipient_id}", status_code=204)
def remove_recipient(campaign_id: int, recipient_id: int, db: Session = Depends(get_db),
                     user_id: int = Depends(get_current_user_id)):
    campaign = _owned(db, campaign_id, user_id)
    svc.remove_recipient(db, _owned_recipient(db, campaign, recipient_id))


@router.post("/{campaign_id}/recipients/{recipient_id}/replied", response_model=CampaignRecipientOut)
def mark_replied(campaign_id: int, recipient_id: int, db: Session = Depends(get_db),
                 user_id: int = Depends(get_current_user_id)):
    """They answered — stop their follow-ups."""
    campaign = _owned(db, campaign_id, user_id)
    r = _owned_recipient(db, campaign, recipient_id)
    svc.mark_replied(db, r)
    db.refresh(r)
    return r


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/generate", response_model=CampaignOut)
def generate(campaign_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Queue personalised first emails for every recipient without one. Runs in the background."""
    campaign = _owned(db, campaign_id, user_id)
    _require_status(campaign, "draft")
    needed = (db.query(func.count(CampaignRecipient.id))
              .filter(CampaignRecipient.campaign_id == campaign.id, CampaignRecipient.status.in_(("new", "error")))
              .scalar())
    if not needed:
        raise HTTPException(status_code=400, detail="No recipients waiting for an email. Import a CSV first.")
    left = plans.remaining(db, user_id)
    if needed > left:
        plan = plans.get_plan(db, user_id)
        hint = " Upgrade to Pro in Settings, or remove some recipients." if plan.id == "free" else " Remove some recipients or wait for next month's reset."
        raise HTTPException(status_code=402, detail=f"This needs {needed} AI emails but you have {left} left this month "
                                                    f"on the {plan.name} plan.{hint}")
    svc.queue_generation(db, campaign)
    return _out(db, campaign)


@router.post("/{campaign_id}/launch", response_model=CampaignOut)
def launch(campaign_id: int, payload: CampaignLaunch, db: Session = Depends(get_db),
           user_id: int = Depends(get_current_user_id)):
    campaign = _owned(db, campaign_id, user_id)
    _require_status(campaign, "draft")
    if not db.query(MailboxCredential).filter(MailboxCredential.user_id == user_id).first():
        raise HTTPException(status_code=400, detail="Connect a Gmail account in Settings before launching.")
    counts = _stats(db, [campaign.id])[campaign.id]
    if counts.queued:
        raise HTTPException(status_code=400, detail="Emails are still being written. Launch when they're ready.")
    if not counts.ready:
        raise HTTPException(status_code=400, detail="No ready emails to send. Generate emails first.")
    if payload.followup_count and not plans.get_plan(db, user_id).followups:
        raise HTTPException(status_code=402, detail="Automatic follow-ups are a Pro feature. Upgrade in Settings, "
                                                    "or launch with no follow-ups.")
    campaign.send_interval_minutes = payload.send_interval_minutes
    campaign.followup_count = payload.followup_count
    campaign.followup_delay_days = payload.followup_delay_days
    svc.launch(db, campaign, payload.start_at or utcnow())
    return _out(db, campaign)


@router.post("/{campaign_id}/pause", response_model=CampaignOut)
def pause(campaign_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    campaign = _owned(db, campaign_id, user_id)
    _require_status(campaign, "running")
    svc.pause(db, campaign)
    return _out(db, campaign)


@router.post("/{campaign_id}/resume", response_model=CampaignOut)
def resume(campaign_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    campaign = _owned(db, campaign_id, user_id)
    _require_status(campaign, "paused")
    svc.resume(db, campaign)
    return _out(db, campaign)
