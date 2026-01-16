from api.models.tx import SimplifiedCategory, SimplifiedTx
from services.domain.transaction import Category, Transaction


def map_tx_to_api(tx: Transaction) -> SimplifiedTx:
    return SimplifiedTx(
        id=tx.id,
        date=tx.date,
        amount=float(tx.amount),
        description=tx.description,
        tags=sorted(tx.tags),
        notes=tx.notes or "",
        category=tx.category or "",
    )


def map_category_to_api(cat: Category) -> SimplifiedCategory:
    return SimplifiedCategory(id=cat.id, name=cat.name)
