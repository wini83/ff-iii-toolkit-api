from services.db.repository import UserRepository


def test_create_and_get_user(db_session):
    repo = UserRepository(db_session)

    repo.create(
        username="alice",
        password_hash="hashed",
        is_superuser=True,
    )

    fetched = repo.get_by_username("alice")

    assert fetched is not None
    assert fetched.username == "alice"
    assert fetched.is_superuser is True
    assert fetched.is_active is True


def test_disable_user(db_session):
    repo = UserRepository(db_session)

    user = repo.create(
        username="bob",
        password_hash="hashed",
    )

    repo.disable(user.id)

    disabled = repo.get_by_id(user.id)
    assert disabled is not None
    assert disabled.is_active is False
