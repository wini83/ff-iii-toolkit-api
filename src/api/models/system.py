from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str | None = None
    external_services: dict[str, str] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VersionResponse(BaseModel):
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BootstrapPayload(BaseModel):
    username: str
    password: str
