from datetime import datetime
from uuid import uuid4

from services.allegro_state_store import (
    AllegroApplyJobManager,
    AllegroStateStore,
    get_allegro_state_store,
)
from services.domain.allegro import ApplyJobStatus


def test_apply_job_manager_create_and_get():
    manager = AllegroApplyJobManager()
    secret_id = uuid4()

    job = manager.create(secret_id=secret_id, total=5)

    assert job.secret_id == secret_id
    assert job.total == 5
    assert job.status == ApplyJobStatus.PENDING
    assert isinstance(job.started_at, datetime)
    assert job.started_at.tzinfo is not None

    fetched = manager.get(job.id)
    assert fetched is job


def test_apply_job_manager_get_missing_returns_none():
    manager = AllegroApplyJobManager()
    assert manager.get(uuid4()) is None


def test_state_store_singleton_and_defaults():
    store1 = get_allegro_state_store()
    store2 = get_allegro_state_store()
    assert store1 is store2
    assert isinstance(store1, AllegroStateStore)
    assert store1.matches_cache == {}
    assert store1.metrics_manager is None
