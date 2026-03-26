import pytest

from settings import Settings


def test_allowed_origins_none_defaults_to_wildcard():
    settings = Settings(allowed_origins=None)
    assert settings.allowed_origins == ["*"]


def test_allowed_origins_star_string_defaults_to_wildcard():
    settings = Settings(allowed_origins="*")
    assert settings.allowed_origins == ["*"]


def test_allowed_origins_csv_string_parses_list():
    settings = Settings(allowed_origins="https://a.com, https://b.com")
    assert settings.allowed_origins == ["https://a.com", "https://b.com"]


def test_allowed_origins_json_list_parses_list():
    settings = Settings(allowed_origins='["https://a.com"]')
    assert settings.allowed_origins == ["https://a.com"]


def test_allowed_origins_invalid_json_raises():
    with pytest.raises(ValueError):
        Settings(allowed_origins='["https://a.com"')


def test_transaction_snapshot_ttl_seconds_has_default():
    settings = Settings(TRANSACTION_SNAPSHOT_TTL_SECONDS=86400)
    assert settings.TRANSACTION_SNAPSHOT_TTL_SECONDS == 86400
