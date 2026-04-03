# services/users/repository.py
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.db.models import (
    AuditLogORM,
    SecretType,
    UserORM,
    UserPasswordSetTokenORM,
    UserSecretORM,
    UserSecretVaultORM,
)
from services.domain.password_set_token import PasswordSetToken
from services.domain.user import User
from services.domain.user_secret_vault import EncryptedSecretBlob


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        row = self.db.query(UserORM).filter(UserORM.username == username).one_or_none()
        return self._to_domain(row) if row else None

    def get_by_id(self, user_id: UUID) -> User | None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one_or_none()
        return self._to_domain(row) if row else None

    def count_users(self) -> int:
        return self.db.query(UserORM).count()

    def list_all(self) -> list[User]:
        rows = self.db.query(UserORM).all()
        return [self._to_domain(r) for r in rows]

    def create(
        self,
        username: str,
        password_hash: str,
        *,
        is_superuser: bool = False,
        must_change_password: bool = False,
        password_changed_at: datetime | None = None,
        commit: bool = True,
    ) -> User:
        if password_changed_at is None and not must_change_password:
            password_changed_at = datetime.now(UTC)
        row = UserORM(
            username=username,
            password_hash=password_hash,
            is_superuser=is_superuser,
            is_active=True,
            must_change_password=must_change_password,
            password_changed_at=password_changed_at,
        )
        self.db.add(row)
        if commit:
            self.db.commit()
            self.db.refresh(row)
        else:
            self.db.flush()
        return self._to_domain(row)

    def set_password(
        self,
        user_id: UUID,
        *,
        password_hash: str,
        must_change_password: bool,
        password_changed_at: datetime,
        commit: bool = True,
    ) -> None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one()
        row.password_hash = password_hash
        row.must_change_password = must_change_password
        row.password_changed_at = password_changed_at
        if commit:
            self.db.commit()
        else:
            self.db.flush()

    def mark_password_reset_required(
        self,
        user_id: UUID,
        *,
        password_hash: str,
        commit: bool = True,
    ) -> None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one()
        row.password_hash = password_hash
        row.must_change_password = True
        row.password_changed_at = None
        if commit:
            self.db.commit()
        else:
            self.db.flush()

    def promote_to_superuser(self, user_id: UUID) -> None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one()
        row.is_superuser = True
        self.db.commit()

    def demote_from_superuser(self, user_id: UUID) -> None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one()
        row.is_superuser = False
        self.db.commit()

    def disable(self, user_id: UUID) -> None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one()
        row.is_active = False
        self.db.commit()

    def enable(self, user_id: UUID) -> None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one()
        row.is_active = True
        self.db.commit()

    def delete(self, user_id: UUID) -> None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one()
        self.db.delete(row)
        self.db.commit()

    def is_superuser(self, user_id: UUID) -> bool:
        return (
            self.db.query(UserORM)
            .filter(
                UserORM.id == user_id,
                UserORM.is_superuser.is_(True),
                UserORM.is_active.is_(True),
            )
            .count()
            > 0
        )

    @staticmethod
    def _to_domain(row: UserORM) -> User:
        return User(
            id=row.id,
            username=row.username,
            password_hash=row.password_hash,
            is_superuser=row.is_superuser,
            is_active=row.is_active,
            must_change_password=row.must_change_password,
            password_changed_at=row.password_changed_at,
        )


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        *,
        actor_id: UUID,
        action: str,
        target_id: UUID | None = None,
        metadata: dict | None = None,
        commit: bool = True,
    ) -> None:
        row = AuditLogORM(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            meta=metadata,
        )
        self.db.add(row)
        if commit:
            self.db.commit()
        else:
            self.db.flush()


class UserSecretRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        type: SecretType,
        alias: str | None,
        external_username: str | None = None,
        ciphertext: bytes | None = None,
        secret_nonce: bytes | None = None,
        wrapped_dek: bytes | None = None,
        wrapped_dek_nonce: bytes | None = None,
        crypto_version: int | None = None,
    ) -> UserSecretORM:
        obj = UserSecretORM(
            user_id=user_id,
            type=type.value if hasattr(type, "value") else type,
            alias=alias,
            external_username=external_username,
            ciphertext=ciphertext,
            secret_nonce=secret_nonce,
            wrapped_dek=wrapped_dek,
            wrapped_dek_nonce=wrapped_dek_nonce,
            crypto_version=crypto_version,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_by_id(self, secret_id: UUID) -> UserSecretORM | None:
        return self.db.get(UserSecretORM, secret_id)

    def get_for_user(
        self,
        *,
        user_id: UUID,
        type: SecretType | None = None,
    ) -> list[UserSecretORM]:
        stmt = select(UserSecretORM).where(UserSecretORM.user_id == user_id)
        if type:
            stmt = stmt.where(
                UserSecretORM.type == (type.value if hasattr(type, "value") else type)
            )
        return list(self.db.scalars(stmt))

    def mark_used(self, *, secret: UserSecretORM, meta: dict | None = None) -> None:
        secret.usage_count += 1
        secret.last_used_at = datetime.now(UTC)
        if meta is not None:
            secret.last_used_meta = meta
        self.db.flush()

    def update_alias(
        self,
        *,
        secret: UserSecretORM,
        alias: str | None,
    ) -> UserSecretORM:
        secret.alias = alias
        self.db.flush()
        return secret

    def update_metadata(
        self,
        *,
        secret: UserSecretORM,
        alias: str | None | object = ...,
        external_username: str | None | object = ...,
    ) -> UserSecretORM:
        if alias is not ...:
            secret.alias = alias
        if external_username is not ...:
            secret.external_username = external_username
        self.db.flush()
        return secret

    def update_encrypted_secret(
        self,
        *,
        secret: UserSecretORM,
        encrypted: EncryptedSecretBlob,
    ) -> UserSecretORM:
        secret.ciphertext = encrypted.ciphertext
        secret.secret_nonce = encrypted.secret_nonce
        secret.wrapped_dek = encrypted.wrapped_dek
        secret.wrapped_dek_nonce = encrypted.wrapped_dek_nonce
        secret.crypto_version = encrypted.crypto_version
        self.db.flush()
        return secret

    def delete(self, *, secret: UserSecretORM) -> None:
        self.db.delete(secret)
        self.db.flush()


class UserSecretVaultRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: UUID) -> UserSecretVaultORM | None:
        return self.db.get(UserSecretVaultORM, user_id)

    def create(
        self,
        *,
        user_id: UUID,
        kdf_salt: bytes,
        kdf_params_json: dict[str, int],
        vault_check_ciphertext: bytes,
        vault_check_nonce: bytes,
    ) -> UserSecretVaultORM:
        obj = UserSecretVaultORM(
            user_id=user_id,
            kdf_salt=kdf_salt,
            kdf_params_json=kdf_params_json,
            vault_check_ciphertext=vault_check_ciphertext,
            vault_check_nonce=vault_check_nonce,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(
        self,
        *,
        vault: UserSecretVaultORM,
        kdf_salt: bytes,
        kdf_params_json: dict[str, int],
        vault_check_ciphertext: bytes,
        vault_check_nonce: bytes,
    ) -> UserSecretVaultORM:
        vault.kdf_salt = kdf_salt
        vault.kdf_params_json = kdf_params_json
        vault.vault_check_ciphertext = vault_check_ciphertext
        vault.vault_check_nonce = vault_check_nonce
        self.db.flush()
        return vault


class PasswordSetTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        created_by: UUID | None = None,
        meta: dict | None = None,
        commit: bool = True,
    ) -> PasswordSetToken:
        row = UserPasswordSetTokenORM(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_by=created_by,
            meta=meta,
        )
        self.db.add(row)
        if commit:
            self.db.commit()
            self.db.refresh(row)
        else:
            self.db.flush()
        return self._to_domain(row)

    def get_by_hash(self, token_hash: str) -> PasswordSetToken | None:
        row = (
            self.db.query(UserPasswordSetTokenORM)
            .filter(UserPasswordSetTokenORM.token_hash == token_hash)
            .one_or_none()
        )
        return self._to_domain(row) if row else None

    def invalidate_previous(
        self,
        *,
        user_id: UUID,
        invalidated_at: datetime,
        commit: bool = True,
    ) -> int:
        rows = (
            self.db.query(UserPasswordSetTokenORM)
            .filter(
                UserPasswordSetTokenORM.user_id == user_id,
                UserPasswordSetTokenORM.used_at.is_(None),
            )
            .all()
        )
        for row in rows:
            row.used_at = invalidated_at
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return len(rows)

    def consume(
        self,
        *,
        token_id: UUID,
        used_at: datetime,
        commit: bool = True,
    ) -> None:
        row = self.db.query(UserPasswordSetTokenORM).filter_by(id=token_id).one()
        row.used_at = used_at
        if commit:
            self.db.commit()
        else:
            self.db.flush()

    @staticmethod
    def _to_domain(row: UserPasswordSetTokenORM) -> PasswordSetToken:
        return PasswordSetToken(
            id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            expires_at=row.expires_at,
            used_at=row.used_at,
            created_at=row.created_at,
            created_by=row.created_by,
            meta=row.meta,
        )
