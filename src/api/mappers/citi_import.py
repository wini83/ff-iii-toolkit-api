from __future__ import annotations

from collections.abc import Iterable

from api.models.citi_import import CitiImportParseResponse, CitiImportRecord
from services.citi_import.service import CitiParsePreview
from services.domain.bank_record import BankRecord


def map_bank_record_to_api(record: BankRecord) -> CitiImportRecord:
    return CitiImportRecord(
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


def map_bank_records_to_api(records: Iterable[BankRecord]) -> list[CitiImportRecord]:
    return [map_bank_record_to_api(record) for record in records]


def map_preview_to_response(preview: CitiParsePreview) -> CitiImportParseResponse:
    return CitiImportParseResponse(
        file_id=preview.file_id,
        record_count=preview.record_count,
        preview=map_bank_records_to_api(preview.preview),
        warnings=list(preview.warnings),
    )
