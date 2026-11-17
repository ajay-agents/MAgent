"""Signed, single-purpose links for email verification and password reset."""

from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.models.models import User

VERIFY_TTL = timedelta(days=3)
RESET_TTL = timedelta(hours=1)


def _encode(payload: dict, ttl: timedelta) -> str:
    return jwt.encode({**payload, "exp": datetime.now(timezone.utc) + ttl}, settings.jwt_secret,
                      algorithm=settings.jwt_algorithm)


def _decode(token: str, purpose: str) -> dict:
    data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
                      options={"require": ["exp", "purpose", "sub"]})
    if data["purpose"] != purpose:
        raise ValueError("wrong token purpose")
    return data


def _password_fingerprint(user: User) -> str:
    # Changes whenever the password does, so a reset link stops working once it has been used
    return user.hashed_password[-12:]


def make_verify_token(user: User) -> str:
    return _encode({"purpose": "verify", "sub": str(user.id), "email": user.email}, VERIFY_TTL)


def read_verify_token(token: str) -> tuple[int, str]:
    data = _decode(token, "verify")
    return int(data["sub"]), data["email"]


def make_reset_token(user: User) -> str:
    return _encode({"purpose": "reset", "sub": str(user.id), "pw": _password_fingerprint(user)}, RESET_TTL)


def read_reset_token(token: str, load_user) -> User:
    """`load_user(id)` returns the User or None. Raises ValueError/jwt.PyJWTError if invalid or already used."""
    data = _decode(token, "reset")
    user = load_user(int(data["sub"]))
    if not user or data.get("pw") != _password_fingerprint(user):
        raise ValueError("reset link already used or account changed")
    return user


def verify_link(user: User) -> str:
    return f"{settings.frontend_url.rstrip('/')}/verify-email?token={make_verify_token(user)}"


def reset_link(user: User) -> str:
    return f"{settings.frontend_url.rstrip('/')}/reset-password?token={make_reset_token(user)}"
