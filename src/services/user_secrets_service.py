# services/user_secrets_service.py
from uuid import UUID

from api.models.user_secrets import SecretTypeAPI
from services.db.models import SecretType, UserSecretORM
from services.db.repository import AuditLogRepository, UserSecretRepository

SECRET_TYPE_MAP: dict[SecretTypeAPI, SecretType] = {
    SecretTypeAPI.ALLEGRO: SecretType.ALLEGRO,
    SecretTypeAPI.AMAZON: SecretType.AMAZON,
}


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

    def _map_type_api_to_db(self, api_type: SecretTypeAPI) -> SecretType:
        """
        Jedyna dozwolona translacja API -> DB.
        """
        try:
            return SecretType(api_type.value)
        except ValueError:
            raise ValueError(f"Unsupported secret type: {api_type}") from None

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
        type: SecretTypeAPI,
        secret: str,
    ) -> UserSecretORM:
        db_type = self._map_type_api_to_db(type)

        obj = self.secret_repo.create(
            user_id=user_id,
            type=db_type,
            secret=secret,
        )

        self.audit_repo.log(
            actor_id=actor_id,
            action="user_secret.create",
            target_id=obj.id,
            metadata={"type": db_type.value},
        )

        return obj

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

    def list_for_user(self, *, user_id: UUID) -> list[dict]:
        """
        Query model SAFE BY DESIGN.
        Nigdy nie zwraca `secret`.
        """
        secrets = self.secret_repo.get_for_user(user_id=user_id)

        return [
            {
                "id": s.id,
                "type": s.type,
                "usage_count": s.usage_count,
                "last_used_at": s.last_used_at,
                "created_at": s.created_at,
            }
            for s in secrets
        ]

    # -------------------------------------------------
    # Internal usage (non-API)
    # -------------------------------------------------

    def get_for_internal_use(
        self,
        *,
        secret_id: UUID,
        usage_meta: dict | None = None,
    ) -> UserSecretORM:
        """
        Jedyna metoda, która zwraca `secret`.
        NIE dla routerów.
        """
        secret = self.secret_repo.get_by_id(secret_id)
        if not secret:
            raise ValueError("Secret not found")

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

        return secret
