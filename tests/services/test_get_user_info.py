import pytest

from services.allegro.get_user_info import GetUserInfoResult


def test_get_user_info_result_maps_login_from_nested_payload():
    result = GetUserInfoResult({"accounts": {"allegro": {"login": "demo-user"}}})

    assert result.login == "demo-user"
    assert result.as_dict() == {"login": "demo-user"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"accounts": {}},
        {"accounts": {"allegro": {}}},
    ],
)
def test_get_user_info_result_rejects_missing_required_fields(payload):
    with pytest.raises(
        ValueError, match="invalid allegro user info response structure"
    ):
        GetUserInfoResult(payload)
