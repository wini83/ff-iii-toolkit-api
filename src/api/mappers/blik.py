import hashlib
from collections.abc import Iterable

from api.mappers.job_status import map_status
from api.mappers.tx import DOMAIN_TO_API_STATUS, map_tx_to_api
from api.models.blik_files import (
    ApplyDecisionsPayload,
    ApplyJobResponse,
    ApplyOutcomeResponse,
    SimplifiedRecord,
)
from api.models.blik_files import (
    MatchResult as ApiMatchResult,
)
from services.domain.bank_record import BankRecord
from services.domain.blik import ApplyOutcome, BlikApplyJob, MatchDecision
from services.domain.match_result import MatchResult as DomainMatchResult
from services.domain.transaction import Transaction


def build_blik_match_id(*, transaction_id: int, record: BankRecord) -> str:
    payload = "|".join(
        [
            str(transaction_id),
            record.date.isoformat(),
            str(record.amount),
            str(record.operation_amount),
            record.recipient,
            record.details,
            record.sender,
            record.operation_currency,
            record.account_currency,
            record.sender_account,
            record.recipient_account,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def map_bank_record_to_simplified(record: BankRecord) -> SimplifiedRecord:
    """
    BankRecord -> SimplifiedRecord

    amount             = kwota w walucie rachunku
    operation_amount   = kwota w walucie transakcji

    Brak FX = brak magii.
    """
    return SimplifiedRecord(
        match_id=None,
        date=record.date,
        amount=float(record.amount),  # waluta rachunku
        details=record.details,
        recipient=record.recipient,
        operation_amount=float(record.operation_amount),  # waluta transakcji
        sender=record.sender,
        operation_currency=record.operation_currency,
        account_currency=record.account_currency,
        sender_account=record.sender_account,
        recipient_account=record.recipient_account,
    )


def map_bank_records_to_simplified(
    records: Iterable[BankRecord],
) -> list[SimplifiedRecord]:
    """
    Bulk mapper: BankRecord -> SimplifiedRecord

    amount           = kwota w walucie rachunku
    operation_amount = kwota w walucie transakcji

    Brak FX, brak magii, pełna transparentność.
    """
    return [
        SimplifiedRecord(
            match_id=None,
            date=r.date,
            amount=float(r.amount),  # waluta rachunku
            details=r.details,
            recipient=r.recipient,
            operation_amount=float(r.operation_amount),  # waluta transakcji
            sender=r.sender,
            operation_currency=r.operation_currency,
            account_currency=r.account_currency,
            sender_account=r.sender_account,
            recipient_account=r.recipient_account,
        )
        for r in records
    ]


def map_match_result_to_api(
    result: DomainMatchResult,
) -> ApiMatchResult:
    """
    Domain MatchResult -> API MatchResult

    Adapter legacy-safe.
    Zero UI changes.
    """
    if not isinstance(result.tx, Transaction):
        raise TypeError(f"Expected Transaction as tx, got {type(result.tx).__name__}")

    simplified_tx = map_tx_to_api(result.tx)
    tx_id = int(result.tx.id)

    records: list[BankRecord] = []
    for m in result.matches:
        if not isinstance(m, BankRecord):
            raise TypeError(f"Expected BankRecord in matches, got {type(m).__name__}")
        records.append(m)

    simplified_matches = [
        SimplifiedRecord(
            match_id=build_blik_match_id(transaction_id=tx_id, record=record),
            date=record.date,
            amount=float(record.amount),
            details=record.details,
            recipient=record.recipient,
            operation_amount=float(record.operation_amount),
            sender=record.sender,
            operation_currency=record.operation_currency,
            account_currency=record.account_currency,
            sender_account=record.sender_account,
            recipient_account=record.recipient_account,
        )
        for record in records
    ]

    return ApiMatchResult(
        tx=simplified_tx,
        matches=simplified_matches,
        status=DOMAIN_TO_API_STATUS[result.status],
    )


def map_match_results_to_api(
    results: Iterable[DomainMatchResult],
) -> list[ApiMatchResult]:
    """
    Bulk mapper: Domain MatchResult -> API MatchResult

    UI-safe
    legacy-preserving
    zero magic
    """
    return [map_match_result_to_api(result) for result in results]


def map_apply_outcome_to_response(outcome: ApplyOutcome) -> ApplyOutcomeResponse:
    return ApplyOutcomeResponse(
        transaction_id=outcome.transaction_id,
        selected_match_id=outcome.selected_match_id,
        status=outcome.status,
        reason=outcome.reason,
    )


def map_job_to_response(job: BlikApplyJob) -> ApplyJobResponse:
    return ApplyJobResponse(
        id=job.id,
        file_id=job.file_id,
        status=map_status(job.status),
        total=job.total,
        applied=job.applied,
        failed=job.failed,
        started_at=job.started_at,
        finished_at=job.finished_at,
        results=[map_apply_outcome_to_response(result) for result in job.results],
    )


def map_payload_to_decisions(payload: ApplyDecisionsPayload) -> list[MatchDecision]:
    return [
        MatchDecision(
            transaction_id=decision.transaction_id,
            selected_match_id=decision.selected_match_id,
        )
        for decision in payload.decisions
    ]
