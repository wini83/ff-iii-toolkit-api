import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

import services.blik_application_service as app_module
from api.mappers.blik import build_blik_match_id
from services.blik_application_service import BlikApplicationService
from services.blik_state_store import BlikStateStore
from services.domain.bank_record import BankRecord
from services.domain.blik import BlikApplyJob, MatchDecision
from services.domain.job_base import JobStatus
from services.domain.match_result import MatchResult
from services.domain.transaction import Currency, Transaction, TxType
from services.exceptions import (
    ExternalServiceFailed,
    FileNotFound,
    InvalidFileId,
    MatchesNotComputed,
)
from services.firefly_base_service import FireflyServiceError
from services.tx_stats.models import MetricsState
from settings import settings
from utils.encoding import encode_base64url

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


def _service(state_store: BlikStateStore | None = None) -> BlikApplicationService:
    return BlikApplicationService(
        enrichment_service=MagicMock(),
        metrics_provider=MagicMock(),
        state_store=state_store or BlikStateStore(),
    )


def test_upload_csv_returns_encoded_id_and_count():
    file_bytes = b"header\nrow\n"
    records = [
        BankRecord(
            date=date(2024, 1, 5),
            amount=Decimal("10.00"),
            details="BLIK payment",
            recipient="ACME",
            operation_amount=Decimal("10.00"),
        )
    ]
    tmp_handle = MagicMock()
    tmp_handle.name = "/tmp/abc123.csv"
    tmp_cm = MagicMock()
    tmp_cm.__enter__.return_value = tmp_handle
    tmp_cm.__exit__.return_value = None

    service = _service()

    with (
        patch(
            "services.blik_application_service.tempfile.NamedTemporaryFile",
            return_value=tmp_cm,
        ),
        patch("services.blik_application_service.BankCSVReader") as reader_cls,
    ):
        reader_cls.return_value.parse.return_value = records
        response = asyncio.run(service.upload_csv(file_bytes=file_bytes))

    tmp_handle.write.assert_called_once_with(file_bytes)
    assert response.message == "File uploaded successfully"
    assert response.count == len(records)
    assert response.id == encode_base64url("abc123")


def test_preview_csv_returns_simplified_content():
    encoded_id = encode_base64url("file123")
    records = [
        BankRecord(
            date=date(2024, 1, 5),
            amount=Decimal("10.00"),
            details="BLIK payment",
            recipient="ACME",
            operation_amount=Decimal("10.00"),
        )
    ]
    service = _service()

    with (
        patch("services.blik_application_service.BankCSVReader") as reader_cls,
        patch("services.blik_application_service.os.path.exists", return_value=True),
    ):
        reader_cls.return_value.parse.return_value = records
        response = asyncio.run(service.preview_csv(encoded_id=encoded_id))

    assert response.file_id == encoded_id
    assert response.decoded_name == "file123"
    assert response.size == 1
    assert response.content[0].details == "BLIK payment"


