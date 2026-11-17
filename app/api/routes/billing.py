from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.core import plans
from app.core.delivery import sent_last_24h
from app.core.security import get_current_user_id
from app.db.session import get_db

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("")
def billing_overview(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Current plan, this month's usage, and what each plan includes (for the upgrade screen)."""
    plan = plans.get_plan(db, user_id)
    resets_at = plans.period_resets_at()
    return {
        "plan": plans.plan_dict(plan),
        "usage": {
            "period": plans.current_period(),
            "ai_emails": plans.ai_emails_used(db, user_id),
            "resets_at": resets_at.isoformat() + "Z",
            "emails_sent_24h": sent_last_24h(db, user_id),
            "daily_send_limit": settings.daily_send_limit,
        },
        "plans": [plans.plan_dict(p) for p in plans.PLANS.values()],
        # Online checkout isn't wired up yet; the UI shows the contact route instead
        "checkout_available": False,
        "support_email": settings.support_email or None,
    }
