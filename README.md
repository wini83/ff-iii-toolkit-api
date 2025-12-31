# Firefly III Toolkit API
[![Build & Publish Docker Image](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/build.yml/badge.svg)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/build.yml)
[![CodeQL Advanced](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/codeql.yml/badge.svg)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/codeql.yml)
[![Lint (ruff)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/lint.yml/badge.svg)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/lint.yml)
[![codecov](https://codecov.io/github/wini83/ff-iii-toolkit-api/graph/badge.svg?token=R5ULUOVPH1)](https://codecov.io/github/wini83/ff-iii-toolkit-api)
![Python](https://img.shields.io/badge/python-3.12-blue)

Backend FastAPI service that helps match and update BLIK transactions in Firefly III using bank CSV exports. Upload a statement, preview parsed rows, review matches, and bulk-apply tags/notes in Firefly.

## Status
Internal tool, actively developed. No persistent database; in-memory match cache is reset on restart. Docker images are published to GHCR from `main`.

## Features
- CSV ingest and preview for Polish bank statement formats.
- Match pipeline against Firefly III transactions with configurable filters.
- Bulk apply notes/description updates and a "done" tag.
- JWT auth with a simple user list from `.env`.
- Docker-first deployment with optional Nginx proxy.

## Architecture (high-level)
- FastAPI app (`src/main.py`) with routers:
  - `auth`: JWT token issuance from `/api/auth/token`.
  - `system`: health/version endpoints under `/api/system/*`.
  - `blik_files`: CSV upload -> preview -> match -> apply flow.
- CSV ingest: files stored temporarily in `/tmp`, parsed by `BankCSVReader`.
- Matching: `TransactionProcessor.match` queries Firefly, filters by `BLIK_DESCRIPTION_FILTER`, excludes `TAG_BLIK_DONE`, and computes candidates.
- Apply: writes updates in Firefly and tags transactions. Match results are cached in-process (`MEM_MATCHES`) and cleared on restart.
- Middleware: CORS (via `ALLOWED_ORIGINS`), logging to `blik_sync.log` and stdout.

## Tech stack
- Backend: Python 3.12, FastAPI, Starlette, Pydantic v2, PyJWT, `fireflyiii-enricher-core`
- Runtime: uvicorn, python-dotenv
- Tooling: `uv`, pytest, black, ruff, isort, mypy, commitizen
- Infra: Docker, docker-compose, GitHub Actions

## Requirements
- Python >= 3.12
- `uv` (https://github.com/astral-sh/uv) or `pip`/`venv`
- Firefly III API access + personal access token
- Docker (optional, for production/runtime)

## Quick start (local)
```bash
# 1) Install deps
uv sync

# 2) Configure
cp .env.example .env

# 3) Run API
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 4) Health check
curl http://localhost:8000/api/system/health
```

Auth:
```bash
# x-www-form-urlencoded token request
curl -X POST http://localhost:8000/api/auth/token \
  -d 'username=user1&password=secret' \
  | jq -r .access_token

# use in requests: Authorization: Bearer <token>
```

## Configuration
Start with `.env.example` and fill in:
- `FIREFLY_URL`: Firefly III API base URL.
- `FIREFLY_TOKEN`: Firefly personal access token.
- `USERS`: comma-separated `user:pass` list.
- `SECRET_KEY` / `ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT settings (must be consistent for issuing and validating tokens).
- `ALLOWED_ORIGINS`: `*`, CSV (`a,b,c`), or JSON list for CORS.
- `DEMO_MODE`: feature flag (currently unused).
- `BLIK_DESCRIPTION_FILTER`: description fragment used to filter Firefly transactions.
- `TAG_BLIK_DONE`: tag applied after `apply`.

Note: avoid spaces around `=` in `.env` for predictable parsing.

## API flow (BLIK)
1. `POST /api/blik_files` with CSV file (`file` in form-data) -> returns `id`.
2. `GET /api/blik_files/{id}` -> preview parsed rows.
3. `GET /api/blik_files/{id}/matches` -> match results and stats.
4. `POST /api/blik_files/{id}/matches` with `{ "tx_indexes": [<id_csv>, ...] }` for rows that have exactly one match.

## API reference (summary)
| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| POST | `/api/auth/token` | Issue JWT access token | No |
| GET | `/api/system/health` | Health check | No |
| GET | `/api/system/version` | Version info | No |
| POST | `/api/blik_files` | Upload CSV file | Yes |
| GET | `/api/blik_files/{id}` | Preview parsed CSV rows | Yes |
| GET | `/api/blik_files/{id}/matches` | Compute and list match candidates | Yes |
| POST | `/api/blik_files/{id}/matches` | Apply matches for selected rows | Yes |

## Docker
Build/run locally:
```bash
docker build -t ff-iii-toolkit-api:local .
docker run --env-file .env -p 8000:8000 ff-iii-toolkit-api:local
```

Compose (backend + proxy to Firefly on host):
```bash
cd infra
docker compose up -d
```
Edit `infra/nginx-firefly.conf` if your Firefly instance listens on a different host/port.

## CI/CD
- `.github/workflows/build.yml`: builds and publishes images to GHCR on `main` and `v*` tags.
- Tests are not enforced in the pipeline; run locally before release.

## Repository structure
- `src/main.py` - FastAPI app and router/middleware wiring.
- `src/api/routers/` - `auth`, `blik_files`, `system`.
- `src/api/models/` - Pydantic request/response models.
- `src/services/` - CSV parser, auth utils, transaction processor.
- `src/utils/` - logger and helpers.
- `infra/` - `docker-compose.yml`, `nginx-firefly.conf`.
- `Dockerfile` - multi-stage build using `uv`.
- `makefile` - shortcuts (`make dev`, `make test`).
- `tests/` - tests for `SimplifiedRecord.pretty_print`.

## Troubleshooting
- 500 on `/statistics` `/matches` `/apply`: missing `FIREFLY_URL` or `FIREFLY_TOKEN`.
- 401 after login: `SECRET_KEY`/`ALGORITHM` mismatch between token issuance and validation environment.
- No matches: verify `BLIK_DESCRIPTION_FILTER` and ensure transactions are not already tagged with `TAG_BLIK_DONE`.
- "No match data found" during apply: in-memory cache cleared on restart; call `/matches` again.
- CORS blocked: set `ALLOWED_ORIGINS` to correct CSV/JSON or `*`.
- Missing CSV preview: files live in `/tmp/<id>.csv`; cleanup or restart removes them.

## Development
- Logs: stdout and `blik_sync.log` in the working directory.
- Tests: `uv run pytest` or `make test`.
- Lint/format: `uv run ruff check`, `uv run black .`, `uv run mypy`.

## License
See `LICENSE`.
