# services/db/models.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.db.types import GUID
from services.domain.user_secrets import SecretType


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
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    secrets: Mapped[list["UserSecretORM"]] = relationship(
        "UserSecretORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    secret_vault: Mapped["UserSecretVaultORM | None"] = relationship(
        "UserSecretVaultORM",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    password_set_tokens: Mapped[list["UserPasswordSetTokenORM"]] = relationship(
        "UserPasswordSetTokenORM",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserPasswordSetTokenORM.user_id",
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

    alias: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )

    external_username: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    secret: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    secret_nonce: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    wrapped_dek: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    wrapped_dek_nonce: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    crypto_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

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


class UserSecretVaultORM(Base):
    __tablename__ = "user_secret_vaults"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    kdf_salt: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    kdf_params_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    vault_check_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    vault_check_nonce: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
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
        back_populates="secret_vault",
    )


class UserPasswordSetTokenORM(Base):
    __tablename__ = "user_password_set_tokens"

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
    token_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    meta: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    user: Mapped["UserORM"] = relationship(
        "UserORM",
        back_populates="password_set_tokens",
        foreign_keys=[user_id],
    )
