# app/api/auth.py
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps_db import get_db
from services.db.passwords import verify_password
from services.db.repository import UserRepository
from settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Token(BaseModel):
    access_token: str
    token_type: str


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
