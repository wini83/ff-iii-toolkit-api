from api.routers.auth import create_access_token
from services.db.repository import UserRepository


def _auth_header(user_id: str) -> dict[str, str]:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def _create_user(db, username: str = "user"):
    repo = UserRepository(db)
    return repo.create(
        username=username,
        password_hash="hashed",
        is_superuser=False,
    )


def test_category_suggestions_legacy_route_is_gone(client):
    response = client.post("/api/transactions/category-suggestions")

    assert response.status_code == 404
