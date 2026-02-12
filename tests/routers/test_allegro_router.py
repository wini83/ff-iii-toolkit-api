from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from api.deps_runtime import get_allegro_application_runtime
from api.routers.auth import create_access_token
from services.db.repository import UserRepository
from services.domain.allegro import AllegroApplyJob, ApplyJobStatus
from services.exceptions import (
    ExternalServiceFailed,
    InvalidFileId,
    InvalidMatchSelection,
    MatchesNotComputed,
    TransactionNotFound,
)


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


def _auth_header(user_id: str) -> dict[str, str]:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def _create_user(db, username: str = "user"):
    repo = UserRepository(db)
    return repo.create(
        username=username,
        password_hash="hashed",
        is_superuser=False,
    )


class FakeAllegroSvc:
    def __init__(self, *, job=None, start_error=None, lookup_job=None):
        self._job = job
        self._start_error = start_error
        self.state_store = SimpleNamespace(
            job_manager=SimpleNamespace(get=lambda _job_id: lookup_job)
        )

    async def start_apply_job(self, *, secret_id, decisions):
        if self._start_error:
            raise self._start_error
        return self._job


def _job() -> AllegroApplyJob:
    return AllegroApplyJob(
        id=uuid4(),
        secret_id=uuid4(),
        total=2,
        status=ApplyJobStatus.DONE,
        started_at=datetime.now(UTC),
        applied=1,
        failed=1,
    )


@pytest.mark.anyio
async def test_apply_matches_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeAllegroSvc(job=_job())
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.post(
        f"/api/allegro/{uuid4()}/apply",
        headers=_auth_header(str(user.id)),
        json={
            "decisions": [
                {"payment_id": "p1", "transaction_id": 1, "strategy": "manual"}
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["applied"] == 1
    assert body["failed"] == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (InvalidFileId("bad"), 400, "bad"),
        (MatchesNotComputed(), 400, "No match data found"),
        (TransactionNotFound("tx missing"), 400, "tx missing"),
        (InvalidMatchSelection("wrong payment"), 400, "wrong payment"),
        (ExternalServiceFailed("upstream"), 502, "upstream"),
    ],
)
async def test_apply_matches_error_mapping(client, db, error, status, detail):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc(start_error=error)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.post(
        f"/api/allegro/{uuid4()}/apply",
        headers=_auth_header(str(user.id)),
        json={"decisions": []},
    )

    assert response.status_code == status
    assert response.json()["detail"] == detail


def test_get_apply_job_returns_404_when_missing(client, db):
    user = _create_user(db)
    svc = FakeAllegroSvc(lookup_job=None)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.get(
        f"/api/allegro/apply-jobs/{uuid4()}",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_get_apply_job_returns_200_when_found(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    job = _job()
    svc = FakeAllegroSvc(lookup_job=job)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.get(
        f"/api/allegro/apply-jobs/{job.id}",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(job.id)
    assert body["status"] == "done"
