from fastapi import APIRouter, Depends

from services.guards import require_active_user

router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"],
    dependencies=[Depends(require_active_user)],
)
