# api/deps_user_secrets.py
from fastapi import Depends
from sqlalchemy.orm import Session

from api.deps_db import get_db
from services.db.repository import AuditLogRepository, UserSecretRepository
from services.user_secrets_service import UserSecretsService


def get_user_secrets_service(
    db: Session = Depends(get_db),
) -> UserSecretsService:
    return UserSecretsService(
        secret_repo=UserSecretRepository(db),
        audit_repo=AuditLogRepository(db),
    )
