import io
from datetime import date
from decimal import Decimal

import pytest

from services.csv_reader import BankCSVReader, parse_amount, parse_pl_date

REQUIRED_HEADER = (
    "Data transakcji;Kwota w walucie rachunku;Kwota operacji;"
    "Nazwa nadawcy;Nazwa odbiorcy;Szczegóły transakcji;Waluta operacji;"
    "Waluta rachunku;Numer rachunku nadawcy;Numer rachunku odbiorcy"
)


def _patch_open_with_content(monkeypatch: pytest.MonkeyPatch, content: str) -> None:
    def fake_open(*args, **kwargs):  # noqa: ANN002, ANN003
        return io.StringIO(content)

    monkeypatch.setattr("builtins.open", fake_open)


def test_parse_pl_date_valid_and_invalid():
    assert parse_pl_date(" 09-11-2025 ") == date(2025, 11, 9)

    with pytest.raises(ValueError):
        parse_pl_date("2025-11-09")


def test_parse_amount_normalizes_and_raises_for_invalid_input():
    parsed = parse_amount(" 1 234,50 ")

    assert parsed == Decimal("1234.50")

    with pytest.raises(ValueError):
        parse_amount("not-a-number")


def test_bank_csv_reader_parse_valid_csv(monkeypatch: pytest.MonkeyPatch):
    content = (
        "ignored metadata line\n"
        f"{REQUIRED_HEADER}\n"
        "09-11-2025;1 234,50;1 234,50;Jan Kowalski;Shop A;Order 1;PLN;PLN;111;222\n"
        "10-11-2025;-10,00;-10,00;Anna;Store B;Refund;PLN;PLN;333;444\n"
    )
    _patch_open_with_content(monkeypatch, content)

    result = BankCSVReader("dummy.csv").parse()

    assert len(result) == 2
    assert result[0].date == date(2025, 11, 9)
    assert result[0].amount == Decimal("1234.50")
    assert result[0].operation_amount == Decimal("1234.50")
    assert result[0].sender == "Jan Kowalski"
    assert result[0].recipient == "Shop A"
    assert result[0].details == "Order 1"
    assert result[0].operation_currency == "PLN"
    assert result[0].account_currency == "PLN"
    assert result[0].sender_account == "111"
    assert result[0].recipient_account == "222"

    assert result[1].date == date(2025, 11, 10)
    assert result[1].amount == Decimal("-10.00")


def test_bank_csv_reader_parse_empty_file_raises_stop_iteration(
    monkeypatch: pytest.MonkeyPatch,
):
    _patch_open_with_content(monkeypatch, "")

    with pytest.raises(StopIteration):
        BankCSVReader("dummy.csv").parse()


def test_bank_csv_reader_parse_malformed_header_raises_key_error(
    monkeypatch: pytest.MonkeyPatch,
):
    content = "ignored metadata line\ntotally_wrong_header\nsome;row;values\n"
    _patch_open_with_content(monkeypatch, content)

    with pytest.raises(KeyError):
        BankCSVReader("dummy.csv").parse()


def test_bank_csv_reader_parse_malformed_row_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
):
    content = (
        "ignored metadata line\n"
        f"{REQUIRED_HEADER}\n"
        "invalid-date;12,00;12,00;A;B;C;PLN;PLN;1;2\n"
    )
    _patch_open_with_content(monkeypatch, content)

    with pytest.raises(ValueError):
        BankCSVReader("dummy.csv").parse()


def test_bank_csv_reader_parse_missing_required_column_raises_key_error(
    monkeypatch: pytest.MonkeyPatch,
):
    header_missing_sender = (
        "Data transakcji;Kwota w walucie rachunku;Kwota operacji;"
        "Nazwa odbiorcy;Szczegóły transakcji;Waluta operacji;"
        "Waluta rachunku;Numer rachunku nadawcy;Numer rachunku odbiorcy"
    )
    content = (
        "ignored metadata line\n"
        f"{header_missing_sender}\n"
        "09-11-2025;12,00;12,00;Shop;Details;PLN;PLN;1;2\n"
    )
    _patch_open_with_content(monkeypatch, content)

    with pytest.raises(KeyError):
        BankCSVReader("dummy.csv").parse()


def test_bank_csv_reader_parse_accepts_extra_columns(monkeypatch: pytest.MonkeyPatch):
    header_with_extra = REQUIRED_HEADER + ";Unused column"
    content = (
        "ignored metadata line\n"
        f"{header_with_extra}\n"
        "09-11-2025;12,00;12,00;Jan;Shop;Details;PLN;PLN;1;2;extra\n"
    )
    _patch_open_with_content(monkeypatch, content)

    result = BankCSVReader("dummy.csv").parse()

    assert len(result) == 1
    assert result[0].details == "Details"
    assert result[0].amount == Decimal("12.00")
