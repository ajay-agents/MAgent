from datetime import datetime
from pydantic import BaseModel, EmailStr


# Auth
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# Email generation
class GenerateEmailRequest(BaseModel):
    purpose: str  # cold_outreach | follow_up | job_application | networking | partnership | thank_you
    tone: str     # professional | friendly | formal | casual | persuasive
    length: str   # short | medium | long
    sender_name: str
    recipient_name: str
    recipient_email: str
    context: str | None = None


class GenerateEmailResponse(BaseModel):
    subject: str
    body: str


# Scheduled email
class ScheduledEmailOut(BaseModel):
    id: int
    purpose: str
    subject: str
    body: str
    recipient_email: str
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
