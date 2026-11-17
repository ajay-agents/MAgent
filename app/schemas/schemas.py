from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field, PlainSerializer, field_validator


# ── Datetimes ─────────────────────────────────────────────────────────────────
# The DB stores naive UTC. Incoming values are normalised to naive UTC (naive input
# is assumed to already be UTC); outgoing values are tagged with "Z" so browsers
# don't misread them as local time.

def _to_naive_utc(v: datetime) -> datetime:
    if v.tzinfo is not None:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


def _serialize_utc(v: datetime) -> str:
    return v.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, AfterValidator(_to_naive_utc), PlainSerializer(_serialize_utc, return_type=str)]

Purpose = Literal["cold_outreach", "follow_up", "job_application", "networking", "partnership", "thank_you"]
Tone    = Literal["professional", "friendly", "formal", "casual", "persuasive"]
Length  = Literal["short", "medium", "long"]

Name = Annotated[str, Field(min_length=1, max_length=100)]


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


# ── Mailbox credentials ───────────────────────────────────────────────────────

class MailboxCredentialCreate(BaseModel):
    gmail_address: EmailStr
    app_password: str  # 16-char Gmail App Password (spaces are stripped automatically)

    @field_validator("app_password")
    @classmethod
    def _normalise_app_password(cls, v: str) -> str:
        v = "".join(v.split())
        if len(v) != 16:
            raise ValueError("Gmail App Password must be 16 characters")
        return v


class MailboxCredentialOut(BaseModel):
    gmail_address: str
    provider: str = "app_password"  # app_password | google
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


# ── Email generation ──────────────────────────────────────────────────────────

class GenerateEmailRequest(BaseModel):
    purpose: Purpose
    tone: Tone
    length: Length
    sender_name: Name
    recipient_name: Name
    recipient_email: EmailStr
    context: str | None = Field(default=None, max_length=2000)


class GenerateEmailResponse(BaseModel):
    id: int
    subject: str
    body: str
    ai_model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class EmailUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, min_length=1, max_length=20000)


Refinement = Literal["shorter", "longer", "warmer", "more_direct", "more_formal"]


class RegenerateRequest(BaseModel):
    """No refinement/instruction = a fresh take from the original inputs; otherwise revise the current draft."""
    refinement: Refinement | None = None
    instruction: str | None = Field(default=None, max_length=500)


# ── Sender profile ────────────────────────────────────────────────────────────

class SenderProfileIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=100)
    company: str | None = Field(default=None, max_length=150)
    about: str | None = Field(default=None, max_length=1500)
    signature: str | None = Field(default=None, max_length=500)
    postal_address: str | None = Field(default=None, max_length=300)

    @field_validator("*")
    @classmethod
    def _blank_to_none(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class SenderProfileOut(SenderProfileIn):
    updated_at: UTCDateTime | None = None

    model_config = {"from_attributes": True}


# ── Scheduled email ───────────────────────────────────────────────────────────

class ScheduleEmailRequest(BaseModel):
    scheduled_at: UTCDateTime  # when the email should be sent (timezone-aware, or naive UTC)

    @field_validator("scheduled_at")
    @classmethod
    def _reasonable_time(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if v < now - timedelta(minutes=1):
            raise ValueError("Scheduled time must be in the future")
        if v > now + timedelta(days=365):
            raise ValueError("Scheduled time must be within the next year")
        return v


class ScheduledEmailOut(BaseModel):
    id: int
    purpose: str
    tone: str
    length: str
    sender_name: str
    recipient_name: str
    recipient_email: str
    subject: str
    body: str
    status: str                    # draft | pending | sending | sent | failed | deleted
    error_message: str | None = None
    scheduled_at: UTCDateTime | None
    sent_at: UTCDateTime | None
    deleted_at: UTCDateTime | None
    edited_at: UTCDateTime | None = None
    created_at: UTCDateTime
    ai_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None

    model_config = {"from_attributes": True}


class EmailListItem(BaseModel):
    id: int
    purpose: str
    tone: str
    length: str
    sender_name: str
    subject: str
    recipient_name: str
    recipient_email: str
    status: str
    error_message: str | None = None
    scheduled_at: UTCDateTime | None
    sent_at: UTCDateTime | None
    deleted_at: UTCDateTime | None
    created_at: UTCDateTime
    ai_model: str | None
    estimated_cost_usd: float | None

    model_config = {"from_attributes": True}


# ── Campaigns ─────────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    purpose: Purpose
    tone: Tone
    length: Length
    sender_name: Name
    context: str | None = Field(default=None, max_length=2000)


class CampaignLaunch(BaseModel):
    start_at: UTCDateTime | None = None  # default: now
    send_interval_minutes: int = Field(default=3, ge=1, le=240)
    followup_count: int = Field(default=0, ge=0, le=3)
    followup_delay_days: int = Field(default=3, ge=1, le=30)

    @field_validator("start_at")
    @classmethod
    def _not_in_past(cls, v):
        if v is not None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if v < now - timedelta(minutes=1):
                raise ValueError("Start time must be in the future")
            if v > now + timedelta(days=365):
                raise ValueError("Start time must be within the next year")
        return v


class CsvUpload(BaseModel):
    csv: str = Field(min_length=1, max_length=2_000_000)


class CampaignStats(BaseModel):
    recipients: int = 0
    new: int = 0
    queued: int = 0
    ready: int = 0
    scheduled: int = 0
    contacted: int = 0
    completed: int = 0
    replied: int = 0
    failed: int = 0
    error: int = 0
    unsubscribed: int = 0
    emails_sent: int = 0


class CampaignOut(BaseModel):
    id: int
    name: str
    purpose: str
    tone: str
    length: str
    sender_name: str
    context: str | None
    status: str
    send_interval_minutes: int
    followup_count: int
    followup_delay_days: int
    launched_at: UTCDateTime | None
    created_at: UTCDateTime
    stats: CampaignStats = CampaignStats()

    model_config = {"from_attributes": True}


class CampaignEmailSummary(BaseModel):
    id: int
    step: int
    subject: str
    status: str
    scheduled_at: UTCDateTime | None
    sent_at: UTCDateTime | None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class CampaignRecipientOut(BaseModel):
    id: int
    email: str
    name: str
    company: str | None
    notes: str | None
    status: str
    error_message: str | None
    replied_at: UTCDateTime | None
    emails: list[CampaignEmailSummary] = []

    model_config = {"from_attributes": True}
