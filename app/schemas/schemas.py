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
    ai_model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


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
    ai_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None

    model_config = {"from_attributes": True}
