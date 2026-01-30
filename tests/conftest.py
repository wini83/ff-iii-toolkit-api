import os
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alembic import command
from api.deps_db import get_db
from main import create_app  # 👈 TO JEST KLUCZ

os.environ.setdefault("SECRET_KEY", "test-secret")


def _run_migrations(connection) -> None:
    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    connection = engine.connect()
    _run_migrations(connection)
    TestingSessionLocal = sessionmaker(
        bind=connection, autocommit=False, autoflush=False
    )

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        connection.close()
        engine.dispose()


@pytest.fixture(scope="function")
def client(db):
    app = create_app()  # 👈 TESTOWA APPKA, BEZ BOOTSTRAPU

    def override_get_db(request: Request):
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
