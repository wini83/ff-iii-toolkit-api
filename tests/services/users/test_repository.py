from services.db.repository import UserRepository


def test_create_and_get_user(db):
    repo = UserRepository(db)

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


def test_disable_user(db):
    repo = UserRepository(db)

    user = repo.create(
        username="bob",
        password_hash="hashed",
    )

    repo.disable(user.id)

    disabled = repo.get_by_id(user.id)
    assert disabled is not None
    assert disabled.is_active is False


def test_enable_user(db):
    repo = UserRepository(db)

    user = repo.create(
        username="carol",
        password_hash="hashed",
    )
    repo.disable(user.id)

    repo.enable(user.id)

    enabled = repo.get_by_id(user.id)
    assert enabled is not None
    assert enabled.is_active is True


def test_demote_user(db):
    repo = UserRepository(db)

    user = repo.create(
        username="dave",
        password_hash="hashed",
        is_superuser=True,
    )

    repo.demote_from_superuser(user.id)

    demoted = repo.get_by_id(user.id)
    assert demoted is not None
    assert demoted.is_superuser is False


def test_delete_user(db):
    repo = UserRepository(db)

    user = repo.create(
        username="erin",
        password_hash="hashed",
    )

    repo.delete(user.id)

    deleted = repo.get_by_id(user.id)
    assert deleted is None
