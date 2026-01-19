# services/db/engine.py
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


def create_engine_from_url(database_url: str) -> Engine:
    return create_engine(
        database_url,
        connect_args=(
            {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        ),
        pool_pre_ping=True,
    )


def create_session_factory(engine: Engine):
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
