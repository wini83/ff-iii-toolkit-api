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
    USERS: str | None = None
    allowed_origins: Any = ["*"]
    DEMO_MODE: bool = False

    SECRET_KEY: str = "not_set"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BLIK_DESCRIPTION_FILTER: str = "BLIK - płatność w internecie"
    TAG_BLIK_DONE: str = "blik_done"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_COOKIE_NAME: str = "refresh_token"
    REFRESH_TOKEN_SECURE: bool = False

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


settings = Settings()
