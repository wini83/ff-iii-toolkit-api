from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from api.routers.auth import create_access_token, create_refresh_token
from services.auth import get_current_user


def test_get_current_user_accepts_bearer_header_token():
    token = create_access_token(str(uuid4()))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    result = get_current_user(credentials=credentials)

    assert result


def test_get_current_user_accepts_access_token_cookie():
    user_id = str(uuid4())

    result = get_current_user(
        credentials=None,
        access_token_cookie=create_access_token(user_id),
    )

    assert result == user_id


def test_get_current_user_prefers_header_over_cookie():
    header_user_id = str(uuid4())

    result = get_current_user(
        credentials=HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=create_access_token(header_user_id),
        ),
        access_token_cookie=create_access_token(str(uuid4())),
    )

    assert result == header_user_id


def test_get_current_user_rejects_refresh_token_cookie():
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=None,
            access_token_cookie=create_refresh_token(str(uuid4())),
        )

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_rejects_invalid_access_token_cookie():
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None, access_token_cookie="not-a-jwt")

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_rejects_invalid_bearer_even_with_valid_cookie():
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="not-a-jwt",
            ),
            access_token_cookie=create_access_token(str(uuid4())),
        )

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_rejects_missing_token():
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None, access_token_cookie=None)

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
