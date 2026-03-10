import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from settings import settings

security = HTTPBearer(auto_error=False)


def _decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from None

    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return sub


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    access_token_cookie: str | None = Cookie(default=None, alias="access_token"),
) -> str:
    token = credentials.credentials if credentials is not None else access_token_cookie
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return _decode_access_token(token)
