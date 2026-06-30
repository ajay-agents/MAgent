from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scheduled_emails: Mapped[list["ScheduledEmail"]] = relationship(back_populates="user")
    mailbox_credential: Mapped["MailboxCredential | None"] = relationship(back_populates="user", uselist=False)


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
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | pending | sent | failed

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="scheduled_emails")


class MailboxCredential(Base):
    __tablename__ = "mailbox_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    gmail_address: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_app_password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="mailbox_credential")
