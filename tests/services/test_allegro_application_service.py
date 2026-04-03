from datetime import date, datetime
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
    AllegroPageRequest,
    MatchDecision,
)
from services.domain.job_base import JobStatus
from services.domain.match_result import MatchProcessingStatus, MatchResult
from services.domain.transaction import Currency, Transaction, TxTag, TxType
from services.domain.user_secrets import SecretType
from services.exceptions import (
    ExternalServiceFailed,
    InvalidSecretId,
    MatchesNotComputed,
    SecretNotAccessible,
)
from services.tx_stats.models import MetricsState


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
    metrics_provider = MagicMock()
    metrics_provider.get_cached_snapshot_timestamp = AsyncMock(
        return_value=datetime.now(app_module.UTC)
    )
    metrics_provider.fetch_metrics = AsyncMock()
    metrics_provider.refresh_metrics = AsyncMock()
    return AllegroApplicationService(
        secrets_service=MagicMock(),
        enrichment_service=MagicMock(),
        metrics_provider=metrics_provider,
        allegro_service=MagicMock(),
        state_store=state_store or AllegroStateStore(),
        filter_desc_allegro="allegro",
    )


def test_get_allegro_secrets_filters_only_allegro():
    service = _service()
    allegro_secret = SimpleNamespace(type=SecretType.ALLEGRO)
    blik_secret = SimpleNamespace(type=SecretType.AMAZON)
    service.secrets_service.list_secrets.return_value = [allegro_secret, blik_secret]

    secrets = service.get_allegro_secrets(user_id=uuid4())

    assert secrets == [allegro_secret]


def test_fetch_allegro_data_wraps_missing_secret():
    service = _service()
    service.secrets_service.get_secret_for_internal_use.side_effect = (
        SecretNotAccessible("missing")
    )

    with pytest.raises(InvalidSecretId, match="Secret with id"):
        service.fetch_allegro_data(
            user_id=uuid4(),
            secret_id=uuid4(),
            vault_session_id="session-123",
            page=AllegroPageRequest(),
        )


def test_fetch_allegro_data_wraps_external_error():
    service = _service()
    secret = SimpleNamespace(secret="cookie", id=uuid4())
    service.secrets_service.get_secret_for_internal_use.return_value = secret
    service.allegro_service.fetch.side_effect = RuntimeError("upstream")

    with pytest.raises(ExternalServiceFailed, match="Failed to fetch allegro data"):
        service.fetch_allegro_data(
            user_id=uuid4(),
            secret_id=uuid4(),
            vault_session_id="session-123",
            page=AllegroPageRequest(),
        )


@pytest.mark.anyio
async def test_preview_matches_uses_unknown_login_for_empty_payments():
    service = _service()
    secret_id = uuid4()
    page = AllegroPageRequest(limit=10, offset=20)
    service.fetch_allegro_data = MagicMock(return_value=SimpleNamespace(payments=[]))
    service.enrichment_service.match_with_unmatched = AsyncMock(return_value=([], []))

    result = await service.preview_matches(
        user_id=uuid4(),
        secret_id=secret_id,
        vault_session_id="session-123",
        page=page,
    )

    assert result.login == "unknown"
    assert result.unmatched_payments == []
    assert service.state_store.get_page_matches(secret_id=secret_id, page=page) == []


@pytest.mark.anyio
async def test_preview_matches_returns_unmatched_payments():
    service = _service()
    secret_id = uuid4()
    page = AllegroPageRequest(limit=10, offset=0)
    matched_payment = _payment("p-1", "full-1")
    unmatched_payment = _payment("p-2", "full-2")
    service.fetch_allegro_data = MagicMock(
        return_value=SimpleNamespace(payments=[matched_payment, unmatched_payment])
    )
    service.enrichment_service.match_with_unmatched = AsyncMock(
        return_value=(
            [
                MatchResult(
                    tx=_tx(1),
                    matches=[matched_payment],
                    status=MatchProcessingStatus.NEW,
                )
            ],
            [unmatched_payment],
        )
    )

    result = await service.preview_matches(
        user_id=uuid4(),
        secret_id=secret_id,
        vault_session_id="session-123",
        page=page,
    )

    assert result.unmatched_payments == [unmatched_payment]


