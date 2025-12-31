import pytest
from fastapi.testclient import TestClient

from api.routers.blik_files import firefly_dep
from services.auth import get_current_user
from src.main import app


# --- dummy user ---
def fake_user():
    return {"id": 1, "email": "test@example.com"}


class DummyFirefly:
    def fetch_transactions(self, *args, **kwargs):
        return []

    def fetch_categories(self, *args, **kwargs):
        return []

    def assign_transaction_category(self, *args, **kwargs):
        return None

    def add_tag_to_transaction(self, *args, **kwargs):
        return None

    def update_transaction_description(self, *args, **kwargs):
        return None

    def update_transaction_notes(self, *args, **kwargs):
        return None


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[firefly_dep] = lambda: DummyFirefly()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
