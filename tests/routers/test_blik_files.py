from datetime import UTC, date, datetime

from api.deps_runtime import get_blik_application_runtime
from api.models.blik_files import (
    ApplyPayload,
    FileApplyResponse,
    FileMatchResponse,
    FilePreviewResponse,
    MatchResult,
    SimplifiedRecord,
    StatisticsResponse,
    UploadResponse,
)
from api.models.tx import SimplifiedTx
from api.routers.auth import create_access_token
from services.db.repository import UserRepository
from services.domain.metrics import BlikStatisticsMetrics
from services.exceptions import FileNotFound, InvalidFileId
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


class FakeBlikApplicationService:
    def __init__(
        self,
        *,
        statistics_response: StatisticsResponse | None = None,
        metrics_state: MetricsState[BlikStatisticsMetrics] | None = None,
        upload_response: UploadResponse | None = None,
        preview_response: FilePreviewResponse | None = None,
        matches_response: FileMatchResponse | None = None,
        apply_response: FileApplyResponse | None = None,
        preview_error: Exception | None = None,
        matches_error: Exception | None = None,
    ) -> None:
        self.statistics_response = statistics_response
        self.metrics_state = metrics_state
        self.upload_response = upload_response
        self.preview_response = preview_response
        self.matches_response = matches_response
        self.apply_response = apply_response
        self.preview_error = preview_error
        self.matches_error = matches_error
        self.uploaded_bytes: bytes | None = None
        self.applied_payload: ApplyPayload | None = None

    async def get_statistics(self, refresh: bool = False):
        return self.statistics_response

    def get_metrics_state(self):
        return self.metrics_state

    async def refresh_metrics_state(self):
        return self.metrics_state

    async def upload_csv(self, *, file_bytes: bytes):
        self.uploaded_bytes = file_bytes
        return self.upload_response

    async def preview_csv(self, *, encoded_id: str):
        if self.preview_error:
            raise self.preview_error
        return self.preview_response

    async def preview_matches(self, *, encoded_id: str):
        if self.matches_error:
            raise self.matches_error
        return self.matches_response

    async def apply_matches(self, *, encoded_id: str, payload: ApplyPayload):
        self.applied_payload = payload
        return self.apply_response


def _metrics_state() -> MetricsState[BlikStatisticsMetrics]:
    result = BlikStatisticsMetrics(
        total_transactions=10,
        fetching_duration_ms=800,
        single_part_transactions=5,
        uncategorized_transactions=2,
        filtered_by_description_exact=1,
        filtered_by_description_partial=1,
        not_processed_transactions=2,
        not_processed_by_month={"2024-01": 1},
        inclomplete_procesed_by_month={"2024-01": 1},
        time_stamp=datetime(2024, 1, 1, tzinfo=UTC),
    )
    return MetricsState(
        status=JobStatus.DONE,
        result=result,
        error=None,
        progress=None,
        last_updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def _statistics_response() -> StatisticsResponse:
    return StatisticsResponse(
        total_transactions=10,
        single_part_transactions=5,
        uncategorized_transactions=2,
        filtered_by_description_exact=1,
        filtered_by_description_partial=1,
        not_processed_transactions=2,
        not_processed_by_month={"2024-01": 1},
        inclomplete_procesed_by_month={"2024-01": 1},
    )


def _file_preview_response() -> FilePreviewResponse:
    record = SimplifiedRecord(
        date=date(2024, 1, 2),
        amount=10.0,
        details="Payment",
        recipient="Store",
        operation_amount=10.0,
    )
    return FilePreviewResponse(
        file_id="file1",
        decoded_name="file.csv",
        size=1,
        content=[record],
    )


def _file_match_response() -> FileMatchResponse:
    tx = SimplifiedTx(
        id=1,
        date=date(2024, 1, 2),
        amount=10.0,
        description="Payment",
        tags=["blik_done"],
        notes="note",
        category=None,
        currency_code="PLN",
        currency_symbol="PLN",
        type="withdrawal",
        fx_amount=None,
        fx_currency=None,
    )
    record = SimplifiedRecord(
        date=date(2024, 1, 2),
        amount=10.0,
        details="Payment",
        recipient="Store",
        operation_amount=10.0,
    )
    return FileMatchResponse(
        file_id="file1",
        decoded_name="file.csv",
        records_in_file=1,
        transactions_found=1,
        transactions_not_matched=0,
        transactions_with_one_match=1,
        transactions_with_many_matches=0,
        content=[MatchResult(tx=tx, matches=[record])],
    )


def test_blik_files_requires_auth_returns_401(client):
    response = client.get("/api/blik_files/statistics_v2")

    assert response.status_code == 401


def test_blik_files_statistics_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(statistics_response=_statistics_response())
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.get(
        "/api/blik_files/statistics",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_transactions"] == 10
    assert body["not_processed_transactions"] == 2


def test_blik_files_statistics_v2_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(metrics_state=_metrics_state())
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.get(
        "/api/blik_files/statistics_v2",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["result"]["filtered_by_description_exact"] == 1


def test_blik_files_statistics_v2_refresh_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(metrics_state=_metrics_state())
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.post(
        "/api/blik_files/statistics_v2/refresh",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"


def test_blik_files_upload_csv_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(
        upload_response=UploadResponse(message="ok", count=1, id="file1")
    )
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.post(
        "/api/blik_files",
        headers=_auth_header(str(user.id)),
        files={"file": ("file.csv", b"a,b\n1,2\n", "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "file1"
    assert svc.uploaded_bytes is not None


def test_blik_files_preview_invalid_id_returns_400(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(preview_error=InvalidFileId("bad"))
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.get(
        "/api/blik_files/bad",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 400


def test_blik_files_preview_matches_missing_file_returns_404(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(matches_error=FileNotFound())
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.get(
        "/api/blik_files/file1/matches",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 404


def test_blik_files_apply_matches_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(
        apply_response=FileApplyResponse(file_id="file1", updated=1, errors=[])
    )
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.post(
        "/api/blik_files/file1/matches",
        headers=_auth_header(str(user.id)),
        json={"tx_indexes": [1, 2]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["updated"] == 1
    assert svc.applied_payload == ApplyPayload(tx_indexes=[1, 2])


def test_blik_files_preview_csv_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(preview_response=_file_preview_response())
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.get(
        "/api/blik_files/file1",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"] == "file1"
    assert body["content"][0]["recipient"] == "Store"


def test_blik_files_preview_matches_happy_path_returns_200(client, db):
    user = _create_user(db)
    svc = FakeBlikApplicationService(matches_response=_file_match_response())
    client.app.dependency_overrides[get_blik_application_runtime] = lambda: svc

    response = client.get(
        "/api/blik_files/file1/matches",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["records_in_file"] == 1
    assert body["content"][0]["tx"]["id"] == 1