@pytest.mark.anyio
async def test_start_apply_job_raises_when_matches_not_computed():
    service = _service()

    with pytest.raises(MatchesNotComputed):
        await service.start_apply_job(secret_id=uuid4(), decisions=[])


@pytest.mark.anyio
async def test_start_apply_job_creates_job_and_schedules_task(monkeypatch):
    secret_id = uuid4()
    store = AllegroStateStore()
    store.put_page_matches(
        secret_id=secret_id,
        entry=app_module.AllegroPageMatchCacheEntry(
            page=AllegroPageRequest(limit=25, offset=0),
            login="u1",
            payments=[],
            matches=[
                MatchResult(tx=_tx(1), matches=[], status=MatchProcessingStatus.NEW)
            ],
        ),
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
        enrichment_service=ff,
        metrics_provider=MagicMock(),
        allegro_service=MagicMock(),
        state_store=AllegroStateStore(),
        filter_desc_allegro="allegro",
    )

    tx1 = _tx(1)
    tx2 = _tx(2)
    pay1 = _payment("ok-1", "full-1")
    pay2 = _payment("ok-2", "full-2")

    matches = [
        MatchResult(tx=tx1, matches=[pay1], status=MatchProcessingStatus.NEW),
        MatchResult(tx=tx2, matches=[pay2], status=MatchProcessingStatus.NEW),
    ]

    job = AllegroApplyJob(
        id=uuid4(),
        secret_id=uuid4(),
        total=4,
        status=JobStatus.PENDING,
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
    assert job.status == JobStatus.DONE
    assert job.finished_at is not None


@pytest.mark.anyio
async def test_start_auto_apply_single_matches_raises_when_matches_not_computed():
    service = _service()
    with pytest.raises(MatchesNotComputed):
        await service.start_auto_apply_single_matches(secret_id=uuid4())


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("limit", "expected_pairs"),
    [
        (None, [(1, "single-1"), (4, "single-4")]),
        (1, [(1, "single-1")]),
    ],
)
async def test_start_auto_apply_single_matches_builds_decisions_for_single_matches_only(
    limit, expected_pairs
):
    secret_id = uuid4()
    store = AllegroStateStore()
    store.put_page_matches(
        secret_id=secret_id,
        entry=app_module.AllegroPageMatchCacheEntry(
            page=AllegroPageRequest(limit=2, offset=0),
            login="u1",
            payments=[],
            matches=[
                MatchResult(
                    tx=_tx(1),
                    matches=[_payment("single-1", "full-1")],
                    status=MatchProcessingStatus.NEW,
                ),
                MatchResult(
                    tx=_tx(2),
                    matches=[
                        _payment("multi-1", "full-2"),
                        _payment("multi-2", "full-3"),
                    ],
                    status=MatchProcessingStatus.NEW,
                ),
            ],
        ),
    )
    store.put_page_matches(
        secret_id=secret_id,
        entry=app_module.AllegroPageMatchCacheEntry(
            page=AllegroPageRequest(limit=2, offset=2),
            login="u1",
            payments=[],
            matches=[
                MatchResult(tx=_tx(3), matches=[], status=MatchProcessingStatus.NEW),
                MatchResult(
                    tx=_tx(4),
                    matches=[_payment("single-4", "full-4")],
                    status=MatchProcessingStatus.NEW,
                ),
            ],
        ),
    )
    service = _service(store)
    job = AllegroApplyJob(
        id=uuid4(),
        secret_id=secret_id,
        total=len(expected_pairs),
        status=JobStatus.PENDING,
    )
    service.start_apply_job = AsyncMock(return_value=job)

    returned_job = await service.start_auto_apply_single_matches(
        secret_id=secret_id,
        limit=limit,
    )

    service.start_apply_job.assert_awaited_once()
    call = service.start_apply_job.await_args
    assert call.kwargs["secret_id"] == secret_id
    decisions = call.kwargs["decisions"]
    assert [(d.transaction_id, d.payment_id) for d in decisions] == expected_pairs
    assert returned_job is job


