"""Admin commands. Run from the project root:

    python -m app.cli set-plan someone@example.com pro
    python -m app.cli show-user someone@example.com
"""

import argparse
import sys

from app.core import plans
from app.db.session import SessionLocal
from app.main import _migrate
from app.models.models import User, utcnow


def _user(db, email: str) -> User:
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user:
        sys.exit(f"No user with email {email}")
    return user


def set_plan(email: str, plan_id: str) -> None:
    if plan_id not in plans.PLANS:
        sys.exit(f"Unknown plan '{plan_id}'. Choose from: {', '.join(plans.PLANS)}")
    db = SessionLocal()
    try:
        user = _user(db, email)
        old = user.plan
        user.plan, user.plan_updated_at = plan_id, utcnow()
        db.commit()
        print(f"{user.email}: {old} -> {plan_id}")
    finally:
        db.close()


def show_user(email: str) -> None:
    db = SessionLocal()
    try:
        user = _user(db, email)
        plan = plans.plan_for(user)
        used = plans.ai_emails_used(db, user.id)
        print(f"{user.email}  plan={plan.id}  AI emails {plans.current_period()}: {used}/{plan.ai_emails_per_month}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("set-plan", help="Change a user's plan")
    p.add_argument("email")
    p.add_argument("plan", choices=list(plans.PLANS))
    s = sub.add_parser("show-user", help="Show a user's plan and usage")
    s.add_argument("email")
    args = parser.parse_args()

    _migrate()  # make sure the plan/usage columns exist
    if args.cmd == "set-plan":
        set_plan(args.email, args.plan)
    else:
        show_user(args.email)


if __name__ == "__main__":
    main()
