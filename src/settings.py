import json
import os
from typing import Any

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env immediately
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)


class Settings(BaseSettings):
    FIREFLY_URL: str | None = None
    FIREFLY_TOKEN: str | None = None
    allowed_origins: Any = ["*"]
    DEMO_MODE: bool = False

    SECRET_KEY: str  # = Field(..., env="SECRET_KEY")
    PASSWORD_SET_TOKEN_PEPPER: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    PASSWORD_SET_TOKEN_EXPIRE_HOURS: int = 24
    APP_PUBLIC_URL: str | None = None
    BLIK_DESCRIPTION_FILTER: str = "BLIK - płatność w internecie"
    TAG_BLIK_DONE: str = "blik_done"
    MATCH_WITH_UNMATCHED_FUTURE_DAYS: int = 7
    TRANSACTION_SNAPSHOT_TTL_SECONDS: int = 300
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_COOKIE_NAME: str = "refresh_token"
    REFRESH_TOKEN_SECURE: bool = False
    VAULT_SESSION_COOKIE_NAME: str = "vault_session_id"
    VAULT_SESSION_TTL_SECONDS: int = 900
    VAULT_SESSION_SECURE: bool = False
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/app.db"

    @field_validator("allowed_origins", mode="before")
    def parse_allowed_origins(cls, v):
        if v is None:
            return ["*"]

        # Jeśli ktoś wpisze "*" → traktujemy jako wildcard
        if isinstance(v, str) and v.strip() == "*":
            return ["*"]

        # CSV: "a,b,c"
        if isinstance(v, str) and "," in v:
            return [item.strip() for item in v.split(",")]

        # JSON list: '["a","b"]'
        if isinstance(v, str) and v.strip().startswith("["):
            try:
                return json.loads(v)
            except Exception as e:
                raise ValueError("ALLOWED_ORIGINS must be valid JSON list") from e

        # jeśli to single string → zrób listę
        if isinstance(v, str):
            return [v]

        # jeśli to lista → OK
        if isinstance(v, list):
            return v

        raise ValueError(f"Invalid ALLOWED_ORIGINS format: {v}")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


# pyright: reportCallIssue=false
settings = Settings()  # type: ignore[call-arg]
