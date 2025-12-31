import os
import tempfile

from api.models.blik_files import MatchResult
from api.routers import blik_files as blik_router
from services.tx_processor import TransactionProcessor
from settings import settings
from utils.encoding import encode_base64url

CSV_TEXT = (
    "ignored line\n"
    "Data transakcji;Kwota w walucie rachunku;Kwota operacji;"
    "Nazwa nadawcy;Nazwa odbiorcy;Szczegóły transakcji;Waluta operacji;"
    "Waluta rachunku;Numer rachunku nadawcy;Numer rachunku odbiorcy\n"
    "01-01-2024;10,00;10,00;Alice;Bob;Test;PLN;PLN;123;456\n"
)


def write_temp_csv(name: str) -> str:
    path = os.path.join(tempfile.gettempdir(), f"{name}.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write(CSV_TEXT)
    return path


class DummyTx:
    def __init__(self, tx_id: int):
        self.id = tx_id


def test_blik_files_statistics(client):
    response = client.get("/api/blik_files/statistics")
    assert response.status_code == 200


def test_blik_files_statistics_refresh(client):
    response = client.post("/api/blik_files/statistics/refresh")
    assert response.status_code == 200


def test_blik_files_upload_csv(client):
    response = client.post(
        "/api/blik_files",
        files={"file": ("test.csv", CSV_TEXT.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200


def test_blik_files_get_tempfile(client):
    name = "blik_testfile"
    path = write_temp_csv(name)
    encoded = encode_base64url(name)
    try:
        response = client.get(f"/api/blik_files/{encoded}")
        assert response.status_code == 200
    finally:
        os.remove(path)


def test_blik_files_matches(client, monkeypatch):
    name = "blik_matches"
    path = write_temp_csv(name)
    encoded = encode_base64url(name)
    monkeypatch.setattr(settings, "FIREFLY_URL", "http://example.test")
    monkeypatch.setattr(settings, "FIREFLY_TOKEN", "token")
    monkeypatch.setattr(TransactionProcessor, "match", lambda *args, **kwargs: [])
    try:
        response = client.get(f"/api/blik_files/{encoded}/matches")
        assert response.status_code == 200
    finally:
        os.remove(path)


def test_blik_files_apply_matches(client, monkeypatch):
    encoded = "apply_matches"
    monkeypatch.setattr(settings, "FIREFLY_URL", "http://example.test")
    monkeypatch.setattr(settings, "FIREFLY_TOKEN", "token")
    monkeypatch.setattr(
        TransactionProcessor, "apply_match", lambda *args, **kwargs: None
    )
    dummy_match = MatchResult(tx=DummyTx(1), matches=[object()])
    blik_router.MEM_MATCHES[encoded] = [dummy_match]
    try:
        response = client.post(
            f"/api/blik_files/{encoded}/matches",
            json={"tx_indexes": [1]},
        )
        assert response.status_code == 200
    finally:
        blik_router.MEM_MATCHES.pop(encoded, None)
