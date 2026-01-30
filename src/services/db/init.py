# services/db/init.py
from sqlalchemy import text
from sqlalchemy.engine import Engine


class DatabaseBootstrap:
    def __init__(self, engine: Engine):
        self.engine = engine

    def run(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))

            # sanity check: czy migracje były uruchomione
            result = conn.execute(
                text(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='alembic_version'"
                )
            ).scalar()

        if not result:
            raise RuntimeError(
                "Database schema not initialized. Run `alembic upgrade head` first."
            )
