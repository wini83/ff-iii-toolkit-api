# services/users/repository.py
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.db.models import AuditLogORM, SecretType, UserORM, UserSecretORM
from services.domain.user import User


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
    ) -> User:
        row = UserORM(
            username=username,
            password_hash=password_hash,
            is_superuser=is_superuser,
            is_active=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_domain(row)

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
    ) -> None:
        row = AuditLogORM(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            metadata=metadata,
        )
        self.db.add(row)
        self.db.commit()


class UserSecretRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        type: SecretType,
        secret: str,
    ) -> UserSecretORM:
        obj = UserSecretORM(
            user_id=user_id,
            type=type.value if hasattr(type, "value") else type,
            secret=secret,
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

    def delete(self, *, secret: UserSecretORM) -> None:
        self.db.delete(secret)
        self.db.flush()
