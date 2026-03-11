# app/api/auth.py
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.models.auth import SetPasswordRequest, Token
from services.db.passwords import hash_password, verify_password
from services.db.repository import (
    AuditLogRepository,
    PasswordSetTokenRepository,
    UserRepository,
)
from services.password_set_tokens import hash_password_set_token
from settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
SYSTEM_ACTOR_ID = UUID("00000000-0000-0000-0000-000000000000")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_access_token(subject: str, expires_delta: timedelta | None = None):
    to_encode: dict[str, object] = {"sub": subject, "typ": "access"}
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, expires_delta: timedelta | None = None):
    to_encode: dict[str, object] = {"sub": subject, "typ": "refresh"}
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, object]:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


@router.post("/token", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    user = repo.get_by_username(form_data.username)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_SECURE,
        samesite="lax",
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
):
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    payload = decode_token(token)
    if payload.get("typ") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token(subject=str(subject))
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/set-password", status_code=status.HTTP_204_NO_CONTENT)
def set_password(
    payload: SetPasswordRequest,
    db: Session = Depends(get_db),
):
    now = datetime.now(UTC)
    token_repo = PasswordSetTokenRepository(db)
    user_repo = UserRepository(db)
    audit_repo = AuditLogRepository(db)

    token = token_repo.get_by_hash(hash_password_set_token(payload.token))
    if token is None or token.used_at is not None or _as_utc(token.expires_at) < now:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = user_repo.get_by_id(token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user_repo.set_password(
        token.user_id,
        password_hash=hash_password(payload.new_password),
        must_change_password=False,
        password_changed_at=now,
        commit=False,
    )
    token_repo.consume(
        token_id=token.id,
        used_at=now,
        commit=False,
    )
    audit_repo.log(
        actor_id=SYSTEM_ACTOR_ID,
        action="user.password.set",
        target_id=token.user_id,
        metadata={"by_token": True},
        commit=False,
    )
    db.commit()
