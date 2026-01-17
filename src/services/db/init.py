from services.db.engine import engine
from services.db.models import Base


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
