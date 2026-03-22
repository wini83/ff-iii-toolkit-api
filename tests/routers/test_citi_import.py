from io import BytesIO
from zipfile import ZipFile

from api.deps_runtime import get_citi_import_runtime
from api.routers.auth import create_access_token
from services.citi_import.cache import CitiImportStore
from services.citi_import.exporter import CitiCsvZipExporter
from services.citi_import.mapper import CitiBankRecordMapper
from services.citi_import.parser import CitiTextParser
from services.citi_import.service import CitiImportService
from services.db.repository import UserRepository


def _auth_header(user_id: str) -> dict[str, str]:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def _create_user(db, username: str = "user"):
    repo = UserRepository(db)
    return repo.create(
        username=username,
        password_hash="hashed",
        is_superuser=False,
    )


def _runtime() -> CitiImportService:
    return CitiImportService(
        parser=CitiTextParser(),
        mapper=CitiBankRecordMapper(),
        store=CitiImportStore(),
        exporter=CitiCsvZipExporter(),
    )


def test_citi_parse_text_happy_path_returns_preview(client, db):
    user = _create_user(db)
    runtime = _runtime()
    client.app.dependency_overrides[get_citi_import_runtime] = lambda: runtime

    response = client.post(
        "/api/tools/citi/parse-text",
        headers=_auth_header(str(user.id)),
        json={
            "text": "16 sty 2025\nTest Shop\nTest Shop\n-42,00PLN\n",
            "include_positive": False,
            "chunk_size": 60,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 1
    assert body["preview"][0]["details"] == "Test Shop"
    assert body["warnings"] == []


def test_citi_upload_happy_path_returns_preview(client, db):
    user = _create_user(db)
    runtime = _runtime()
    client.app.dependency_overrides[get_citi_import_runtime] = lambda: runtime

    response = client.post(
        "/api/tools/citi/upload?chunk_size=20",
        headers=_auth_header(str(user.id)),
        files={
            "file": ("input.txt", b"16 sty 2025\nTest Shop\nTest Shop\n-42,00PLN\n")
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 1
    assert body["preview"][0]["recipient"] == "Test Shop"


def test_citi_get_file_reads_cached_preview(client, db):
    user = _create_user(db)
    runtime = _runtime()
    client.app.dependency_overrides[get_citi_import_runtime] = lambda: runtime
    parse_response = client.post(
        "/api/tools/citi/parse-text",
        headers=_auth_header(str(user.id)),
        json={
            "text": "16 sty 2025\nTest Shop\nTest Shop\n-42,00PLN\n",
            "chunk_size": 60,
        },
    )
    file_id = parse_response.json()["file_id"]

    response = client.get(
        f"/api/tools/citi/files/{file_id}",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    assert response.json()["file_id"] == file_id


def test_citi_export_csv_returns_zip(client, db):
    user = _create_user(db)
    runtime = _runtime()
    client.app.dependency_overrides[get_citi_import_runtime] = lambda: runtime
    parse_response = client.post(
        "/api/tools/citi/parse-text",
        headers=_auth_header(str(user.id)),
        json={
            "text": "\n".join(
                [
                    "16 sty 2025",
                    "Shop 1",
                    "Shop 1",
                    "-1,00PLN",
                    "17 sty 2025",
                    "Shop 2",
                    "Shop 2",
                    "-2,00PLN",
                ]
            ),
            "chunk_size": 1,
        },
    )
    file_id = parse_response.json()["file_id"]

    response = client.post(
        f"/api/tools/citi/files/{file_id}/export-csv",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.namelist() == [
            f"citi_import_{file_id}_1.csv",
            f"citi_import_{file_id}_2.csv",
        ]


def test_citi_get_file_invalid_id_returns_400(client, db):
    user = _create_user(db)
    runtime = _runtime()
    client.app.dependency_overrides[get_citi_import_runtime] = lambda: runtime

    response = client.get(
        "/api/tools/citi/files/bad-id",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "bad-id"
