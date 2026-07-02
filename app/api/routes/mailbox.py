from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.core.encryption import encrypt_password
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.models import MailboxCredential
from app.schemas.schemas import MailboxCredentialCreate, MailboxCredentialOut

router = APIRouter(prefix="/api/mailbox", tags=["mailbox"])


@router.post("", response_model=MailboxCredentialOut, status_code=201)
def save_mailbox_credential(
    payload: MailboxCredentialCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    encrypted = encrypt_password(payload.app_password, settings.fernet_key)
    cred = db.query(MailboxCredential).filter(MailboxCredential.user_id == user_id).first()
    if cred:
        cred.gmail_address = payload.gmail_address
        cred.encrypted_app_password = encrypted
    else:
        cred = MailboxCredential(
            user_id=user_id,
            gmail_address=payload.gmail_address,
            encrypted_app_password=encrypted,
        )
        db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


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
    db.delete(cred)
    db.commit()
