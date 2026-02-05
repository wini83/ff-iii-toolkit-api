"""Data structures for the ``get_user_info`` call."""

from typing import Any


class GetUserInfoResult:
    """Result of get_orders method"""

    def __init__(self, items: dict[str, Any]) -> None:
        """Init method"""
        try:
            self._login: str = items["accounts"]["allegro"]["login"]
        except KeyError as exc:
            raise ValueError("invalid allegro user info response structure") from exc

    @property
    def login(self) -> str:
        """Return user's login."""
        return self._login

    def as_dict(self) -> dict[str, str]:
        """Return result as dictionary."""
        return {"login": self._login}
