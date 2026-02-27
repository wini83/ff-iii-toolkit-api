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
    def __init__(
        self,
        *,
        job=None,
        start_error=None,
        auto_job=None,
        auto_error=None,
        lookup_job=None,
        metrics_state=None,
        refresh_metrics_state=None,
    ):
        self._job = job
        self._start_error = start_error
        self._auto_job = auto_job
        self._auto_error = auto_error
        self._metrics_state = metrics_state
        self._refresh_metrics_state = refresh_metrics_state
        self.state_store = SimpleNamespace(
            job_manager=SimpleNamespace(get=lambda _job_id: lookup_job)
        )

    async def start_apply_job(self, *, secret_id, decisions):
        if self._start_error:
            raise self._start_error
        return self._job

    async def start_auto_apply_single_matches(self, *, secret_id, limit):
        if self._auto_error:
            raise self._auto_error
        return self._auto_job

    def get_metrics_state(self):
        return self._metrics_state

    async def refresh_metrics_state(self):
        return self._refresh_metrics_state


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


def test_auto_apply_single_matches_requires_auth_returns_401(client):
    response = client.post(f"/api/allegro/{uuid4()}/apply/auto")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_auto_apply_single_matches_happy_path_returns_200(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    job = _job()
    svc = FakeAllegroSvc(auto_job=job)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.post(
        f"/api/allegro/{job.secret_id}/apply/auto?limit=25",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(job.id)
    assert body["status"] == "done"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("secret_id", "error", "status", "detail"),
    [
        (
            str(uuid4()),
            MatchesNotComputed(),
            400,
            "No match data found; run preview first",
        ),
        (str(uuid4()), ExternalServiceFailed("upstream"), 502, "upstream"),
        ("not-a-uuid", None, 400, "Invalid secret_id"),
    ],
)
async def test_auto_apply_single_matches_error_mapping(
    client, db, secret_id, error, status, detail
):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc(auto_error=error, auto_job=_job())
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.post(
        f"/api/allegro/{secret_id}/apply/auto",
        headers=_auth_header(str(user.id)),
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


@pytest.mark.anyio
async def test_get_statistics_current_returns_mapped_state(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    state = SimpleNamespace(status=SimpleNamespace(value="pending"), progress="p", result=None, error=None)
    svc = FakeAllegroSvc(metrics_state=state)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.get(
        "/api/allegro/statistics",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["progress"] == "p"


@pytest.mark.anyio
async def test_refresh_statistics_current_returns_mapped_state(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    state = SimpleNamespace(status=SimpleNamespace(value="done"), progress=None, result=None, error=None)
    svc = FakeAllegroSvc(refresh_metrics_state=state)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.post(
        "/api/allegro/statistics/refresh",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "done"
