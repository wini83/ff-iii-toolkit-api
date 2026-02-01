import asyncio
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models.blik_files import ApplyPayload
from services.blik_application_service import BlikApplicationService
from services.domain.bank_record import BankRecord
from services.domain.match_result import MatchResult
from services.domain.metrics import BlikStatisticsMetrics
from services.domain.transaction import Currency, Transaction, TxType
from services.exceptions import (
    ExternalServiceFailed,
    FileNotFound,
    InvalidFileId,
    InvalidMatchSelection,
)
from services.firefly_base_service import FireflyServiceError
from services.firefly_blik_service import FireflyBlikService
from settings import settings
from utils.encoding import encode_base64url

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


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

    service = BlikApplicationService(blik_service=MagicMock(spec=FireflyBlikService))

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
    service = BlikApplicationService(blik_service=MagicMock(spec=FireflyBlikService))

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

    blik_service = MagicMock(spec=FireflyBlikService)
    blik_service.match = AsyncMock(return_value=matches)
    service = BlikApplicationService(blik_service=blik_service)

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

    blik_service = MagicMock(spec=FireflyBlikService)
    blik_service.match = AsyncMock(side_effect=FireflyServiceError("boom"))
    service = BlikApplicationService(blik_service=blik_service)

    with (
        patch("services.blik_application_service.BankCSVReader") as reader_cls,
        patch("services.blik_application_service.os.path.exists", return_value=True),
    ):
        reader_cls.return_value.parse.return_value = csv_records
        with pytest.raises(ExternalServiceFailed):
            asyncio.run(service.preview_matches(encoded_id=encoded_id))


def test_preview_csv_rejects_invalid_file_id():
    blik_service = MagicMock(spec=FireflyBlikService)
    service = BlikApplicationService(blik_service=blik_service)
    bad_id = encode_base64url("../bad")

    with pytest.raises(InvalidFileId):
        asyncio.run(service.preview_csv(encoded_id=bad_id))


def test_preview_csv_raises_when_file_missing():
    blik_service = MagicMock(spec=FireflyBlikService)
    service = BlikApplicationService(blik_service=blik_service)
    encoded_id = encode_base64url("missing")

    with (
        patch("services.blik_application_service.os.path.exists", return_value=False),
        pytest.raises(FileNotFound),
    ):
        asyncio.run(service.preview_csv(encoded_id=encoded_id))


def test_apply_matches_updates_transactions():
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
    evidence = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="BLIK payment",
        recipient="ACME",
        operation_amount=Decimal("10.00"),
    )
    match = MatchResult(tx=tx, matches=[evidence])

    blik_service = MagicMock(spec=FireflyBlikService)
    blik_service.apply_match = AsyncMock()
    service = BlikApplicationService(blik_service=blik_service)
    service._matches_cache[encoded_id] = [match]

    payload = ApplyPayload(tx_indexes=[1])
    response = asyncio.run(
        service.apply_matches(encoded_id=encoded_id, payload=payload)
    )

    blik_service.apply_match.assert_awaited_once_with(tx=tx, evidence=evidence)
    assert response.file_id == encoded_id
    assert response.updated == 1
    assert response.errors == []


def test_apply_matches_rejects_non_single_match():
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
    evidence_a = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="BLIK payment",
        recipient="ACME",
        operation_amount=Decimal("10.00"),
    )
    evidence_b = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="BLIK payment",
        recipient="Shop",
        operation_amount=Decimal("10.00"),
    )
    match = MatchResult(tx=tx, matches=[evidence_a, evidence_b])

    blik_service = MagicMock(spec=FireflyBlikService)
    service = BlikApplicationService(blik_service=blik_service)
    service._matches_cache[encoded_id] = [match]

    payload = ApplyPayload(tx_indexes=[1])
    with pytest.raises(InvalidMatchSelection):
        asyncio.run(service.apply_matches(encoded_id=encoded_id, payload=payload))


def test_get_statistics_fetches_once_and_caches():
    metrics = BlikStatisticsMetrics(
        total_transactions=10,
        fetching_duration_ms=5,
        single_part_transactions=7,
        uncategorized_transactions=2,
        filtered_by_description_exact=3,
        filtered_by_description_partial=1,
        not_processed_transactions=4,
        not_processed_by_month={"2024-01": 2},
        inclomplete_procesed_by_month={"2024-01": 1},
        time_stamp=datetime(2024, 1, 1),
    )
    blik_service = MagicMock(spec=FireflyBlikService)
    blik_service.fetch_metrics = AsyncMock(return_value=metrics)
    service = BlikApplicationService(blik_service=blik_service)

    async def run():
        first = await service.get_statistics()
        second = await service.get_statistics()
        return first, second

    stats_first, stats_second = asyncio.run(run())

    assert blik_service.fetch_metrics.await_count == 1
    assert stats_first.total_transactions == 10
    assert stats_second.filtered_by_description_exact == 3
