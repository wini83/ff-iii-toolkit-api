# services/users/repository.py
from uuid import UUID

from sqlalchemy.orm import Session

from services.db.models import UserORM
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

    def disable(self, user_id: UUID) -> None:
        row = self.db.query(UserORM).filter(UserORM.id == user_id).one()
        row.is_active = False
        self.db.commit()

    @staticmethod
    def _to_domain(row: UserORM) -> User:
        return User(
            id=row.id,
            username=row.username,
            password_hash=row.password_hash,
            is_superuser=row.is_superuser,
            is_active=row.is_active,
        )
