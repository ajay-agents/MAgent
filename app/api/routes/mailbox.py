import logging
import smtplib
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core import google_oauth
from app.core.encryption import decrypt_password, encrypt_password
from app.core.security import get_current_user_id
from app.core.smtp_sender import verify_login
from app.db.session import get_db
from app.models.models import MailboxCredential
from app.schemas.schemas import MailboxCredentialCreate, MailboxCredentialOut

router = APIRouter(prefix="/api/mailbox", tags=["mailbox"])

logger = logging.getLogger("mailflow.mailbox")


def _upsert_credential(db: Session, user_id: int, gmail_address: str, provider: str, secret: str) -> MailboxCredential:
    """Store the user's single sending account, replacing any previous one (and revoking an old Google grant)."""
    cred = db.query(MailboxCredential).filter(MailboxCredential.user_id == user_id).first()
    if cred and cred.provider == "google":
        old_token = decrypt_password(cred.encrypted_secret, settings.fernet_key)
        if old_token != secret:
            google_oauth.forget(old_token)
            google_oauth.revoke(old_token)
    if not cred:
        cred = MailboxCredential(user_id=user_id)
        db.add(cred)
    cred.gmail_address = gmail_address
    cred.provider = provider
    cred.encrypted_secret = encrypt_password(secret, settings.fernet_key)
    db.commit()
    db.refresh(cred)
    return cred


@router.get("/options")
def mailbox_options():
    """Which ways of connecting Gmail this deployment supports."""
    return {"google_oauth": settings.google_oauth_enabled, "app_password": True}


# ── App Password ──────────────────────────────────────────────────────────────

@router.post("", response_model=MailboxCredentialOut, status_code=201)
def save_mailbox_credential(
    payload: MailboxCredentialCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        verify_login(payload.gmail_address, payload.app_password)
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=400,
            detail="Gmail rejected these credentials. Use a 16-character App Password, not your normal password.",
        )
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Could not verify Gmail credentials: %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=502, detail="Could not reach Gmail to verify the credentials. Please try again.")

    return _upsert_credential(db, user_id, payload.gmail_address, "app_password", payload.app_password)


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google/authorize")
def google_authorize(user_id: int = Depends(get_current_user_id)):
    """URL of Google's consent screen. The frontend navigates the browser there."""
    if not settings.google_oauth_enabled:
        raise HTTPException(status_code=404, detail="Google sign-in is not configured on this server.")
    return {"url": google_oauth.authorization_url(user_id)}


def _back_to_settings(**params) -> RedirectResponse:
    return RedirectResponse(f"{settings.frontend_url}/settings?{urlencode(params)}", status_code=302)


@router.get("/google/callback", include_in_schema=False)
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    # Google redirects the browser here, so there's no bearer token: the signed state identifies the user
    if error:  # e.g. the user clicked Cancel on the consent screen
        return _back_to_settings(gmail="error", reason="denied" if error == "access_denied" else "google")
    if not code or not state or not settings.google_oauth_enabled:
        return _back_to_settings(gmail="error", reason="invalid")
    try:
        user_id = google_oauth.read_state(state)
    except (jwt.PyJWTError, ValueError):
        return _back_to_settings(gmail="error", reason="expired")

    try:
        result = google_oauth.exchange_code(code)
    except (google_oauth.GoogleApiError, OSError) as exc:
        logger.warning("Google token exchange failed: %s", exc)
        return _back_to_settings(gmail="error", reason="google")

    # The consent screen lets users untick individual permissions
    if google_oauth.GMAIL_SEND_SCOPE not in result["scopes"]:
        google_oauth.revoke(result["access_token"])
        return _back_to_settings(gmail="error", reason="scope")
    if not result["refresh_token"] or not result["email"]:
        return _back_to_settings(gmail="error", reason="google")

    _upsert_credential(db, user_id, result["email"], "google", result["refresh_token"])
    google_oauth.cache_access_token(result["refresh_token"], result["access_token"], result["expires_in"])
    logger.info("User %s connected Gmail via Google OAuth", user_id)
    return _back_to_settings(gmail="connected")


# ── Read / remove ─────────────────────────────────────────────────────────────

@router.get("", response_model=MailboxCredentialOut)
def get_mailbox_credential(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    cred = db.query(MailboxCredential).filter(MailboxCredential.user_id == user_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="No mailbox credential configured")
    return cred


@router.delete("", status_code=204)
def delete_mailbox_credential(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    cred = db.query(MailboxCredential).filter(MailboxCredential.user_id == user_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="No mailbox credential configured")
    if cred.provider == "google":
        token = decrypt_password(cred.encrypted_secret, settings.fernet_key)
        google_oauth.forget(token)
        google_oauth.revoke(token)  # also removes MailFlow from the user's Google account permissions
    db.delete(cred)
    db.commit()
