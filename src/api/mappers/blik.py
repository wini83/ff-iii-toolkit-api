from collections.abc import Iterable

from api.models.blik_files import MatchResult as ApiMatchResult
from api.models.blik_files import SimplifiedRecord, SimplifiedTx, StatisticsResponse
from services.domain.bank_record import BankRecord
from services.domain.match_result import MatchResult as DomainMatchResult
from services.domain.metrics import BlikStatisticsMetrics
from services.domain.transaction import Transaction


def map_tx_to_simplified(tx: Transaction) -> SimplifiedTx:
    """
    Domain Transaction -> API SimplifiedTx

    Contract-stable.
    UI-safe.
    Deterministic.
    """
    return SimplifiedTx(
        id=tx.id,
        date=tx.date,
        amount=float(tx.amount),
        description=tx.description,
        tags=sorted(tx.tags),  # set -> list, stabilna kolejność
        notes=tx.notes or "",  # UI nie lubi None
        category=tx.category or "",
    )


def map_bank_record_to_simplified(record: BankRecord) -> SimplifiedRecord:
    """
    BankRecord -> SimplifiedRecord

    amount             = kwota w walucie rachunku
    operation_amount   = kwota w walucie transakcji

    Brak FX = brak magii.
    """
    return SimplifiedRecord(
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

    simplified_tx = map_tx_to_simplified(result.tx)

    records: list[BankRecord] = []
    for m in result.matches:
        if not isinstance(m, BankRecord):
            raise TypeError(f"Expected BankRecord in matches, got {type(m).__name__}")
        records.append(m)

    simplified_matches = map_bank_records_to_simplified(records)

    return ApiMatchResult(
        tx=simplified_tx,
        matches=simplified_matches,
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


def map_blik_metrics_to_api(metrics: BlikStatisticsMetrics) -> StatisticsResponse:
    return StatisticsResponse(
        total_transactions=metrics.total_transactions,
        single_part_transactions=metrics.single_part_transactions,
        uncategorized_transactions=metrics.uncategorized_transactions,
        filtered_by_description_exact=metrics.filtered_by_description_exact,
        filtered_by_description_partial=metrics.filtered_by_description_partial,
        not_processed_transactions=metrics.not_processed_transactions,
        not_processed_by_month=metrics.not_processed_by_month,
        inclomplete_procesed_by_month=metrics.inclomplete_procesed_by_month,
    )
