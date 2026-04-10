from datetime import date
from decimal import Decimal

from ff_iii_luciferin.domain.models import (
    AccountType as FfAccountType,
)
from ff_iii_luciferin.domain.models import (
    Currency as FfCurrency,
)
from ff_iii_luciferin.domain.models import (
    SimplifiedAccountRef as FfAccountRef,
)
from ff_iii_luciferin.domain.models import (
    SimplifiedTx,
)
from ff_iii_luciferin.domain.models import (
    TxType as FfTxType,
)

from services.domain.transaction import AccountRef, AccountType, TxType
from services.mappers.firefly import tx_from_ff_tx


def test_tx_from_ff_tx_maps_account_refs():
    tx = SimplifiedTx(
        id=1,
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        type=FfTxType.WITHDRAWAL,
        description="Test",
        tags=[],
        notes=None,
        category=None,
        currency=FfCurrency(code="PLN", symbol="zl", decimals=2),
        fx=None,
        source_account=FfAccountRef(
            id=11,
            name="Main account",
            type=FfAccountType.ASSET,
            iban="PL123",
        ),
        destination_account=FfAccountRef(
            id=12,
            name="Store",
            type=FfAccountType.EXPENSE,
            iban=None,
        ),
    )

    result = tx_from_ff_tx(tx)

    assert result.type == TxType.WITHDRAWAL
    assert result.source_account == AccountRef(
        id=11,
        name="Main account",
        type=AccountType.ASSET,
        iban="PL123",
    )
    assert result.destination_account == AccountRef(
        id=12,
        name="Store",
        type=AccountType.EXPENSE,
        iban=None,
    )
