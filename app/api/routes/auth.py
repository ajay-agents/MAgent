from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.rate_limit import RateLimiter
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, UserLogin, Token, UserOut
from app.core.security import hash_password, verify_password, create_access_token, get_current_user_id

router = APIRouter(prefix="/api/auth", tags=["auth"])

auth_limiter = RateLimiter("auth", settings.rate_limit_auth_per_minute)


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(auth_limiter)])
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # concurrent signup with the same email
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(user)
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
