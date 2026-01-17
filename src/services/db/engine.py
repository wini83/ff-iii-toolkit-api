# services/db/engine.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from settings import settings

DATABASE_URL = settings.database_url  # np. sqlite:///./app.db

engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
