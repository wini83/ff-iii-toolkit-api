import calendar
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from ff_iii_luciferin.api import FireflyClient
from services.firefly_service import (
    CategoryApplyError,
    TransactionProcessor,
)

from api.models.tx import ScreeningMonthResponse, TxTag
from api.routers.blik_files import firefly_dep
from services.auth import get_current_user


def month_range(year: int, month: int) -> tuple[date, date]:
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


router = APIRouter(prefix="/api/tx", tags=["transactions"])


@router.get(
    "/screening",
    dependencies=[Depends(get_current_user)],
    response_model=ScreeningMonthResponse,
    responses={
        200: {"description": "Uncategorized transactions for given month"},
        204: {"description": "No uncategorized transactions in this month"},
        400: {"description": "Invalid year or month"},
        502: {"description": "Firefly error"},
    },
)
async def get_screening_month(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    firefly: FireflyClient = Depends(firefly_dep),
):
    try:
        processor = TransactionProcessor(firefly)
        start_date, end_date = month_range(year=year, month=month)
        cats = await processor.get_categories()
        txs = await processor.get_txs_for_screening(
            start_date=start_date, end_date=end_date
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if len(txs) == 0:
        raise HTTPException(status_code=204)
    return ScreeningMonthResponse(
        year=year, month=month, remaining=len(txs), transactions=txs, categories=cats
    )


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
    global _tx_cache
    try:
        await processor.apply_category(tx_id, category_id)
    except CategoryApplyError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post(
    "/{tx_id}/tag/",
    status_code=204,
    dependencies=[Depends(get_current_user)],
)
async def apply_tag(
    tx_id: int,
    tag: TxTag = Query(...),
    firefly: FireflyClient = Depends(firefly_dep),
):
    processor = TransactionProcessor(firefly)
    global _tx_cache
    try:
        await processor.add_tag(tx_id=tx_id, tag=tag)
    except CategoryApplyError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
