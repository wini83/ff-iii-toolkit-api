# services/user_secrets_service.py
from types import EllipsisType
from uuid import UUID

from services.db.models import UserSecretORM
from services.db.repository import AuditLogRepository, UserSecretRepository
from services.domain.user_secret_vault import EncryptedSecretBlob
from services.domain.user_secrets import (
    SecretType,
    UserSecretModel,
    UserSecretReadModel,
)
from services.exceptions import SecretDecryptionFailed, SecretNotAccessible
from services.mappers.user_secrets import (
    map_secret_to_domain_read_model,
    map_secrets_to_domain_read_models,
)
from services.secret_crypto_service import SecretCryptoService
from services.vault_service import VaultService


class UserSecretsService:
    """
    Application service for user-owned secrets.

    Plaintext secret material may leave this service only via
    `get_secret_for_internal_use(...)` and only with an active vault session.
    """

    def __init__(
        self,
        *,
        secret_repo: UserSecretRepository,
        audit_repo: AuditLogRepository,
        vault_service: VaultService,
        crypto_service: SecretCryptoService,
    ):
        self.secret_repo = secret_repo
        self.audit_repo = audit_repo
        self.vault_service = vault_service
        self.crypto_service = crypto_service

    # -------------------------------------------------
    # Internal helpers (policy layer)
    # -------------------------------------------------

    def _assert_ownership(self, *, secret: UserSecretORM, user_id: UUID) -> None:
        if secret.user_id != user_id:
            raise SecretNotAccessible("Secret not found")

    # -------------------------------------------------
    # Commands
    # -------------------------------------------------

    def create_secret(
        self,
        *,
        actor_id: UUID,
        user_id: UUID,
        vault_session_id: str | None,
        type: SecretType,
        alias: str | None,
        secret: str,
        external_username: str | None = None,
    ) -> UserSecretReadModel:
        """Create a secret by encrypting it with the active user vault key."""
        user_key = self.vault_service.require_user_key(user_id, vault_session_id)
        encrypted = self.crypto_service.encrypt_secret(secret, user_key)
        obj = self.secret_repo.create(
            user_id=user_id,
            type=type,
            alias=alias,
            external_username=external_username,
            ciphertext=encrypted.ciphertext,
            secret_nonce=encrypted.secret_nonce,
            wrapped_dek=encrypted.wrapped_dek,
            wrapped_dek_nonce=encrypted.wrapped_dek_nonce,
            crypto_version=encrypted.crypto_version,
        )

        self.audit_repo.log(
            actor_id=actor_id,
            action="user_secret.create",
            target_id=obj.id,
            metadata={
                "type": type.value,
                "alias": alias,
                "external_username": external_username,
            },
        )

        return map_secret_to_domain_read_model(obj=obj)

    def update_secret(
        self,
        *,
        actor_id: UUID,
        user_id: UUID,
        secret_id: UUID,
        vault_session_id: str | None = None,
        alias: str | None | object = ...,
        external_username: str | None | object = ...,
        secret: str | None | EllipsisType = ...,
    ) -> UserSecretReadModel:
        """Update metadata and optionally rotate encrypted secret material."""
        secret_obj = self.secret_repo.get_by_id(secret_id)
        if not secret_obj:
            raise SecretNotAccessible("Secret not found")

        self._assert_ownership(secret=secret_obj, user_id=user_id)

        metadata_changed = alias is not ... or external_username is not ...
        if metadata_changed:
            self.secret_repo.update_metadata(
                secret=secret_obj,
                alias=alias,
                external_username=external_username,
            )

        if isinstance(secret, str):
            user_key = self.vault_service.require_user_key(user_id, vault_session_id)
            encrypted = self.crypto_service.encrypt_secret(secret, user_key)
            self.secret_repo.update_encrypted_secret(
                secret=secret_obj,
                encrypted=encrypted,
            )

        self.audit_repo.log(
            actor_id=actor_id,
            action="user_secret.update",
            target_id=secret_id,
            metadata={
                "alias": None if alias is ... else alias,
                "external_username": (
                    None if external_username is ... else external_username
                ),
                "secret_rotated": isinstance(secret, str),
            },
        )
        return map_secret_to_domain_read_model(obj=secret_obj)

    def update_alias(
        self,
        *,
        actor_id: UUID,
        user_id: UUID,
        secret_id: UUID,
        alias: str | None,
    ) -> UserSecretReadModel:
        return self.update_secret(
            actor_id=actor_id,
            user_id=user_id,
            secret_id=secret_id,
            alias=alias,
        )

    def delete_secret(
        self,
        *,
        actor_id: UUID,
        user_id: UUID,
        secret_id: UUID,
    ) -> None:
        secret = self.secret_repo.get_by_id(secret_id)
        if not secret:
            raise SecretNotAccessible("Secret not found")

        self._assert_ownership(secret=secret, user_id=user_id)

        self.secret_repo.delete(secret=secret)

        self.audit_repo.log(
            actor_id=actor_id,
            action="user_secret.delete",
            target_id=secret_id,
        )

    # -------------------------------------------------
    # Queries (SAFE)
    # -------------------------------------------------

    def list_secrets(self, *, user_id: UUID) -> list[UserSecretReadModel]:
        """
        Query model SAFE BY DESIGN.
        Nigdy nie zwraca `secret`.
        """
        secrets = self.secret_repo.get_for_user(user_id=user_id)

        return map_secrets_to_domain_read_models(objs=secrets)

    # -------------------------------------------------
    # Internal usage (non-API)
    # -------------------------------------------------

    def get_secret_for_internal_use(
        self,
        *,
        secret_id: UUID,
        user_id: UUID,
        vault_session_id: str | None,
        usage_meta: dict | None = None,
    ) -> UserSecretModel:
        """
        The only supported plaintext access path.

        Use from backend integrations or application services, not directly from
        API routers.
        """
        secret_obj = self.secret_repo.get_by_id(secret_id)
        if not secret_obj:
            raise SecretNotAccessible("Secret not found")

        self._assert_ownership(secret=secret_obj, user_id=user_id)
        user_key = self.vault_service.require_user_key(user_id, vault_session_id)
        encrypted_blob = self._get_encrypted_blob(secret_obj)
        try:
            plaintext = self.crypto_service.decrypt_secret(encrypted_blob, user_key)
        except ValueError as exc:
            raise SecretDecryptionFailed("Secret decryption failed") from exc

        self.secret_repo.mark_used(
            secret=secret_obj,
            meta=usage_meta,
        )

        self.audit_repo.log(
            actor_id=secret_obj.user_id,
            action="user_secret.used",
            target_id=secret_obj.id,
            metadata=usage_meta,
        )

        read_model = map_secret_to_domain_read_model(obj=secret_obj)
        return UserSecretModel(
            id=read_model.id,
            type=read_model.type,
            alias=read_model.alias,
            external_username=read_model.external_username,
            usage_count=read_model.usage_count,
            last_used_at=read_model.last_used_at,
            created_at=read_model.created_at,
            secret=plaintext,
        )

    @staticmethod
    def _get_encrypted_blob(secret: UserSecretORM) -> EncryptedSecretBlob:
        if (
            secret.ciphertext is None
            or secret.secret_nonce is None
            or secret.wrapped_dek is None
            or secret.wrapped_dek_nonce is None
            or secret.crypto_version is None
        ):
            raise SecretDecryptionFailed("Secret decryption failed")
        return EncryptedSecretBlob(
            ciphertext=secret.ciphertext,
            secret_nonce=secret.secret_nonce,
            wrapped_dek=secret.wrapped_dek,
            wrapped_dek_nonce=secret.wrapped_dek_nonce,
            crypto_version=secret.crypto_version,
        )
