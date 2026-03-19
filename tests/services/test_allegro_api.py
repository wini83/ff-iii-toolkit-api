from unittest.mock import MagicMock

import pytest
import requests

import services.allegro.api as allegro_api_module
from services.allegro.api import (
    ALLEGRO_API_URL,
    AllegroApiClient,
    AllegroApiError,
    AllegroAuthError,
    ApiWrapper,
)


def test_api_client_standard_header_uses_cookie_and_version():
    client = AllegroApiClient(cookie="cookie-123", session=MagicMock())

    header = client.get_standard_header(api_ver=3)

    assert header["Cookie"] == "QXLSESSID=cookie-123"
    assert header["Accept"] == "application/vnd.allegro.public.v3+json"
    assert header["Referer"] == "https://allegro.pl/"


@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (-1, 0), (1, -1)])
def test_get_orders_rejects_invalid_pagination(limit, offset):
    client = AllegroApiClient(cookie="cookie-123", session=MagicMock())

    with pytest.raises(ValueError, match="Limit & Offset must be greater than 0"):
        client.get_orders(limit=limit, offset=offset)


def test_get_orders_calls_api_wrapper_and_parser(monkeypatch):
    client = AllegroApiClient(cookie="cookie-123", session=MagicMock())
    wrapper_get = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(client, "_api_wrapper", MagicMock(get=wrapper_get))
    monkeypatch.setattr(
        allegro_api_module,
        "GetOrdersResult",
        lambda payload: ("parsed-orders", payload),
    )

    result = client.get_orders(limit=10, offset=20)

    assert result == ("parsed-orders", {"ok": True})
    wrapper_get.assert_called_once_with(
        f"{ALLEGRO_API_URL}/myorder-api/myorders?limit=10&offset=20",
        headers=client.get_standard_header(3),
    )


def test_get_user_info_wraps_parse_error(monkeypatch):
    client = AllegroApiClient(cookie="cookie-123", session=MagicMock())
    wrapper_get = MagicMock(return_value={"users": []})
    monkeypatch.setattr(client, "_api_wrapper", MagicMock(get=wrapper_get))

    def _raise_parse_error(_payload):
        raise ValueError("invalid")

    monkeypatch.setattr(allegro_api_module, "GetUserInfoResult", _raise_parse_error)

    with pytest.raises(
        AllegroApiError, match="Failed to parse Allegro user info response"
    ):
        client.get_user_info()


def test_api_wrapper_get_and_post_delegate_to_request():
    wrapper = ApiWrapper(session=MagicMock())
    wrapper.request = MagicMock(return_value={"ok": True})

    get_result = wrapper.get("https://example.com", headers={"h": "1"}, auth="a")
    post_result = wrapper.post(
        "https://example.com", data="x", headers={"h": "2"}, auth="b"
    )

    assert get_result == {"ok": True}
    assert post_result == {"ok": True}
    assert wrapper.request.call_args_list[0].args == ("GET", "https://example.com")
    assert wrapper.request.call_args_list[1].args == ("POST", "https://example.com")


def test_api_wrapper_request_returns_json_on_success():
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {"ok": True}
    session.request.return_value = response
    wrapper = ApiWrapper(session=session)

    result = wrapper.request("GET", "https://example.com", headers={"X": "1"})

    assert result == {"ok": True}
    session.request.assert_called_once()
    response.raise_for_status.assert_called_once()


def test_api_wrapper_request_maps_auth_errors():
    session = MagicMock()
    response = MagicMock(status_code=401)
    http_error = requests.HTTPError("unauthorized")
    http_error.response = response
    session.request.return_value = MagicMock(
        raise_for_status=MagicMock(side_effect=http_error)
    )
    wrapper = ApiWrapper(session=session)

    with pytest.raises(AllegroAuthError, match="Allegro authentication failed"):
        wrapper.request("GET", "https://example.com")


def test_api_wrapper_request_maps_http_error_to_api_error():
    session = MagicMock()
    response = MagicMock(status_code=500)
    http_error = requests.HTTPError("boom")
    http_error.response = response
    session.request.return_value = MagicMock(
        raise_for_status=MagicMock(side_effect=http_error)
    )
    wrapper = ApiWrapper(session=session)

    with pytest.raises(AllegroApiError, match="Allegro API error 500"):
        wrapper.request("GET", "https://example.com")


def test_api_wrapper_request_maps_timeout():
    session = MagicMock()
    session.request.side_effect = requests.Timeout("slow")
    wrapper = ApiWrapper(session=session)

    with pytest.raises(AllegroApiError, match="Allegro API timeout"):
        wrapper.request("GET", "https://example.com")
