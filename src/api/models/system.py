from pydantic import BaseModel,Field
from datetime import datetime,timezone


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str | None = None
    external_services: dict[str, str] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VersionResponse(BaseModel):
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))