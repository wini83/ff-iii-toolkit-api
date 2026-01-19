from uuid import UUID

import pytest
from fastapi import HTTPException, status

from services.db.repository import UserRepository
from services.guards import require_superuser


def test_require_superuser_rejects_invalid_uuid(db):
    with pytest.raises(HTTPException) as exc:
        require_superuser("not-a-uuid", db)

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_require_superuser_rejects_non_superuser(db):
    repo = UserRepository(db)
    user = repo.create(
        username="regular",
        password_hash="hashed",
        is_superuser=False,
    )

    with pytest.raises(HTTPException) as exc:
        require_superuser(str(user.id), db)

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_require_superuser_accepts_superuser(db):
    repo = UserRepository(db)
    user = repo.create(
        username="admin",
        password_hash="hashed",
        is_superuser=True,
    )

    result = require_superuser(str(user.id), db)

    assert isinstance(result, UUID)
    assert result == user.id
