from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fireflyiii_enricher_core.firefly_client import FireflyClient

from api.models.tx import ScreeningResponse
from api.routers.blik_files import firefly_dep
from services.auth import get_current_user
from services.tx_processor import (
    CategoryApplyError,
    SimplifiedCategory,
    SimplifiedTx,
    TransactionProcessor,
)

router = APIRouter(prefix="/api/tx", tags=["transactions"])

_tx_cache: list[SimplifiedTx] | None = None


@router.get(
    "/next",
    dependencies=[Depends(get_current_user)],
    response_model=ScreeningResponse,
    responses={
        200: {"description": "Next transaction for screening"},
        204: {"description": "No more transactions to screen"},
        502: {"description": "Firefly error"},
    },
)
async def get_tx(
    order: Literal["asc", "desc"] = "asc",
    after_id: int | None = None,
    firefly: FireflyClient = Depends(firefly_dep),
):
    global _tx_cache
    cats: list[SimplifiedCategory] = []
    try:
        processor = TransactionProcessor(firefly)
        cats = await processor.get_categories()
        if not _tx_cache:
            _tx_cache = await processor.get_txs_for_screening()
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if len(_tx_cache) == 0:
        raise HTTPException(status_code=204)
    txs = _tx_cache if order == "asc" else list(reversed(_tx_cache))
    diag = ""
    for tx in txs[:10]:
        diag += f"{tx.id};"
    print(diag)
    tx_result: SimplifiedTx | None = None

    if (after_id is None) and txs:
        tx_result = txs[0]

    for idx, tx in enumerate(txs):
        print(f"idx:{idx}; id:{tx.id}")
        if tx.id == str(after_id):
            tx_result = txs[idx + 1] if idx + 1 < len(txs) else None
            break
    if not tx_result:
        # after_id nie znaleziony → fallback
        tx_result = txs[0]
    return ScreeningResponse(tx=tx_result, categories=cats)


@router.post(
    "/{tx_id}/category/{category_id}",
    status_code=204,
    dependencies=[Depends(get_current_user)],
)
async def apply_category(
    tx_id: int,
    category_id: int,
    firefly: FireflyClient = Depends(firefly_dep),
):
    processor = TransactionProcessor(firefly)
    try:
        await processor.apply_category(tx_id, category_id)
    except CategoryApplyError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
