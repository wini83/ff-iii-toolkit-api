import os

os.environ.setdefault("SECRET_KEY", "test-secret")
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.deps_db import get_db
from main import create_app  # 👈 TO JEST KLUCZ
from services.db.models import Base

os.environ.setdefault("SECRET_KEY", "test-secret")


@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    app = create_app()  # 👈 TESTOWA APPKA, BEZ BOOTSTRAPU

    def override_get_db(request: Request):
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
