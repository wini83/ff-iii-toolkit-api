import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.auth import get_current_user


# --- dummy user ---
def fake_user():
    return {"id": 1, "email": "test@example.com"}


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = fake_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
