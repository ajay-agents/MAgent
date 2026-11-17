"""Plan definitions and monthly usage metering.

Change limits here. A payment provider (added later) only needs to set `User.plan`.
"""

from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import UsageCounter, User, utcnow


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_label: str
    ai_emails_per_month: int    # every AI write counts: generate, rewrite/refine, campaign emails, follow-ups
    campaign_recipients: int    # max recipients per campaign
    followups: bool             # automatic campaign follow-ups


PLANS = {
    "free": Plan("free", "Free", "Free", ai_emails_per_month=50, campaign_recipients=25, followups=False),
    "pro":  Plan("pro", "Pro", "$19 / month", ai_emails_per_month=2000, campaign_recipients=500, followups=True),
}
DEFAULT_PLAN = "free"


class QuotaExceeded(Exception):
    pass


def plan_for(user: User | None) -> Plan:
    return PLANS.get(user.plan if user else DEFAULT_PLAN, PLANS[DEFAULT_PLAN])


def get_plan(db: Session, user_id: int) -> Plan:
    return plan_for(db.get(User, user_id))


# ── Monthly AI email counter ──────────────────────────────────────────────────

def current_period(now: datetime | None = None) -> str:
    return (now or utcnow()).strftime("%Y-%m")


def period_resets_at(now: datetime | None = None) -> datetime:
    now = now or utcnow()
    return datetime(now.year + (now.month == 12), now.month % 12 + 1, 1)


def _ensure_counter(db: Session, user_id: int, period: str) -> None:
    if db.query(UsageCounter.id).filter_by(user_id=user_id, period=period).first():
        return
    try:
        with db.begin_nested():
            db.add(UsageCounter(user_id=user_id, period=period, ai_emails=0))
    except IntegrityError:
        pass  # created concurrently


def ai_emails_used(db: Session, user_id: int) -> int:
    row = db.query(UsageCounter.ai_emails).filter_by(user_id=user_id, period=current_period()).first()
    return row[0] if row else 0


def remaining(db: Session, user_id: int) -> int:
    return max(get_plan(db, user_id).ai_emails_per_month - ai_emails_used(db, user_id), 0)


def reserve_ai_email(db: Session, user_id: int) -> None:
    """Atomically count one AI email against this month's quota, or raise QuotaExceeded.

    Reserve before calling the AI and `release_ai_email` if the call fails, so concurrent
    requests can never push a user past their limit.
    """
    period = current_period()
    limit = get_plan(db, user_id).ai_emails_per_month
    _ensure_counter(db, user_id, period)
    took = db.execute(
        update(UsageCounter)
        .where(UsageCounter.user_id == user_id, UsageCounter.period == period, UsageCounter.ai_emails < limit)
        .values(ai_emails=UsageCounter.ai_emails + 1)
    ).rowcount
    db.commit()
    if not took:
        raise QuotaExceeded(quota_message(db, user_id))


def release_ai_email(db: Session, user_id: int) -> None:
    db.execute(
        update(UsageCounter)
        .where(UsageCounter.user_id == user_id, UsageCounter.period == current_period(), UsageCounter.ai_emails > 0)
        .values(ai_emails=UsageCounter.ai_emails - 1)
    )
    db.commit()


def quota_message(db: Session, user_id: int) -> str:
    plan = get_plan(db, user_id)
    r = period_resets_at()
    resets = f"{r.day} {r:%b}"  # not %-d: unsupported on Windows
    msg = f"You've used all {plan.ai_emails_per_month} AI emails included in the {plan.name} plan this month. It resets on {resets}."
    if plan.id == "free":
        msg += " Upgrade to Pro in Settings for more."
    return msg


def plan_dict(plan: Plan) -> dict:
    return asdict(plan)


def metered_ai_call(db: Session, user_id: int, fn):
    """Run one AI generation against the user's quota; the unit is refunded if the call fails."""
    reserve_ai_email(db, user_id)
    try:
        return fn()
    except BaseException:
        release_ai_email(db, user_id)
        raise