@pytest.mark.anyio
async def test_preview_matches_fetches_and_caches_only_requested_page():
    service = _service()
    secret_id = uuid4()
    page = AllegroPageRequest(limit=5, offset=10)
    payment = _payment("p-1", "full-1")
    service.fetch_allegro_data = MagicMock(
        return_value=SimpleNamespace(payments=[payment])
    )
    service.enrichment_service.match_with_unmatched = AsyncMock(
        return_value=(
            [
                MatchResult(
                    tx=_tx(1), matches=[payment], status=MatchProcessingStatus.NEW
                )
            ],
            [],
        )
    )

    await service.preview_matches(
        user_id=uuid4(),
        secret_id=secret_id,
        vault_session_id="session-123",
        page=page,
    )

    service.fetch_allegro_data.assert_called_once()
    call = service.fetch_allegro_data.call_args
    assert call.kwargs["page"] == page
    assert (
        service.state_store.get_page_matches(secret_id=secret_id, page=page) is not None
    )
    assert (
        service.state_store.get_page_matches(
            secret_id=secret_id,
            page=AllegroPageRequest(limit=5, offset=0),
        )
        is None
    )


@pytest.mark.anyio
async def test_start_apply_job_uses_matches_loaded_from_cached_pages(monkeypatch):
    secret_id = uuid4()
    store = AllegroStateStore()
    page_one = AllegroPageRequest(limit=1, offset=0)
    page_two = AllegroPageRequest(limit=1, offset=1)
    p1 = _payment("p1", "full-1")
    p2 = _payment("p2", "full-2")
    store.put_page_matches(
        secret_id=secret_id,
        entry=app_module.AllegroPageMatchCacheEntry(
            page=page_one,
            login="u1",
            payments=[p1],
            matches=[
                MatchResult(tx=_tx(1), matches=[p1], status=MatchProcessingStatus.NEW)
            ],
        ),
    )
    store.put_page_matches(
        secret_id=secret_id,
        entry=app_module.AllegroPageMatchCacheEntry(
            page=page_two,
            login="u1",
            payments=[p2],
            matches=[
                MatchResult(tx=_tx(2), matches=[p2], status=MatchProcessingStatus.NEW)
            ],
        ),
    )
    service = _service(store)

    captured = {}

    def fake_create_task(coro):
        captured["scheduled"] = True
        coro.close()
        return object()

    monkeypatch.setattr(app_module, "create_task", fake_create_task)

    await service.start_apply_job(
        secret_id=secret_id,
        decisions=[MatchDecision(payment_id="p2", transaction_id=2)],
    )

    assert captured["scheduled"] is True


def test_clear_cached_page_delegates_to_state_store():
    store = AllegroStateStore()
    service = _service(store)
    secret_id = uuid4()
    page = AllegroPageRequest(limit=25, offset=0)

    store.put_page_matches(
        secret_id=secret_id,
        entry=app_module.AllegroPageMatchCacheEntry(
            page=page,
            login="u1",
            payments=[],
            matches=[],
        ),
    )

    assert service.clear_cached_page(secret_id=secret_id, page=page) is True
    assert store.get_page_matches(secret_id=secret_id, page=page) is None


def test_clear_cached_secret_delegates_to_state_store():
    store = AllegroStateStore()
    service = _service(store)
    secret_id = uuid4()
    page = AllegroPageRequest(limit=25, offset=0)

    store.put_page_matches(
        secret_id=secret_id,
        entry=app_module.AllegroPageMatchCacheEntry(
            page=page,
            login="u1",
            payments=[],
            matches=[],
        ),
    )

    assert service.clear_cached_secret(secret_id=secret_id) is True
    assert store.get_all_matches(secret_id=secret_id) == []


@pytest.mark.anyio
async def test_get_metrics_state_recreates_manager_if_missing():
    service = _service()
    service.state_store.metrics_manager = None

    state = await service.get_metrics_state()

    assert state.status == JobStatus.RUNNING
    assert service.state_store.metrics_manager is not None


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

    store = AllegroStateStore(metrics_manager=manager)
    service = _service(store)

    state = await service.get_metrics_state()

    manager.ensure_current.assert_awaited_once()
    assert state is expected_state


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
