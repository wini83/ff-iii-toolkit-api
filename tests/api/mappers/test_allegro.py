from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from api.mappers.allegro import (
    map_allegro_metrics_state_to_response,
    map_allegro_payment_to_response,
    map_allegro_payments_to_response,
    map_job_to_response,
    map_match_result_to_api,
    map_match_results_to_api,
    map_payload_to_decisions,
)
from api.models.allegro import ApplyDecision, ApplyPayload
from services.domain.allegro import (
    AllegroApplyJob,
    AllegroOrderPayment,
    ApplyJobStatus,
)
from services.domain.match_result import MatchResult
from services.domain.metrics import AllegroMetrics
from services.domain.transaction import Currency, Transaction, TxType
from services.domain.transaction import TxTag as DomainTxTag
from services.tx_stats.models import JobStatus, MetricsState


def _tx():
    return Transaction(
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        id=1,
        type=TxType.WITHDRAWAL,
        description="desc",
        tags={"b", "a"},
        notes=None,
        category=None,
        currency=Currency(code="PLN", symbol="zl", decimals=2),
        fx=None,
    )


def _payment():
    return AllegroOrderPayment(
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        details=["d1"],
        tag_done=DomainTxTag.allegro_done,
        is_balanced=True,
        allegro_login="login",
        external_short_id="short",
        external_id="full",
    )


def test_map_allegro_metrics_state_to_response_with_result():
    metrics = AllegroMetrics(
        total_transactions=10,
        fetching_duration_ms=2500,
        allegro_transactions=4,
        not_processed_allegro_transactions=2,
        not_processed_by_month={"2024-01": 2},
        time_stamp=datetime.now(UTC),
    )
    state = MetricsState(
        status=JobStatus.DONE,
        result=metrics,
        error=None,
        progress=None,
        last_updated_at=None,
    )

    resp = map_allegro_metrics_state_to_response(state)

    assert resp.status == "done"
    assert resp.result is not None
    assert resp.result.total_transactions == 10
    assert resp.result.not_processed__allegro_transactions == 2
    assert resp.result.fetch_seconds == pytest.approx(2.5)


def test_map_allegro_metrics_state_to_response_without_result():
    state = MetricsState(
        status=JobStatus.PENDING,
        result=None,
        error="x",
        progress="p",
        last_updated_at=None,
    )

    resp = map_allegro_metrics_state_to_response(state)

    assert resp.status == "pending"
    assert resp.result is None
    assert resp.error == "x"
    assert resp.progress == "p"


def test_map_allegro_payment_to_response():
    payment = _payment()

    resp = map_allegro_payment_to_response(payment)

    assert resp.amount == float(payment.amount)
    assert resp.external_id == payment.external_id
    assert resp.external_short_id == payment.external_short_id


def test_map_allegro_payments_to_response_empty():
    class Dummy:
        payments = []

    assert map_allegro_payments_to_response(Dummy()) == []


def test_map_match_result_to_api_happy_path():
    tx = _tx()
    payment = _payment()

    result = map_match_result_to_api(MatchResult(tx=tx, matches=[payment]))

    assert result.tx.id == tx.id
    assert result.matches[0].external_id == payment.external_id


def test_map_match_result_to_api_invalid_tx():
    with pytest.raises(TypeError):
        map_match_result_to_api(MatchResult(tx="nope", matches=[]))


def test_map_match_result_to_api_invalid_match():
    tx = _tx()
    with pytest.raises(TypeError):
        map_match_result_to_api(MatchResult(tx=tx, matches=[object()]))


def test_map_match_results_to_api_bulk():
    tx = _tx()
    payment = _payment()
    results = map_match_results_to_api(
        [MatchResult(tx=tx, matches=[payment]), MatchResult(tx=tx, matches=[payment])]
    )
    assert len(results) == 2


def test_map_job_to_response():
    job = AllegroApplyJob(
        id=uuid4(),
        secret_id=uuid4(),
        total=3,
        status=ApplyJobStatus.DONE,
        started_at=datetime.now(UTC),
        applied=2,
        failed=1,
    )

    resp = map_job_to_response(job)

    assert resp.status.value.lower() == "done"
    assert resp.total == 3
    assert resp.applied == 2
    assert resp.failed == 1


def test_map_payload_to_decisions():
    payload = ApplyPayload(
        decisions=[
            ApplyDecision(payment_id="p1", transaction_id=1, strategy="force"),
            ApplyDecision(payment_id="p2", transaction_id=2, strategy="manual"),
        ]
    )

    decisions = map_payload_to_decisions(payload)

    assert decisions[0].payment_id == "p1"
    assert decisions[0].strategy == "force"
    assert decisions[1].transaction_id == 2
