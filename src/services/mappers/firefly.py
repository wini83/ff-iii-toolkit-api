from ff_iii_luciferin.api.transaction_update import TransactionUpdate as ff_tu
from ff_iii_luciferin.domain.models import SimplifiedCategory, SimplifiedTx

from services.domain.transaction import (
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
    )


def category_from_ff_category(cat: SimplifiedCategory) -> Category:
    return Category(id=cat.id, name=cat.name)


def tx_update_to_ff_tx_update(tu: TransactionUpdate) -> ff_tu:
    return ff_tu(
        description=tu.description,
        notes=tu.notes,
        tags=tu.tags,
        category_id=tu.category_id,
    )
