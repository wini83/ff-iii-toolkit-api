from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_db(request: Request) -> Iterator[Session]:
    SessionLocal = request.app.state.session_factory
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
