from datetime import date
from decimal import Decimal

from api.mappers.tx import map_tx_to_api
from api.models.tx import AccountType as ApiAccountType
from api.models.tx import SimplifiedAccountRef
from services.domain.transaction import (
    AccountRef,
    Currency,
    FXContext,
    Transaction,
    TxType,
)
from services.domain.transaction import (
    AccountType as DomainAccountType,
)


def test_map_tx_to_api_includes_account_refs():
    tx = Transaction(
        id=1,
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="Test",
        tags={"b", "a"},
        notes=None,
        category=None,
        currency=Currency(code="PLN", symbol="zl", decimals=2),
        fx=FXContext(
            original_currency=Currency(code="EUR", symbol="€", decimals=2),
            original_amount=Decimal("9.50"),
        ),
        source_account=AccountRef(
            id=11,
            name="Main account",
            type=DomainAccountType.ASSET,
            iban="PL123",
        ),
        destination_account=AccountRef(
            id=12,
            name="Store",
            type=DomainAccountType.EXPENSE,
            iban=None,
        ),
    )

    resp = map_tx_to_api(tx)

    assert resp.source_account == SimplifiedAccountRef(
        id=11,
        name="Main account",
        type=ApiAccountType.ASSET,
        iban="PL123",
    )
    assert resp.destination_account == SimplifiedAccountRef(
        id=12,
        name="Store",
        type=ApiAccountType.EXPENSE,
        iban=None,
    )
    assert resp.tags == ["a", "b"]
    assert resp.fx_amount == 9.5
    assert resp.fx_currency == "EUR"
