from fastapi import APIRouter

from src.api.models.system import HealthResponse


router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()