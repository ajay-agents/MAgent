import logging

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core import account_tokens
from app.core.rate_limit import RateLimiter
from app.core.system_mail import send_system_email
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import (
    ChangePasswordIn,
    ForgotPasswordIn,
    ResetPasswordIn,
    Token,
    TokenIn,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.core.security import hash_password, verify_password, create_access_token, get_current_user_id

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("mailflow.auth")

auth_limiter = RateLimiter("auth", settings.rate_limit_auth_per_minute)
mail_limiter = RateLimiter("auth-mail", 5)  # requests that send an email


def _send_verification(user: User, background: BackgroundTasks) -> None:
    background.add_task(
        send_system_email, user.email, "Confirm your email for MailFlow AI",
        "Welcome to MailFlow AI!\n\n"
        f"Confirm your email address to start writing and sending emails:\n{account_tokens.verify_link(user)}\n\n"
        "The link works for 3 days. If you didn't sign up, you can ignore this email.",
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(auth_limiter)])
def signup(payload: UserCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, hashed_password=hash_password(payload.password), email_verified=False)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # concurrent signup with the same email
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(user)
    _send_verification(user, background)
    return user


@router.post("/login", response_model=Token, dependencies=[Depends(auth_limiter)])
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Email verification ────────────────────────────────────────────────────────

@router.post("/verify-email", response_model=UserOut, dependencies=[Depends(auth_limiter)])
def verify_email(payload: TokenIn, db: Session = Depends(get_db)):
    try:
        user_id, email = account_tokens.read_verify_token(payload.token)
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired. "
                                                    "Request a new one from the banner in the app.")
    user = db.get(User, user_id)
    if not user or user.email != email:
        raise HTTPException(status_code=400, detail="This verification link is no longer valid.")
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/resend-verification", status_code=202, dependencies=[Depends(mail_limiter)])
def resend_verification(background: BackgroundTasks, db: Session = Depends(get_db),
                        user_id: int = Depends(get_current_user_id)):
    user = db.get(User, user_id)
    if user and not user.email_verified:
        _send_verification(user, background)
    return {"detail": "Verification email sent."}


# ── Passwords ─────────────────────────────────────────────────────────────────

@router.post("/forgot-password", status_code=202, dependencies=[Depends(mail_limiter)])
def forgot_password(payload: ForgotPasswordIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user:
        background.add_task(
            send_system_email, user.email, "Reset your MailFlow AI password",
            f"Someone asked to reset the password for {user.email}.\n\n"
            f"Choose a new password here (the link works for 1 hour, once):\n{account_tokens.reset_link(user)}\n\n"
            "If this wasn't you, ignore this email. Your password won't change.",
        )
    # Same answer either way, so this can't be used to find out who has an account
    return {"detail": "If an account exists for that email, we've sent a reset link."}


@router.post("/reset-password", response_model=Token, dependencies=[Depends(auth_limiter)])
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    try:
        user = account_tokens.read_reset_token(payload.token, lambda uid: db.get(User, uid))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=400, detail="This reset link is invalid, expired or already used. "
                                                    "Request a new one.")
    user.hashed_password = hash_password(payload.password)
    user.email_verified = True  # they proved they can read mail at this address
    db.commit()
    logger.info("Password reset for user %s", user.id)
    return Token(access_token=create_access_token(user.id))


@router.post("/change-password", status_code=204, dependencies=[Depends(auth_limiter)])
def change_password(payload: ChangePasswordIn, db: Session = Depends(get_db),
                    user_id: int = Depends(get_current_user_id)):
    user = db.get(User, user_id)
    if not user or not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Your current password is incorrect.")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
