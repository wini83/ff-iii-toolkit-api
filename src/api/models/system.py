from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    database: Literal["ok", "error"]
    external_services: dict[str, str] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VersionResponse(BaseModel):
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BootstrapResponse(BaseModel):
    bootstrapped: bool


class BootstrapPayload(BaseModel):
    username: str
    password: str