def test_preview_matches_calls_service_and_returns_counts():
    encoded_id = encode_base64url("file123")
    csv_records = [
        BankRecord(
            date=date(2024, 1, 5),
            amount=Decimal("10.00"),
            details="BLIK payment",
            recipient="ACME",
            operation_amount=Decimal("10.00"),
        )
    ]
    record_extra = BankRecord(
        date=date(2024, 1, 6),
        amount=Decimal("12.00"),
        details="BLIK payment",
        recipient="Shop",
        operation_amount=Decimal("12.00"),
    )
    tx1 = Transaction(
        id=1,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx2 = Transaction(
        id=2,
        date=date(2024, 1, 6),
        amount=Decimal("12.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx3 = Transaction(
        id=3,
        date=date(2024, 1, 7),
        amount=Decimal("14.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    matches = [
        MatchResult(tx=tx1, matches=[]),
        MatchResult(tx=tx2, matches=[csv_records[0]]),
        MatchResult(tx=tx3, matches=[csv_records[0], record_extra]),
    ]

    blik_service = MagicMock()
    blik_service.match = AsyncMock(return_value=matches)
    service = BlikApplicationService(
        enrichment_service=blik_service,
        metrics_provider=MagicMock(),
        state_store=BlikStateStore(),
    )

    with (
        patch("services.blik_application_service.BankCSVReader") as reader_cls,
        patch("services.blik_application_service.os.path.exists", return_value=True),
    ):
        reader_cls.return_value.parse.return_value = csv_records
        response = asyncio.run(service.preview_matches(encoded_id=encoded_id))

    blik_service.match.assert_awaited_once_with(
        candidates=csv_records,
        filter_text=settings.BLIK_DESCRIPTION_FILTER,
        tag_done=settings.TAG_BLIK_DONE,
    )
    assert response.file_id == encoded_id
    assert response.decoded_name == "file123"
    assert response.records_in_file == len(csv_records)
    assert response.transactions_found == len(matches)
    assert response.transactions_not_matched == 1
    assert response.transactions_with_one_match == 1
    assert response.transactions_with_many_matches == 1
    assert len(response.content) == len(matches)
    assert response.content[1].matches[0].match_id == build_blik_match_id(
        transaction_id=2,
        record=csv_records[0],
    )


def test_preview_matches_propagates_firefly_error():
    encoded_id = encode_base64url("file123")
    csv_records = [
        BankRecord(
            date=date(2024, 1, 5),
            amount=Decimal("10.00"),
            details="BLIK payment",
            recipient="ACME",
            operation_amount=Decimal("10.00"),
        )
    ]

    blik_service = MagicMock()
    blik_service.match = AsyncMock(side_effect=FireflyServiceError("boom"))
    service = BlikApplicationService(
        enrichment_service=blik_service,
        metrics_provider=MagicMock(),
        state_store=BlikStateStore(),
    )

    with (
        patch("services.blik_application_service.BankCSVReader") as reader_cls,
        patch("services.blik_application_service.os.path.exists", return_value=True),
    ):
        reader_cls.return_value.parse.return_value = csv_records
        with pytest.raises(ExternalServiceFailed):
            asyncio.run(service.preview_matches(encoded_id=encoded_id))


def test_preview_csv_rejects_invalid_file_id():
    blik_service = MagicMock()
    service = BlikApplicationService(
        enrichment_service=blik_service,
        metrics_provider=MagicMock(),
        state_store=BlikStateStore(),
    )
    bad_id = encode_base64url("../bad")

    with pytest.raises(InvalidFileId):
        asyncio.run(service.preview_csv(encoded_id=bad_id))


def test_preview_csv_raises_when_file_missing():
    blik_service = MagicMock()
    service = BlikApplicationService(
        enrichment_service=blik_service,
        metrics_provider=MagicMock(),
        state_store=BlikStateStore(),
    )
    encoded_id = encode_base64url("missing")

    with (
        patch("services.blik_application_service.os.path.exists", return_value=False),
        pytest.raises(FileNotFound),
    ):
        asyncio.run(service.preview_csv(encoded_id=encoded_id))


@pytest.mark.anyio
async def test_get_metrics_state_triggers_refresh_when_pending():
    expected_state = MetricsState(
        status=JobStatus.RUNNING,
        result=None,
        error=None,
        progress="queued",
        last_updated_at=None,
    )
    manager = MagicMock()
    manager.get_state.return_value = MetricsState(
        status=JobStatus.PENDING,
        result=None,
        error=None,
        progress=None,
        last_updated_at=None,
    )
    manager.ensure_current = AsyncMock(return_value=expected_state)

    service = _service()
    service.blik_metrics_manager = manager

    state = await service.get_metrics_state()

    manager.ensure_current.assert_awaited_once()
    assert state is expected_state


@pytest.mark.anyio
async def test_start_apply_job_raises_when_matches_not_computed():
    service = _service()

    with pytest.raises(MatchesNotComputed):
        await service.start_apply_job(
            encoded_id=encode_base64url("missing"),
            decisions=[],
        )


@pytest.mark.anyio
async def test_start_apply_job_creates_job_and_schedules_task(monkeypatch):
    encoded_id = encode_base64url("file123")
    tx = Transaction(
        id=1,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    match = MatchResult(tx=tx, matches=[])

    store = BlikStateStore()
    store.put_matches(file_id=encoded_id, matches=[match])
    service = BlikApplicationService(
        enrichment_service=MagicMock(),
        metrics_provider=MagicMock(),
        state_store=store,
    )

    captured = {}

    def fake_create_task(coro):
        captured["scheduled"] = True
        coro.close()
        return object()

    monkeypatch.setattr(app_module, "create_task", fake_create_task)

    job = await service.start_apply_job(
        encoded_id=encoded_id,
        decisions=[MatchDecision(transaction_id=1, selected_match_id="m1")],
    )

    assert captured["scheduled"] is True
    assert isinstance(job.id, type(uuid4()))
    assert job.file_id == encoded_id
    assert job.total == 1


@pytest.mark.anyio
async def test_run_apply_job_counts_success_and_failures():
    tx1 = Transaction(
        id=1,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx2 = Transaction(
        id=2,
        date=date(2024, 1, 6),
        amount=Decimal("12.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    evidence1 = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="BLIK payment 1",
        recipient="ACME",
        operation_amount=Decimal("10.00"),
    )
    evidence2 = BankRecord(
        date=date(2024, 1, 6),
        amount=Decimal("12.00"),
        details="BLIK payment 2",
        recipient="SHOP",
        operation_amount=Decimal("12.00"),
    )

    blik_service = MagicMock()

    async def _apply_match(*, tx, evidence):
        if int(tx.id) == 2:
            raise FireflyServiceError("boom")

    blik_service.apply_match = AsyncMock(side_effect=_apply_match)
    service = BlikApplicationService(
        enrichment_service=blik_service,
        metrics_provider=MagicMock(),
        state_store=BlikStateStore(),
    )

    matches = [
        MatchResult(tx=tx1, matches=[evidence1]),
        MatchResult(tx=tx2, matches=[evidence2]),
    ]
    job = BlikApplyJob(
        id=uuid4(),
        file_id=encode_base64url("file123"),
        total=3,
        status=JobStatus.PENDING,
    )
    decisions = [
        MatchDecision(
            transaction_id=1,
            selected_match_id=build_blik_match_id(transaction_id=1, record=evidence1),
        ),
        MatchDecision(transaction_id=999, selected_match_id="missing"),
        MatchDecision(
            transaction_id=2,
            selected_match_id=build_blik_match_id(transaction_id=2, record=evidence2),
        ),
    ]

    await service._run_apply_job(job=job, decisions=decisions, matches=matches)

    assert blik_service.apply_match.await_count == 2
    assert job.applied == 1
    assert job.failed == 2
    assert job.status == JobStatus.DONE
    assert job.finished_at is not None


@pytest.mark.anyio
@pytest.mark.parametrize("limit,expected_ids", [(None, [1, 3]), (1, [1])])
async def test_start_auto_apply_single_matches_builds_decisions_for_single_matches_only(
    limit, expected_ids
):
    encoded_id = encode_base64url("file123")
    tx1 = Transaction(
        id=1,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx2 = Transaction(
        id=2,
        date=date(2024, 1, 6),
        amount=Decimal("12.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx3 = Transaction(
        id=3,
        date=date(2024, 1, 7),
        amount=Decimal("14.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    evidence1 = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="single 1",
        recipient="ACME",
        operation_amount=Decimal("10.00"),
    )
    evidence2a = BankRecord(
        date=date(2024, 1, 6),
        amount=Decimal("12.00"),
        details="multi a",
        recipient="SHOP",
        operation_amount=Decimal("12.00"),
    )
    evidence2b = BankRecord(
        date=date(2024, 1, 6),
        amount=Decimal("12.00"),
        details="multi b",
        recipient="SHOP",
        operation_amount=Decimal("12.00"),
    )
    evidence3 = BankRecord(
        date=date(2024, 1, 7),
        amount=Decimal("14.00"),
        details="single 3",
        recipient="MARKET",
        operation_amount=Decimal("14.00"),
    )

    store = BlikStateStore()
    store.put_matches(
        file_id=encoded_id,
        matches=[
            MatchResult(tx=tx1, matches=[evidence1]),
            MatchResult(tx=tx2, matches=[evidence2a, evidence2b]),
            MatchResult(tx=tx3, matches=[evidence3]),
        ],
    )
    service = BlikApplicationService(
        enrichment_service=MagicMock(),
        metrics_provider=MagicMock(),
        state_store=store,
    )
    job = BlikApplyJob(
        id=uuid4(),
        file_id=encoded_id,
        total=len(expected_ids),
        status=JobStatus.PENDING,
    )
    service.start_apply_job = AsyncMock(return_value=job)

    result = await service.start_auto_apply_single_matches(
        encoded_id=encoded_id,
        limit=limit,
    )

    service.start_apply_job.assert_awaited_once()
    decisions = service.start_apply_job.await_args.kwargs["decisions"]
    assert [decision.transaction_id for decision in decisions] == expected_ids
    assert result is job
