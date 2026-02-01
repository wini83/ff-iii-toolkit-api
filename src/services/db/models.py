# services/db/models.py
import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .types import GUID


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    secrets: Mapped[list["UserSecretORM"]] = relationship(
        "UserSecretORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AuditLogORM(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    target_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        nullable=True,
    )

    meta: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class SecretType(str, Enum):
    ALLEGRO = "allegro"
    AMAZON = "amazon"
    SESSION = "session"
    API_TOKEN = "api_token"


class UserSecretORM(Base):
    __tablename__ = "user_secrets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[SecretType] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    secret: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # MVP: plaintext
    # next sprint: encrypt before persist

    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_used_meta: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    # np. {"source": "allegro-sync", "ip": "1.2.3.4"}

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["UserORM"] = relationship(
        "UserORM",
        back_populates="secrets",
    )
