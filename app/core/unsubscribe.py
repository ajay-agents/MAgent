"""Unsubscribe links, the compliance footer, and each sender's do-not-contact (suppression) list."""

import jwt
from sqlalchemy import delete, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import CampaignRecipient, Campaign, ScheduledEmail, SenderProfile, Suppression

_PURPOSE = "unsubscribe"


# ── Signed links ──────────────────────────────────────────────────────────────

def make_token(user_id: int, email: str) -> str:
    # No expiry: an unsubscribe link must keep working for as long as the email exists
    return jwt.encode({"purpose": _PURPOSE, "u": user_id, "e": email.lower()},
                      settings.link_secret, algorithm=settings.jwt_algorithm)


def read_token(token: str) -> tuple[int, str]:
    """(user_id, email); raises jwt.PyJWTError/KeyError/ValueError if the token is invalid."""
    data = jwt.decode(token, settings.link_secret, algorithms=[settings.jwt_algorithm])
    if data.get("purpose") != _PURPOSE:
        raise ValueError("not an unsubscribe token")
    return int(data["u"]), str(data["e"])


def unsubscribe_url(user_id: int, email: str) -> str:
    return f"{settings.public_api_url.rstrip('/')}/u/{make_token(user_id, email)}"


def compliance_footer(db: Session, user_id: int, email: str) -> tuple[str, dict[str, str]]:
    """Text appended to campaign emails at send time, and the matching one-click unsubscribe headers."""
    url = unsubscribe_url(user_id, email)
    address = db.query(SenderProfile.postal_address).filter(SenderProfile.user_id == user_id).scalar()
    lines = ["", "--", f"Don't want emails from me? Unsubscribe: {url}"]
    if address:
        lines.append(address)
    headers = {
        "List-Unsubscribe": f"<{url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",  # RFC 8058, required by Gmail/Yahoo for bulk mail
    }
    return "\n".join(lines), headers


# ── Suppression list ──────────────────────────────────────────────────────────

def is_suppressed(db: Session, user_id: int, email: str) -> bool:
    return db.query(Suppression.id).filter(Suppression.user_id == user_id,
                                           func.lower(Suppression.email) == email.lower()).first() is not None


def suppressed_set(db: Session, user_id: int) -> set[str]:
    return {e.lower() for (e,) in db.query(Suppression.email).filter(Suppression.user_id == user_id)}


def suppress(db: Session, user_id: int, email: str, reason: str) -> None:
    """Add to the list and stop anything still queued to that address. Idempotent."""
    email = email.strip().lower()
    try:
        with db.begin_nested():
            db.add(Suppression(user_id=user_id, email=email, reason=reason))
    except IntegrityError:
        pass  # already on the list

    campaign_ids = [cid for (cid,) in db.query(Campaign.id).filter(Campaign.user_id == user_id)]
    if campaign_ids:
        recipient_ids = [rid for (rid,) in db.query(CampaignRecipient.id).filter(
            CampaignRecipient.campaign_id.in_(campaign_ids), func.lower(CampaignRecipient.email) == email)]
        if recipient_ids:
            db.execute(update(CampaignRecipient).where(CampaignRecipient.id.in_(recipient_ids))
                       .values(status="unsubscribed", error_message=None))
    # Unsent campaign emails are dropped; one-off drafts stay (the send-time check blocks them)
    db.execute(delete(ScheduledEmail).where(
        ScheduledEmail.user_id == user_id, func.lower(ScheduledEmail.recipient_email) == email,
        ScheduledEmail.campaign_id.isnot(None), ScheduledEmail.status.in_(("draft", "pending"))))
    db.commit()


def unsuppress(db: Session, user_id: int, email: str) -> bool:
    n = db.execute(delete(Suppression).where(Suppression.user_id == user_id,
                                             func.lower(Suppression.email) == email.strip().lower())).rowcount
    db.commit()
    return bool(n)
