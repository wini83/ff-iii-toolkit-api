from datetime import UTC, date, datetime

from api.deps_runtime import get_tx_application_runtime
from api.models.tx import (
    ScreeningMonthResponse,
    SimplifiedCategory,
    SimplifiedTx,
    TxTag,
)
from api.routers.auth import create_access_token
from services.db.repository import UserRepository
from services.domain.metrics import TXStatisticsMetrics
from services.exceptions import ExternalServiceFailed
from services.tx_stats.models import JobStatus, MetricsState


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


class FakeTxApplicationService:
    def __init__(
        self,
        *,
        screening_response: ScreeningMonthResponse | None = None,
        metrics_state: MetricsState[TXStatisticsMetrics] | None = None,
        apply_category_error: Exception | None = None,
        apply_tag_error: Exception | None = None,
    ) -> None:
        self.screening_response = screening_response
        self.metrics_state = metrics_state
        self.apply_category_error = apply_category_error
        self.apply_tag_error = apply_tag_error
        self.applied_categories: list[tuple[int, int]] = []
        self.applied_tags: list[tuple[int, TxTag]] = []

    async def get_screening_month(self, *, year: int, month: int):
        return self.screening_response

    async def apply_category(self, *, tx_id: int, category_id: int) -> None:
        if self.apply_category_error:
            raise self.apply_category_error
        self.applied_categories.append((tx_id, category_id))

    async def apply_tag(self, *, tx_id: int, tag: TxTag) -> None:
        if self.apply_tag_error:
            raise self.apply_tag_error
        self.applied_tags.append((tx_id, tag))

    async def get_tx_metrics(self):
        return self.metrics_state

    async def refresh_tx_metrics(self):
        return self.metrics_state


def _metrics_state() -> MetricsState[TXStatisticsMetrics]:
    result = TXStatisticsMetrics(
        total_transactions=10,
        fetching_duration_ms=1500,
        single_part_transactions=5,
        uncategorized_transactions=2,
        blik_not_ok=1,
        action_req=1,
        allegro_not_ok=1,
        categorizable=3,
        categorizable_by_month={"2024-01": 3},
        time_stamp=datetime(2024, 1, 1, tzinfo=UTC),
    )
    return MetricsState(
        status=JobStatus.DONE,
        result=result,
        error=None,
        progress=None,
        last_updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def _screening_response() -> ScreeningMonthResponse:
    tx = SimplifiedTx(
        id=1,
        date=date(2024, 1, 2),
        amount=10.0,
        description="Coffee",
        tags=["tag1"],
        notes="note",
        category=None,
        currency_code="PLN",
        currency_symbol="PLN",
        type="withdrawal",
        fx_amount=None,
        fx_currency=None,
    )
    category = SimplifiedCategory(id=1, name="Food")
    return ScreeningMonthResponse(
        year=2024,
        month=1,
        remaining=1,
        transactions=[tx],
        categories=[category],
    )


def test_tx_screening_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeTxApplicationService(screening_response=_screening_response())
    client.app.dependency_overrides[get_tx_application_runtime] = lambda: svc

    response = client.get(
        "/api/tx/screening?year=2024&month=1",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["year"] == 2024
    assert body["month"] == 1
    assert body["remaining"] == 1
    assert body["transactions"][0]["id"] == 1
    assert body["categories"][0]["name"] == "Food"


def test_tx_screening_no_results_returns_204(client, db):
    user = _create_user(db)
    svc = FakeTxApplicationService(screening_response=None)
    client.app.dependency_overrides[get_tx_application_runtime] = lambda: svc

    response = client.get(
        "/api/tx/screening?year=2024&month=1",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 204


def test_tx_requires_auth_returns_401(client):
    response = client.get("/api/tx/screening?year=2024&month=1")

    assert response.status_code == 401


def test_tx_apply_category_happy_path_returns_204(client, db):
    user = _create_user(db)
    svc = FakeTxApplicationService()
    client.app.dependency_overrides[get_tx_application_runtime] = lambda: svc

    response = client.post(
        "/api/tx/123/category/456",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 204
    assert svc.applied_categories == [(123, 456)]


def test_tx_apply_tag_external_error_returns_502(client, db):
    user = _create_user(db)
    svc = FakeTxApplicationService(apply_tag_error=ExternalServiceFailed("boom"))
    client.app.dependency_overrides[get_tx_application_runtime] = lambda: svc

    response = client.post(
        "/api/tx/123/tag/?tag=blik_done",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 502


def test_tx_stats_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeTxApplicationService(metrics_state=_metrics_state())
    client.app.dependency_overrides[get_tx_application_runtime] = lambda: svc

    response = client.get(
        "/api/tx/statistics",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["result"]["categorizable"] == 3
    assert body["result"]["fetch_seconds"] == 1.5


def test_tx_stats_refresh_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeTxApplicationService(metrics_state=_metrics_state())
    client.app.dependency_overrides[get_tx_application_runtime] = lambda: svc

    response = client.post(
        "/api/tx/statistics/refresh",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["result"]["uncategorized_transactions"] == 2
