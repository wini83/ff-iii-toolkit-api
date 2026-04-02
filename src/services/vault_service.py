from uuid import UUID

from services.db.models import UserSecretVaultORM
from services.db.repository import AuditLogRepository, UserSecretVaultRepository
from services.domain.user_secret_vault import VaultCheckBlob
from services.exceptions import (
    InvalidVaultPassphrase,
    VaultAlreadyConfigured,
    VaultLocked,
    VaultNotConfigured,
    VaultSessionExpired,
)
from services.secret_crypto_service import SecretCryptoService
from services.vault_session_store import VaultSessionStore


class VaultService:
    def __init__(
        self,
        *,
        vault_repo: UserSecretVaultRepository,
        session_store: VaultSessionStore,
        crypto_service: SecretCryptoService,
        audit_repo: AuditLogRepository | None = None,
        vault_session_ttl_seconds: int = 900,
    ) -> None:
        self.vault_repo = vault_repo
        self.session_store = session_store
        self.crypto_service = crypto_service
        self.audit_repo = audit_repo
        self.vault_session_ttl_seconds = vault_session_ttl_seconds

    def setup_vault(self, user_id: UUID, passphrase: str) -> None:
        existing = self.vault_repo.get_for_user(user_id)
        if existing is not None:
            raise VaultAlreadyConfigured("Vault already configured")

        derived_key = self.crypto_service.derive_user_key(passphrase)
        vault_check = self.crypto_service.create_vault_check(derived_key.key)

        self.vault_repo.create(
            user_id=user_id,
            kdf_salt=derived_key.salt,
            kdf_params_json=derived_key.params,
            vault_check_ciphertext=vault_check.ciphertext,
            vault_check_nonce=vault_check.nonce,
        )

        self._log(actor_id=user_id, action="vault.setup")
        self._commit()

    def unlock_vault(self, user_id: UUID, passphrase: str) -> str:
        vault = self._get_vault_or_raise(user_id)
        derived_key = self.crypto_service.derive_user_key(
            passphrase,
            vault.kdf_salt,
            params=self._get_kdf_params(vault),
        )
        vault_check = self._build_vault_check(vault)
        if not self.crypto_service.verify_vault_check(derived_key.key, vault_check):
            raise InvalidVaultPassphrase("Invalid vault passphrase")

        session_id = self.session_store.create(
            user_id,
            derived_key.key,
            ttl_seconds=self.vault_session_ttl_seconds,
        )
        self._log(actor_id=user_id, action="vault.unlock")
        self._commit()
        return session_id

    def lock_vault(self, user_id: UUID, vault_session_id: str) -> None:
        self.session_store.invalidate(user_id, vault_session_id)
        self._log(actor_id=user_id, action="vault.lock")
        self._commit()

    def is_configured(self, user_id: UUID) -> bool:
        return self.vault_repo.get_for_user(user_id) is not None

    def is_unlocked(self, user_id: UUID, vault_session_id: str | None) -> bool:
        if vault_session_id is None:
            return False
        return self.session_store.get_user_key(user_id, vault_session_id) is not None

    def require_user_key(self, user_id: UUID, vault_session_id: str | None) -> bytes:
        self._get_vault_or_raise(user_id)
        if vault_session_id is None:
            raise VaultLocked("Vault session missing")

        user_key = self.session_store.get_user_key(user_id, vault_session_id)
        if user_key is None:
            raise VaultSessionExpired("Vault session expired")
        return user_key

    def change_passphrase(
        self,
        user_id: UUID,
        current_passphrase: str,
        new_passphrase: str,
    ) -> None:
        raise NotImplementedError(
            "Vault passphrase change is not supported yet until secret rewrap is implemented"
        )

    def _get_vault_or_raise(self, user_id: UUID) -> UserSecretVaultORM:
        vault = self.vault_repo.get_for_user(user_id)
        if vault is None:
            raise VaultNotConfigured("Vault not configured")
        return vault

    @staticmethod
    def _build_vault_check(vault: UserSecretVaultORM) -> VaultCheckBlob:
        if vault.vault_check_ciphertext is None or vault.vault_check_nonce is None:
            raise VaultNotConfigured("Vault not configured")
        return VaultCheckBlob(
            ciphertext=vault.vault_check_ciphertext,
            nonce=vault.vault_check_nonce,
        )

    @staticmethod
    def _get_kdf_params(vault: UserSecretVaultORM) -> dict[str, int]:
        if vault.kdf_salt is None or vault.kdf_params_json is None:
            raise VaultNotConfigured("Vault not configured")
        return {key: int(value) for key, value in vault.kdf_params_json.items()}

    def _log(
        self,
        *,
        actor_id: UUID,
        action: str,
        target_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        if self.audit_repo is None:
            return
        self.audit_repo.log(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            metadata=metadata,
            commit=False,
        )

    def _commit(self) -> None:
        if self.audit_repo is not None:
            self.audit_repo.db.commit()
            return
        self.vault_repo.db.commit()
