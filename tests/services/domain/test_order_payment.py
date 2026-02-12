from datetime import date
from decimal import Decimal

import pytest

from services.domain.order_payment import OrderPayment
from services.domain.transaction import Currency, Transaction, TxTag, TxType

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def make_tx(
    *, amount: Decimal, tx_date: date, notes: str | None, tags: set[str] | None = None
) -> Transaction:
    return Transaction(
        id=1,
        date=tx_date,
        amount=amount,
        type=TxType.WITHDRAWAL,
        description="sample",
        tags=tags or set(),
        notes=notes,
        category=None,
        currency=DEFAULT_CURRENCY,
    )


def test_constructor_stores_all_fields_including_zero_and_negative_amounts():
    payment_zero = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("0"),
        details=[],
        tag_done=TxTag.allegro_done,
    )
    payment_negative = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("-12.34"),
        details=["Line"],
        tag_done=TxTag.allegro_done,
    )

    assert payment_zero.amount == Decimal("0")
    assert payment_zero.details == []
    assert payment_negative.amount == Decimal("-12.34")
    assert payment_negative.tag_done == TxTag.allegro_done


def test_flatten_details_returns_empty_string_for_empty_list():
    payment = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("1.00"),
        details=[],
        tag_done=TxTag.allegro_done,
    )

    assert payment.flatten_details() == ""


def test_flatten_details_joins_multiple_lines_with_newlines():
    payment = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("1.00"),
        details=["first", "second", "third"],
        tag_done=TxTag.allegro_done,
    )

    assert payment.flatten_details() == "first\nsecond\nthird"


@pytest.mark.parametrize(
    ("payment_amount", "other_amount", "other_date", "expected"),
    [
        (Decimal("10.00"), Decimal("10.00"), date(2025, 1, 10), True),
        (Decimal("10.00"), Decimal("-10.00"), date(2025, 1, 16), True),
        (Decimal("10.00"), Decimal("10.00"), date(2025, 1, 17), False),
        (Decimal("10.00"), Decimal("10.00"), date(2025, 1, 9), False),
        (Decimal("10.00"), Decimal("9.99"), date(2025, 1, 10), False),
        (Decimal("0"), Decimal("0"), date(2025, 1, 12), True),
    ],
)
def test_compare_covers_amount_and_date_tolerance_branches(
    payment_amount: Decimal,
    other_amount: Decimal,
    other_date: date,
    expected: bool,
):
    payment = OrderPayment(
        date=date(2025, 1, 10),
        amount=payment_amount,
        details=["Order"],
        tag_done=TxTag.allegro_done,
    )
    other = make_tx(amount=other_amount, tx_date=other_date, notes=None)

    assert payment.compare(other) is expected


def test_build_tx_update_raises_value_error_when_details_are_empty():
    payment = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("10.00"),
        details=[],
        tag_done=TxTag.allegro_done,
    )
    tx = make_tx(amount=Decimal("10.00"), tx_date=date(2025, 1, 10), notes=None)

    with pytest.raises(ValueError):
        payment.build_tx_update(tx)


def test_build_tx_update_adds_details_to_notes_when_notes_missing():
    payment = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("10.00"),
        details=["Order #123"],
        tag_done=TxTag.allegro_done,
    )
    tx = make_tx(amount=Decimal("10.00"), tx_date=date(2025, 1, 10), notes=None)

    update = payment.build_tx_update(tx)

    assert update.notes == "Order #123"
    assert set(update.tags or []) == {TxTag.allegro_done}


def test_build_tx_update_keeps_notes_none_when_details_already_present_case_insensitive():
    payment = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("10.00"),
        details=["order #abc"],
        tag_done=TxTag.allegro_done,
    )
    tx = make_tx(
        amount=Decimal("10.00"),
        tx_date=date(2025, 1, 10),
        notes="Existing note has ORDER #ABC inside",
        tags={TxTag.action_req},
    )

    update = payment.build_tx_update(tx)

    assert update.notes is None
    assert set(update.tags or []) == {TxTag.action_req, TxTag.allegro_done}


def test_build_tx_update_appends_to_existing_notes_when_details_not_present():
    payment = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("10.00"),
        details=["line one", "line two"],
        tag_done=TxTag.allegro_done,
    )
    tx = make_tx(
        amount=Decimal("10.00"),
        tx_date=date(2025, 1, 10),
        notes="existing",
        tags={TxTag.allegro_done},
    )

    update = payment.build_tx_update(tx)

    assert update.notes == "existing\nline one\nline two"
    assert set(update.tags or []) == {TxTag.allegro_done}


def test_build_tx_update_raises_type_error_when_details_contain_none():
    payment = OrderPayment(
        date=date(2025, 1, 10),
        amount=Decimal("10.00"),
        details=[None],  # type: ignore[list-item]
        tag_done=TxTag.allegro_done,
    )
    tx = make_tx(amount=Decimal("10.00"), tx_date=date(2025, 1, 10), notes=None)

    with pytest.raises(TypeError):
        payment.build_tx_update(tx)
