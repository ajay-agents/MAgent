from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    """Naive UTC timestamp — the DB stores all datetimes as naive UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(20), default="free")  # see app/core/plans.py
    plan_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    scheduled_emails: Mapped[list["ScheduledEmail"]] = relationship(back_populates="user")
    mailbox_credential: Mapped["MailboxCredential | None"] = relationship(back_populates="user", uselist=False)
    sender_profile: Mapped["SenderProfile | None"] = relationship(back_populates="user", uselist=False)


class ScheduledEmail(Base):
    """Stores both generated content and scheduling state in one table (MVP simplification)."""

    __tablename__ = "scheduled_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # generation fields
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    tone: Mapped[str] = mapped_column(String(50), nullable=False)
    length: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # token usage & cost tracking
    ai_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # scheduling fields
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # last manual edit

    # campaign membership — null for one-off emails from the builder
    campaign_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    campaign_recipient_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("campaign_recipients.id"), nullable=True, index=True)
    step: Mapped[int] = mapped_column(Integer, default=0)  # 0 = first email, 1.. = follow-ups
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # set when sent; follow-ups reply to it
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)  # draft | pending | sending | sent | failed | deleted
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="scheduled_emails")


class MailboxCredential(Base):
    __tablename__ = "mailbox_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    gmail_address: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), default="app_password")  # app_password | google
    # Fernet-encrypted App Password or Google refresh token, depending on provider.
    # The DB column keeps its original name so existing databases need no rebuild.
    encrypted_secret: Mapped[str] = mapped_column("encrypted_app_password", Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="mailbox_credential")


class SenderProfile(Base):
    """Facts about the sender that every generated email can draw on."""

    __tablename__ = "sender_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company: Mapped[str | None] = mapped_column(String(150), nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)  # what they offer / value proposition
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_address: Mapped[str | None] = mapped_column(String(300), nullable=True)  # CAN-SPAM footer
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="sender_profile")


class Campaign(Base):
    """One message, personalised for many recipients, with optional automatic follow-ups."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    tone: Mapped[str] = mapped_column(String(50), nullable=False)
    length: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)  # shared pitch, applies to every recipient
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | running | paused | completed

    send_interval_minutes: Mapped[int] = mapped_column(Integer, default=3)
    followup_count: Mapped[int] = mapped_column(Integer, default=0)
    followup_delay_days: Mapped[int] = mapped_column(Integer, default=3)

    launched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    recipients: Mapped[list["CampaignRecipient"]] = relationship(back_populates="campaign")


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"
    __table_args__ = (UniqueConstraint("campaign_id", "email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # per-person context from the CSV
    # new -> queued -> ready -> scheduled -> contacted -> completed
    # or: replied | failed | error (generation failed permanently)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    campaign: Mapped["Campaign"] = relationship(back_populates="recipients")


class UsageCounter(Base):
    """Per-user, per-calendar-month (UTC) usage that plan limits are checked against."""

    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("user_id", "period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    ai_emails: Mapped[int] = mapped_column(Integer, default=0)


class Suppression(Base):
    """Addresses a user must never email again (unsubscribed, or added by hand)."""

    __tablename__ = "suppressions"
    __table_args__ = (UniqueConstraint("user_id", "email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(20), nullable=False)  # unsubscribed | manual
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
