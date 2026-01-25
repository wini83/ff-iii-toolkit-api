from decimal import Decimal

from api.models.tx import SimplifiedCategory, SimplifiedTx
from services.domain.transaction import Category, Transaction


def to_api_amount(amount: Decimal, decimals: int) -> float:
    return float(amount.quantize(Decimal("1").scaleb(-decimals)))


def map_tx_to_api(tx: Transaction) -> SimplifiedTx:
    """
    Domain Transaction -> API SimplifiedTx

    Contract-stable.
    UI-safe.
    Deterministic.
    """

    amount = to_api_amount(tx.amount, tx.currency.decimals)
    fx_amount = None
    fx_currency = None
    if tx.fx is not None:
        fx_amount = to_api_amount(
            tx.fx.original_amount,
            tx.fx.original_currency.decimals,
        )
        fx_currency = tx.fx.original_currency.code

    return SimplifiedTx(
        id=tx.id,
        date=tx.date,
        amount=amount,
        description=tx.description,
        tags=sorted(tx.tags),  # set -> list, stabilna kolejność
        notes=tx.notes or "",  # UI nie lubi None
        category=tx.category.name if tx.category else None,
        type=tx.type.value,
        currency_symbol=tx.currency.symbol,
        currency_code=tx.currency.code,
        fx_amount=fx_amount,
        fx_currency=fx_currency,
    )


def map_category_to_api(cat: Category) -> SimplifiedCategory:
    return SimplifiedCategory(id=cat.id, name=cat.name)
