import html
import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core import unsubscribe as unsub
from app.core.rate_limit import RateLimiter
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.models import MailboxCredential, SenderProfile, Suppression

logger = logging.getLogger("mailflow.unsubscribe")

# ── Public pages reached from links in sent emails (no login) ────────────────

public = APIRouter(include_in_schema=False)
page_limiter = RateLimiter("unsubscribe", 30)


def _sender_label(db: Session, user_id: int) -> str:
    p = db.query(SenderProfile).filter(SenderProfile.user_id == user_id).first()
    if p and p.full_name:
        return f"{p.full_name}{f' ({p.company})' if p.company else ''}"
    gmail = db.query(MailboxCredential.gmail_address).filter(MailboxCredential.user_id == user_id).scalar()
    return gmail or "this sender"


def _page(title: str, body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(status_code=status, content=f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#f9fafb; --card:#fff; --text:#111827; --muted:#6b7280; --border:#e5e7eb; --btn:#111827; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#090B12; --card:#11141D; --text:#f9fafb; --muted:#9ca3af; --border:#1f2937; --btn:#6366f1; }} }}
  body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:var(--bg); color:var(--text);
         font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; padding:16px; box-sizing:border-box; }}
  .card {{ box-sizing:border-box; background:var(--card); border:1px solid var(--border); border-radius:20px; padding:32px; max-width:440px; width:100%; }}
  h1 {{ font-size:22px; margin:0 0 8px; }} p {{ color:var(--muted); margin:0 0 20px; }}
  button {{ background:var(--btn); color:#fff; border:0; border-radius:12px; padding:12px 20px; font-size:16px; cursor:pointer; width:100%; }}
</style></head><body><main class="card">{body}</main></body></html>""")


def _decode(token: str) -> tuple[int, str]:
    try:
        return unsub.read_token(token)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=404)


@public.get("/u/{token}", response_class=HTMLResponse, dependencies=[Depends(page_limiter)])
def unsubscribe_page(token: str, db: Session = Depends(get_db)):
    # GET only shows a confirmation: mail security scanners pre-open links, and must not unsubscribe people
    try:
        user_id, email = _decode(token)
    except HTTPException:
        return _page("Link not valid", "<h1>This link isn't valid</h1><p>It may have been copied incompletely.</p>", 404)
    sender = html.escape(_sender_label(db, user_id))
    if unsub.is_suppressed(db, user_id, email):
        return _page("Unsubscribed", f"<h1>You're already unsubscribed</h1><p>{html.escape(email)} won't receive more emails from {sender}.</p>")
    return _page("Unsubscribe", f"""<h1>Unsubscribe?</h1>
<p>Stop emails from <b>{sender}</b> to {html.escape(email)}.</p>
<form method="post"><button type="submit">Unsubscribe</button></form>""")


@public.post("/u/{token}", response_class=HTMLResponse, dependencies=[Depends(page_limiter)])
async def unsubscribe_confirm(token: str, request: Request, db: Session = Depends(get_db)):
    # Handles both our confirmation form and RFC 8058 one-click POSTs sent by Gmail/Yahoo/Apple Mail
    try:
        user_id, email = _decode(token)
    except HTTPException:
        return _page("Link not valid", "<h1>This link isn't valid</h1>", 404)
    unsub.suppress(db, user_id, email, "unsubscribed")
    logger.info("Recipient unsubscribed from user %s", user_id)
    sender = html.escape(_sender_label(db, user_id))
    return _page("Unsubscribed", f"<h1>You're unsubscribed</h1><p>{html.escape(email)} won't receive more emails from {sender}.</p>")


# ── The user's do-not-contact list ────────────────────────────────────────────

router = APIRouter(prefix="/api/suppressions", tags=["suppressions"])


class SuppressionIn(BaseModel):
    email: EmailStr


class SuppressionOut(BaseModel):
    email: str
    reason: str
    created_at: str


@router.get("", response_model=list[SuppressionOut])
def list_suppressions(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rows = db.query(Suppression).filter(Suppression.user_id == user_id).order_by(Suppression.created_at.desc()).all()
    return [SuppressionOut(email=r.email, reason=r.reason, created_at=r.created_at.isoformat() + "Z") for r in rows]


@router.post("", status_code=201)
def add_suppression(payload: SuppressionIn, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    unsub.suppress(db, user_id, str(payload.email), "manual")
    return {"email": str(payload.email).lower()}


@router.delete("/{email}", status_code=204)
def remove_suppression(email: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Only for addresses you added by hand, or someone who asked to hear from you again."""
    if not unsub.unsuppress(db, user_id, email):
        raise HTTPException(status_code=404, detail="Not on your do-not-contact list")
