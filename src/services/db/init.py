# services/db/init.py
from sqlalchemy.engine import Engine

from services.db.models import Base


class DatabaseBootstrap:
    def __init__(self, engine: Engine):
        self.engine = engine

    def run(self) -> None:
        Base.metadata.create_all(bind=self.engine)
