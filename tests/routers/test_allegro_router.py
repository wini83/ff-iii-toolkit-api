from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from api.deps_runtime import get_allegro_application_runtime
from api.routers.auth import create_access_token
from services.db.repository import UserRepository
from services.domain.allegro import AllegroApplyJob
from services.domain.job_base import JobStatus
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
        secrets=None,
        payments=None,
        matches=None,
        fetch_error=None,
        matches_error=None,
        job=None,
        start_error=None,
        auto_job=None,
        auto_error=None,
        lookup_job=None,
        metrics_state=None,
        refresh_metrics_state=None,
    ):
        self._secrets = secrets if secrets is not None else []
        self._payments = payments
        self._matches = matches
        self._fetch_error = fetch_error
        self._matches_error = matches_error
        self._job = job
        self._start_error = start_error
        self._auto_job = auto_job
        self._auto_error = auto_error
        self._metrics_state = metrics_state
        self._refresh_metrics_state = refresh_metrics_state
        self._cleared_secret = False
        self._cleared_page = False
        self._cleared_page_payload = None
        self.state_store = SimpleNamespace(
            job_manager=SimpleNamespace(get=lambda _job_id: lookup_job)
        )

    async def start_apply_job(self, *, secret_id, decisions):
        if self._start_error:
            raise self._start_error
        return self._job

    def get_allegro_secrets(self, *, user_id):
        return self._secrets

    def fetch_allegro_data(self, *, user_id, secret_id, page):
        if self._fetch_error:
            raise self._fetch_error
        return self._payments

    async def preview_matches(self, *, user_id, secret_id, page):
        if self._matches_error:
            raise self._matches_error
        return self._matches

    async def start_auto_apply_single_matches(self, *, secret_id, limit):
        if self._auto_error:
            raise self._auto_error
        return self._auto_job

    def get_metrics_state(self):
        return self._metrics_state

    async def refresh_metrics_state(self):
        return self._refresh_metrics_state

    def clear_cached_secret(self, *, secret_id):
        self._cleared_secret = True
        return True

    def clear_cached_page(self, *, secret_id, page):
        self._cleared_page = True
        self._cleared_page_payload = page
        return True


def _job() -> AllegroApplyJob:
    return AllegroApplyJob(
        id=uuid4(),
        secret_id=uuid4(),
        total=2,
        status=JobStatus.DONE,
        started_at=datetime.now(UTC),
        applied=1,
        failed=1,
    )


def test_list_secrets_returns_payload(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    secrets = [
        {
            "id": str(uuid4()),
            "type": "allegro",
            "usage_count": 0,
            "last_used_at": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
    ]
    svc = FakeAllegroSvc(secrets=secrets)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.get("/api/allegro/secrets", headers=_auth_header(str(user.id)))

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == secrets[0]["id"]
    assert body[0]["type"] == "allegro"
    assert body[0]["usage_count"] == 0
    assert body[0]["last_used_at"] is None


@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (None, 200, None),
        (ExternalServiceFailed("upstream"), 502, "upstream"),
    ],
)
def test_fetch_for_id_maps_success_and_external_error(
    client, db, error, status, detail
):
    user = _create_user(db, username=f"u-{uuid4()}")
    payment = {
        "date": "2025-01-10",
        "amount": "10.00",
        "details": ["d1"],
        "tx_id": 1,
        "tx_match": True,
        "tx_date": "2025-01-10",
        "tx_amount": "10.00",
        "tx_description": "desc",
        "tx_compare": True,
        "tx_tags": [],
        "tx_notes": None,
        "tag_done": "allegro_done",
        "allegro_login": "login",
        "is_balanced": True,
        "external_short_id": "A1",
        "external_id": "PAY-1",
        "matches": [],
    }
    svc = FakeAllegroSvc(
        payments=SimpleNamespace(payments=[SimpleNamespace(**payment)]),
        fetch_error=error,
    )
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.get(
        f"/api/allegro/{uuid4()}/payments?limit=20&offset=5",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == status
    if status == 200:
        assert response.json()[0]["external_id"] == "PAY-1"
    else:
        assert response.json()["detail"] == detail


def test_fetch_for_id_invalid_secret_id_returns_400(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc()
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.get(
        "/api/allegro/not-a-uuid/payments",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 400


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (None, 200, None),
        (MatchesNotComputed(), 400, "No match data found"),
        (TransactionNotFound("tx missing"), 400, "tx missing"),
        (InvalidMatchSelection("bad selection"), 400, "bad selection"),
        (ExternalServiceFailed("upstream"), 502, "upstream"),
    ],
)
async def test_preview_matches_maps_all_errors(client, db, error, status, detail):
    user = _create_user(db, username=f"u-{uuid4()}")
    data = {
        "login": "unknown",
        "payments_fetched": 0,
        "transactions_found": 0,
        "transactions_not_matched": 0,
        "transactions_with_one_match": 0,
        "transactions_with_many_matches": 0,
        "fetch_seconds": 0.01,
        "content": [],
    }
    svc = FakeAllegroSvc(matches=data, matches_error=error)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.get(
        f"/api/allegro/{uuid4()}/matches",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == status
    if status == 200:
        assert response.json()["content"] == []
    else:
        assert response.json()["detail"] == detail


@pytest.mark.anyio
async def test_preview_matches_invalid_secret_id_returns_400(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc(matches={"page": {"limit": 25, "offset": 0}, "results": []})
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.get(
        "/api/allegro/not-a-uuid/matches",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 400


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


@pytest.mark.anyio
async def test_apply_matches_invalid_secret_id_returns_400(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc(job=_job())
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.post(
        "/api/allegro/not-a-uuid/apply",
        headers=_auth_header(str(user.id)),
        json={"decisions": []},
    )

    assert response.status_code == 400


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
    state = SimpleNamespace(
        status=JobStatus.PENDING, progress="p", result=None, error=None
    )
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
    state = SimpleNamespace(
        status=JobStatus.DONE, progress=None, result=None, error=None
    )
    svc = FakeAllegroSvc(refresh_metrics_state=state)
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.post(
        "/api/allegro/statistics/refresh",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_clear_cache_for_secret_returns_scope_secret(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc()
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.delete(
        f"/api/allegro/{uuid4()}/cache",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    assert response.json() == {"scope": "secret", "cleared": True}
    assert svc._cleared_secret is True


def test_clear_cache_for_page_returns_scope_page(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc()
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.delete(
        f"/api/allegro/{uuid4()}/cache?limit=25&offset=50",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "scope": "page",
        "cleared": True,
        "limit": 25,
        "offset": 50,
    }
    assert svc._cleared_page is True
    assert svc._cleared_page_payload.limit == 25
    assert svc._cleared_page_payload.offset == 50


@pytest.mark.parametrize(
    "query",
    [
        "?limit=25",
        "?offset=0",
    ],
)
def test_clear_cache_requires_limit_and_offset_pair(client, db, query):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc()
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.delete(
        f"/api/allegro/{uuid4()}/cache{query}",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Provide both limit and offset to clear a single page cache"
    )


def test_clear_cache_invalid_secret_id_returns_400(client, db):
    user = _create_user(db, username=f"u-{uuid4()}")
    svc = FakeAllegroSvc()
    client.app.dependency_overrides[get_allegro_application_runtime] = lambda: svc

    response = client.delete(
        "/api/allegro/not-a-uuid/cache",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid secret_id"
