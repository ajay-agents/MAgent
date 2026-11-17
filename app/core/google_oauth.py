"""Google OAuth (authorization-code flow) and sending through the Gmail API."""

import base64
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt

from app.config import settings
from app.core.smtp_sender import build_message

AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL    = "https://oauth2.googleapis.com/token"
REVOKE_URL   = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SEND_URL     = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
SCOPES = ["openid", "email", GMAIL_SEND_SCOPE]

_STATE_PURPOSE = "gmail_oauth"
_TIMEOUT = 20


class GoogleAuthError(Exception):
    """The refresh token was revoked or expired — the user must reconnect."""


class GoogleApiError(Exception):
    """Google returned an unexpected error (outage, quota, bad request)."""


# ── Authorization ─────────────────────────────────────────────────────────────

def make_state(user_id: int) -> str:
    """Signed, short-lived state tying the callback to the user who started the flow (CSRF protection)."""
    return jwt.encode(
        {"sub": str(user_id), "purpose": _STATE_PURPOSE, "nonce": secrets.token_urlsafe(8),
         "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )


def read_state(state: str) -> int:
    """Return the user id from a state value; raises jwt.PyJWTError/ValueError if invalid or expired."""
    payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
                         options={"require": ["exp", "sub", "purpose"]})
    if payload["purpose"] != _STATE_PURPOSE:
        raise ValueError("wrong state purpose")
    return int(payload["sub"])


def authorization_url(user_id: int) -> str:
    return AUTH_URL + "?" + urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",   # we need a refresh token to send scheduled emails later
        "prompt": "consent",        # Google only issues a refresh token on consent
        "include_granted_scopes": "true",
        "state": make_state(user_id),
    })


def exchange_code(code: str) -> dict:
    """Swap the callback code for tokens. Returns {'email', 'refresh_token', 'scopes'}."""
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.post(TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        })
        if r.status_code != 200:
            raise GoogleApiError(f"token exchange failed: {r.status_code} {r.text[:200]}")
        tokens = r.json()
        info = client.get(USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"})
        if info.status_code != 200:
            raise GoogleApiError(f"userinfo failed: {info.status_code}")
    return {
        "email": info.json().get("email", ""),
        "refresh_token": tokens.get("refresh_token"),
        "scopes": tokens.get("scope", "").split(),
        "access_token": tokens["access_token"],
        "expires_in": tokens.get("expires_in", 3600),
    }


def revoke(token: str) -> None:
    """Best effort — the user can also remove access at myaccount.google.com/permissions."""
    try:
        httpx.post(REVOKE_URL, data={"token": token}, timeout=_TIMEOUT)
    except httpx.HTTPError:
        pass


# ── Access tokens ─────────────────────────────────────────────────────────────

_token_cache: dict[str, tuple[str, float]] = {}  # refresh token -> (access token, expiry monotonic time)
_cache_lock = threading.Lock()


def cache_access_token(refresh_token: str, access_token: str, expires_in: int) -> None:
    with _cache_lock:
        _token_cache[refresh_token] = (access_token, time.monotonic() + expires_in - 60)


def _access_token(refresh_token: str) -> str:
    with _cache_lock:
        cached = _token_cache.get(refresh_token)
    if cached and cached[1] > time.monotonic():
        return cached[0]

    r = httpx.post(TOKEN_URL, data={
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=_TIMEOUT)
    if r.status_code in (400, 401) and _error_code(r) in ("invalid_grant", "unauthorized_client"):
        raise GoogleAuthError("refresh token revoked or expired")
    if r.status_code != 200:
        raise GoogleApiError(f"token refresh failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    cache_access_token(refresh_token, data["access_token"], data.get("expires_in", 3600))
    return data["access_token"]


def _error_code(r: httpx.Response) -> str:
    try:
        return r.json().get("error", "")
    except ValueError:
        return ""


def forget(refresh_token: str) -> None:
    with _cache_lock:
        _token_cache.pop(refresh_token, None)


# ── Sending ───────────────────────────────────────────────────────────────────

def send_via_gmail_api(refresh_token: str, from_address: str, to_email: str, subject: str, body: str,
                       message_id: str | None = None, in_reply_to: str | None = None,
                       extra_headers: dict[str, str] | None = None) -> None:
    msg = build_message(from_address, to_email, subject, body, message_id, in_reply_to, extra_headers)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    def post() -> httpx.Response:
        return httpx.post(SEND_URL, json={"raw": raw},
                          headers={"Authorization": f"Bearer {_access_token(refresh_token)}"}, timeout=_TIMEOUT)

    r = post()
    if r.status_code == 401:
        forget(refresh_token)  # cached access token expired or was revoked — refresh and try once more
        r = post()
    if r.status_code == 401:
        raise GoogleAuthError("access token rejected")
    if r.status_code == 403 and "insufficient" in r.text.lower():
        raise GoogleAuthError("gmail.send permission missing")
    if r.status_code >= 400:
        raise GoogleApiError(f"Gmail API send failed: {r.status_code} {r.text[:200]}")
