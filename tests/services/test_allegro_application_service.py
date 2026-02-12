from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import services.allegro_application_service as app_module
from services.allegro_application_service import AllegroApplicationService
from services.allegro_state_store import AllegroStateStore
from services.domain.allegro import (
    AllegroApplyJob,
    AllegroOrderPayment,
    ApplyJobStatus,
    MatchDecision,
)
from services.domain.match_result import MatchResult
from services.domain.transaction import Currency, Transaction, TxTag, TxType
from services.domain.user_secrets import SecretType
from services.exceptions import (
    ExternalServiceFailed,
    InvalidSecretId,
    MatchesNotComputed,
)
from services.tx_stats.models import JobStatus, MetricsState


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


def _tx(tx_id: int) -> Transaction:
    return Transaction(
        id=tx_id,
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description=f"tx-{tx_id}",
        tags=set(),
        notes=None,
        category=None,
        currency=Currency(code="PLN", symbol="zl", decimals=2),
        fx=None,
    )


def _payment(external_short_id: str, external_id: str) -> AllegroOrderPayment:
    return AllegroOrderPayment(
        amount=Decimal("10.00"),
        date=date(2024, 1, 1),
        details=["d1"],
        tag_done=TxTag.allegro_done,
        is_balanced=True,
        allegro_login="login",
        external_short_id=external_short_id,
        external_id=external_id,
    )


def _service(state_store: AllegroStateStore | None = None) -> AllegroApplicationService:
    return AllegroApplicationService(
        secrets_service=MagicMock(),
        ff_allegro_service=MagicMock(),
        allegro_service=MagicMock(),
        state_store=state_store or AllegroStateStore(),
    )


def test_get_allegro_secrets_filters_only_allegro():
    service = _service()
    allegro_secret = SimpleNamespace(type=SecretType.ALLEGRO)
    blik_secret = SimpleNamespace(type=SecretType.AMAZON)
    service.secrets_service.list_for_user.return_value = [allegro_secret, blik_secret]

    secrets = service.get_allegro_secrets(user_id=uuid4())

    assert secrets == [allegro_secret]


def test_fetch_allegro_data_wraps_missing_secret():
    service = _service()
    service.secrets_service.get_for_internal_use.side_effect = RuntimeError("missing")

    with pytest.raises(InvalidSecretId, match="Secret with id"):
        service.fetch_allegro_data(user_id=uuid4(), secret_id=uuid4())


def test_fetch_allegro_data_wraps_external_error():
    service = _service()
    secret = SimpleNamespace(secret="cookie", id=uuid4())
    service.secrets_service.get_for_internal_use.return_value = secret
    service.allegro_service.fetch.side_effect = RuntimeError("upstream")

    with pytest.raises(ExternalServiceFailed, match="Failed to fetch allegro data"):
        service.fetch_allegro_data(user_id=uuid4(), secret_id=uuid4())


@pytest.mark.anyio
async def test_preview_matches_uses_unknown_login_for_empty_payments():
    service = _service()
    secret_id = uuid4()
    service.fetch_allegro_data = MagicMock(return_value=SimpleNamespace(payments=[]))
    service.ff_allegro_service.match = AsyncMock(return_value=[])

    result = await service.preview_matches(user_id=uuid4(), secret_id=secret_id)

    assert result.login == "unknown"
    assert service.state_store.matches_cache[str(secret_id)] == []


@pytest.mark.anyio
async def test_start_apply_job_raises_when_matches_not_computed():
    service = _service()

    with pytest.raises(MatchesNotComputed):
        await service.start_apply_job(secret_id=uuid4(), decisions=[])


@pytest.mark.anyio
async def test_start_apply_job_creates_job_and_schedules_task(monkeypatch):
    secret_id = uuid4()
    store = AllegroStateStore(
        matches_cache={str(secret_id): [MatchResult(tx=_tx(1), matches=[])]}
    )
    service = _service(store)

    captured = {}

    def fake_create_task(coro):
        captured["scheduled"] = True
        coro.close()
        return object()

    monkeypatch.setattr(app_module, "create_task", fake_create_task)

    job = await service.start_apply_job(
        secret_id=secret_id,
        decisions=[MatchDecision(payment_id="p1", transaction_id=1)],
    )

    assert captured["scheduled"] is True
    assert isinstance(job.id, type(secret_id))
    assert job.total == 1


@pytest.mark.anyio
async def test_run_apply_job_counts_success_and_failures():
    ff = MagicMock()

    async def _apply_match(*, tx, evidence):
        if int(tx.id) == 2:
            raise RuntimeError("boom")

    ff.apply_match = AsyncMock(side_effect=_apply_match)

    service = AllegroApplicationService(
        secrets_service=MagicMock(),
        ff_allegro_service=ff,
        allegro_service=MagicMock(),
        state_store=AllegroStateStore(),
    )

    tx1 = _tx(1)
    tx2 = _tx(2)
    pay1 = _payment("ok-1", "full-1")
    pay2 = _payment("ok-2", "full-2")

    matches = [
        MatchResult(tx=tx1, matches=[pay1]),
        MatchResult(tx=tx2, matches=[pay2]),
    ]

    job = AllegroApplyJob(
        id=uuid4(),
        secret_id=uuid4(),
        total=4,
        status=ApplyJobStatus.PENDING,
    )

    decisions = [
        MatchDecision(payment_id="ok-1", transaction_id=1),  # success
        MatchDecision(payment_id="missing", transaction_id=1),  # invalid payment
        MatchDecision(payment_id="ok-1", transaction_id=999),  # tx not found
        MatchDecision(payment_id="ok-2", transaction_id=2),  # apply error
    ]

    await service._run_apply_job(job=job, decisions=decisions, matches=matches)

    assert ff.apply_match.await_count == 2
    assert job.applied == 1
    assert job.failed == 3
    assert job.status == ApplyJobStatus.DONE
    assert job.finished_at is not None


def test_get_metrics_state_recreates_manager_if_missing():
    service = _service()
    service.state_store.metrics_manager = None

    state = service.get_metrics_state()

    assert state.status == JobStatus.PENDING
    assert service.state_store.metrics_manager is not None


@pytest.mark.anyio
async def test_refresh_metrics_state_uses_existing_manager():
    expected_state = MetricsState(
        status=JobStatus.DONE,
        result=None,
        error=None,
        progress=None,
        last_updated_at=None,
    )
    manager = MagicMock()
    manager.refresh = AsyncMock(return_value=expected_state)

    store = AllegroStateStore(metrics_manager=manager)
    service = _service(store)

    state = await service.refresh_metrics_state()

    manager.refresh.assert_awaited_once()
    assert state is expected_state
