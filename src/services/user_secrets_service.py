# services/user_secrets_service.py
from uuid import UUID

from services.db.models import UserSecretORM
from services.db.repository import AuditLogRepository, UserSecretRepository
from services.domain.user_secrets import (
    SecretType,
    UserSecretModel,
    UserSecretReadModel,
)
from services.mappers.user_secrets import (
    map_secret_to_domain_model,
    map_secret_to_domain_read_model,
    map_secrets_to_domain_read_models,
)


class UserSecretsService:
    def __init__(
        self,
        *,
        secret_repo: UserSecretRepository,
        audit_repo: AuditLogRepository,
    ):
        self.secret_repo = secret_repo
        self.audit_repo = audit_repo

    # -------------------------------------------------
    # Internal helpers (policy layer)
    # -------------------------------------------------

    def _assert_ownership(self, *, secret: UserSecretORM, user_id: UUID) -> None:
        if secret.user_id != user_id:
            raise ValueError("Secret not found")

    # -------------------------------------------------
    # Commands
    # -------------------------------------------------

    def create(
        self,
        *,
        actor_id: UUID,
        user_id: UUID,
        type: SecretType,
        secret: str,
    ) -> UserSecretReadModel:
        obj = self.secret_repo.create(
            user_id=user_id,
            type=type,
            secret=secret,
        )

        self.audit_repo.log(
            actor_id=actor_id,
            action="user_secret.create",
            target_id=obj.id,
            metadata={"type": type.value},
        )

        return map_secret_to_domain_read_model(obj=obj)

    def delete(
        self,
        *,
        actor_id: UUID,
        user_id: UUID,
        secret_id: UUID,
    ) -> None:
        secret = self.secret_repo.get_by_id(secret_id)
        if not secret:
            raise ValueError("Secret not found")

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

    def list_for_user(self, *, user_id: UUID) -> list[UserSecretReadModel]:
        """
        Query model SAFE BY DESIGN.
        Nigdy nie zwraca `secret`.
        """
        secrets = self.secret_repo.get_for_user(user_id=user_id)

        return map_secrets_to_domain_read_models(objs=secrets)

    # -------------------------------------------------
    # Internal usage (non-API)
    # -------------------------------------------------

    def get_for_internal_use(
        self,
        *,
        secret_id: UUID,
        user_id: UUID,
        usage_meta: dict | None = None,
    ) -> UserSecretModel:
        """
        Jedyna metoda, która zwraca `secret`.
        NIE dla routerów.
        """
        secret = self.secret_repo.get_by_id(secret_id)
        if not secret:
            raise ValueError("Secret not found")

        self._assert_ownership(secret=secret, user_id=user_id)

        self.secret_repo.mark_used(
            secret=secret,
            meta=usage_meta,
        )

        self.audit_repo.log(
            actor_id=secret.user_id,
            action="user_secret.used",
            target_id=secret.id,
            metadata=usage_meta,
        )

        return map_secret_to_domain_model(obj=secret)
