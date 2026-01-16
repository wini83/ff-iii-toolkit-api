from ff_iii_luciferin.api.transaction_update import TransactionUpdate as ff_tu
from ff_iii_luciferin.domain.models import SimplifiedCategory, SimplifiedTx

from services.domain.transaction import Category, Transaction, TransactionUpdate


def tx_from_ff_tx(tx: SimplifiedTx) -> Transaction:
    return Transaction(
        id=tx.id,
        date=tx.date,
        amount=tx.amount,
        description=tx.description,
        tags=set(tx.tags),
        notes=tx.notes,
        category=tx.category,
        currency="PLN",
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
