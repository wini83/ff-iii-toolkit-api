# app/api/auth.py
from datetime import datetime, timedelta

import jwt  # pip install PyJWT
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
REFRESH_TOKEN_EXPIRE_DAYS = 30
REFRESH_COOKIE_NAME = "refresh_token"


def load_users() -> dict:
    users = {}
    if settings.USERS:
        for part in settings.USERS.split(","):
            if ":" in part:
                u, p = part.split(":", 1)
                users[u.strip()] = p.strip()
    return users


USERS = load_users()


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(subject: str, expires_delta: timedelta | None = None):
    to_encode: dict[str, object] = {"sub": subject, "typ": "access"}
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded


def create_refresh_token(subject: str, expires_delta: timedelta | None = None):
    to_encode: dict[str, object] = {"sub": subject, "typ": "refresh"}
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode["exp"] = expire
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded


def decode_token(token: str) -> dict[str, object]:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from None


@router.post("/token", response_model=Token)
async def login_for_access_token(
    response: Response, form_data: OAuth2PasswordRequestForm = Depends()
):
    # OAuth2PasswordRequestForm expects fields: username, password (x-www-form-urlencoded)
    username = form_data.username
    password = form_data.password
    real = USERS.get(username)
    if not real or real != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(subject=username)
    refresh_token = create_refresh_token(subject=username)
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=int(timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: Request):
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    payload = decode_token(token)

    if payload.get("typ") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    access_token = create_access_token(subject=str(subject))
    return {"access_token": access_token, "token_type": "bearer"}
