from ff_iii_luciferin.api.transaction_update import TransactionUpdate as ff_tu
from ff_iii_luciferin.domain.models import (
    SimplifiedAccountRef as ff_account_ref,
)
from ff_iii_luciferin.domain.models import (
    SimplifiedCategory,
    SimplifiedTx,
)

from services.domain.transaction import (
    AccountRef,
    AccountType,
    Category,
    Currency,
    FXContext,
    Transaction,
    TransactionUpdate,
    TxType,
)


def tx_from_ff_tx(tx: SimplifiedTx) -> Transaction:
    fx = None
    if tx.fx is not None:
        fx = FXContext(
            original_currency=Currency(
                code=tx.fx.original_currency.code,
                symbol=tx.fx.original_currency.symbol,
                decimals=tx.fx.original_currency.decimals,
            ),
            original_amount=tx.fx.original_amount,
        )

    source_account = getattr(tx, "source_account", None)
    if source_account is not None:
        source_account = account_ref_from_ff_account_ref(source_account)

    destination_account = getattr(tx, "destination_account", None)
    if destination_account is not None:
        destination_account = account_ref_from_ff_account_ref(destination_account)

    return Transaction(
        id=tx.id,
        date=tx.date,
        amount=tx.amount,
        type=TxType(tx.type.value),
        description=tx.description,
        tags=set(tx.tags),
        notes=tx.notes,
        category=(
            Category(id=tx.category.id, name=tx.category.name) if tx.category else None
        ),
        currency=Currency(
            code=tx.currency.code,
            symbol=tx.currency.symbol,
            decimals=tx.currency.decimals,
        ),
        fx=fx,
        source_account=source_account,
        destination_account=destination_account,
    )


def category_from_ff_category(cat: SimplifiedCategory) -> Category:
    return Category(id=cat.id, name=cat.name)


def account_ref_from_ff_account_ref(account: ff_account_ref) -> AccountRef:
    return AccountRef(
        id=account.id,
        name=account.name,
        type=AccountType(account.type.value),
        iban=account.iban,
    )


def tx_update_to_ff_tx_update(tu: TransactionUpdate) -> ff_tu:
    return ff_tu(
        description=tu.description,
        notes=tu.notes,
        tags=tu.tags,
        category_id=tu.category_id,
    )
