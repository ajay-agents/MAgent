from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.models import SenderProfile
from app.schemas.schemas import SenderProfileIn, SenderProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])

PROFILE_FIELDS = ("full_name", "role", "company", "about", "signature", "postal_address")


def load_profile(db: Session, user_id: int) -> dict | None:
    """The user's sender profile as a plain dict for prompt building, or None if not set up."""
    profile = db.query(SenderProfile).filter(SenderProfile.user_id == user_id).first()
    if not profile:
        return None
    return {f: getattr(profile, f) for f in PROFILE_FIELDS}


@router.get("", response_model=SenderProfileOut)
def get_profile(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile = db.query(SenderProfile).filter(SenderProfile.user_id == user_id).first()
    return profile or SenderProfileOut()


@router.put("", response_model=SenderProfileOut)
def save_profile(
    payload: SenderProfileIn,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    profile = db.query(SenderProfile).filter(SenderProfile.user_id == user_id).first()
    if not profile:
        profile = SenderProfile(user_id=user_id)
        db.add(profile)
    for field in PROFILE_FIELDS:
        setattr(profile, field, getattr(payload, field))
    db.commit()
    db.refresh(profile)
    return profile
