import hmac
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from services.db.passwords import hash_password
from settings import settings


def generate_password_set_token() -> str:
    return token_urlsafe(32)


def hash_password_set_token(token: str) -> str:
    key = (settings.PASSWORD_SET_TOKEN_PEPPER or settings.SECRET_KEY).encode("utf-8")
    return hmac.new(key, token.encode("utf-8"), sha256).hexdigest()


def get_password_set_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(hours=settings.PASSWORD_SET_TOKEN_EXPIRE_HOURS)


def build_invite_url(token: str) -> str | None:
    if not settings.APP_PUBLIC_URL:
        return None
    return f"{settings.APP_PUBLIC_URL.rstrip('/')}/set-password?token={token}"


def generate_placeholder_password_hash() -> str:
    return hash_password(token_urlsafe(32))
