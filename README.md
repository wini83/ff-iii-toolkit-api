# Firefly III Toolkit API
FastAPI backend for reconciling Firefly III transactions with BLIK CSV imports and Allegro payments, with authenticated multi-user operations.

[![Build & Publish Docker Image](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/build.yml/badge.svg)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/build.yml)
[![CodeQL Advanced](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/codeql.yml/badge.svg)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/codeql.yml)
[![Lint (ruff)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/lint.yml/badge.svg)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/lint.yml)
[![tests-with-coverage](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/pytest_coverage.yml/badge.svg)](https://github.com/wini83/ff-iii-toolkit-api/actions/workflows/pytest_coverage.yml)
[![codecov](https://codecov.io/github/wini83/ff-iii-toolkit-api/graph/badge.svg?token=R5ULUOVPH1)](https://codecov.io/github/wini83/ff-iii-toolkit-api)
![Python](https://img.shields.io/badge/python-3.12-blue)

## Table of contents
- [What it does](#what-it-does)
- [Key features](#key-features)
- [Architecture](#architecture)
- [Getting started](#getting-started)
- [Configuration (.env)](#configuration-env)
- [API overview](#api-overview)
- [Development](#development)
- [CI/CD](#cicd)
- [Security notes](#security-notes)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## What it does
Use-cases:
- Import BLIK bank CSV files, preview parsed rows, compute matches against Firefly III transactions, and apply selected one-to-one matches.
- Pull Allegro payments (per stored user secret), preview matching against Firefly III transactions, and run async apply jobs.
- Screen uncategorized Firefly III transactions by month and apply categories/tags from the API.
- Manage local API users (bootstrap, create/disable/promote, audit log) and user-owned external secrets.

Non-goals:
- Not a Firefly III replacement or general-purpose accounting backend.
- Not a durable job queue system; matching/apply runtime state is process memory.
- Not a frontend UI in this repository.

## Key features
- FastAPI app with JWT access tokens and refresh-token cookie flow.
- SQLite/SQLAlchemy persistence with Alembic migrations for users, audit log, and user secrets.
- Runtime services for BLIK, Allegro, and transaction screening flows.
- Superuser-only user administration and audit-log querying.
- Health/version/bootstrap system endpoints.
- Docker image build with migration-on-start entrypoint.

## Architecture
High level:
- API layer: `src/api/routers/*`.
- Application services: `src/services/*_application_service.py`.
- Firefly integration: `src/services/firefly_*_service.py` via `ff-iii-luciferin` client.
- Persistence: SQLAlchemy models/repositories in `src/services/db/*` with Alembic migrations in `alembic/`.
- Runtime state: in-memory caches for BLIK matches, Allegro matches/jobs, and metrics states.

Request flow:
```text
Client
  -> FastAPI Router (/api/...)
    -> Auth guards (JWT + DB user checks)
      -> Application Service
        -> Firefly/Allegro integration and/or DB repositories
          -> Response DTO mapper
            -> Client
```

## Getting started
### Local
```bash
cp .env.example .env

# install dependencies
uv sync --frozen --dev

# initialize DB schema
uv run alembic upgrade head

# start API (same as make dev)
PYTHONPATH=src uv run uvicorn main:create_production_app --factory --reload --app-dir src
```

Health check:
```bash
curl http://localhost:8000/api/system/health
```

### Docker
```bash
docker build -t ff-iii-toolkit-api:local .
docker run --rm --env-file .env -p 8000:8000 ff-iii-toolkit-api:local
```

Notes:
- Container entrypoint runs `alembic upgrade head` before starting `uvicorn`.
- API listens on port `8000`.

### Docker Compose
No `docker-compose.yml` / `compose.yaml` exists in this repository at the moment.

Assumption:
- If compose is required, verify whether it lives in another repo or branch.

## Configuration (.env)
Documented keys that currently exist in `.env.example` and/or code:

| Variable | Source | Description |
| --- | --- | --- |
| `FIREFLY_URL` | `.env.example`, `src/settings.py` | Firefly III base URL used by service clients. |
| `FIREFLY_TOKEN` | `.env.example`, `src/settings.py` | Firefly III API token. |
| `SECRET_KEY` | `.env.example`, `src/settings.py` | JWT signing key (required). |
| `ALGORITHM` | `.env.example`, `src/settings.py` | JWT algorithm (default `HS256`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `.env.example`, `src/settings.py` | Access-token TTL in minutes. |
| `TRANSACTION_SNAPSHOT_TTL_SECONDS` | `.env.example`, `src/settings.py` | Shared in-memory TTL for transaction snapshots used by statistics endpoints. |
| `DEMO_MODE` | `.env.example`, `src/settings.py` | Feature flag (currently not used by routers/services). |
| `LOG_LEVEL` | `.env.example`, `src/settings.py` | Root logging level. |
| `ALLOWED_ORIGINS` | `.env.example`, `src/settings.py` | CORS origins (`*`, CSV list, or JSON list). |
| `BLIK_DESCRIPTION_FILTER` | `.env.example`, `src/settings.py` | BLIK text filter used in matching/screening. |
| `TAG_BLIK_DONE` | `.env.example`, `src/settings.py` | Tag treated as completed BLIK processing. |
| `USERS` | `.env.example` only | Legacy key; current auth uses DB users, not this variable. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `src/settings.py` | Refresh-token TTL in days. |
| `REFRESH_COOKIE_NAME` | `src/settings.py` | Cookie name for refresh token. |
| `REFRESH_TOKEN_SECURE` | `src/settings.py` | Sets `Secure` flag on refresh cookie. |
| `DATABASE_URL` / `database_url` | `src/settings.py` | SQLAlchemy DB URL (default `sqlite:///./data/app.db`). |

## API overview
- OpenAPI JSON: `/openapi.json`
- Swagger UI: `/docs`
- ReDoc: `/redoc`

Endpoint summary from current routers:

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/auth/token` | No | Issue access token and set refresh-token cookie. |
| `POST` | `/api/auth/refresh` | Refresh cookie | Issue new access token from refresh token. |
| `GET` | `/api/me` | Active user | Return current user profile. |
| `GET` | `/api/system/health` | No | API + DB health and bootstrap status. |
| `GET` | `/api/system/version` | No | API version from `pyproject.toml`. |
| `GET` | `/api/system/bootstrap/status` | No | Whether first superuser exists. |
| `POST` | `/api/system/bootstrap` | No | Create first superuser (one-time). |
| `GET` | `/api/blik_files/statistics` | Active user | Legacy BLIK statistics endpoint (deprecated). |
| `POST` | `/api/blik_files/statistics/refresh` | Active user | Legacy BLIK statistics refresh (deprecated). |
| `GET` | `/api/blik_files/statistics_v2` | Active user | Get async BLIK metrics job state/result. |
| `POST` | `/api/blik_files/statistics_v2/refresh` | Active user | Trigger BLIK metrics recomputation. |
| `POST` | `/api/blik_files` | Active user | Upload CSV file for BLIK processing. |
| `GET` | `/api/blik_files/{encoded_id}` | Active user | Preview uploaded CSV rows. |
| `GET` | `/api/blik_files/{encoded_id}/matches` | Active user | Compute BLIK-to-Firefly match candidates. |
| `POST` | `/api/blik_files/{encoded_id}/matches` | Active user | Apply selected BLIK matches. |
| `GET` | `/api/tx/screening` | Active user | List month transactions eligible for manual categorization. |
| `POST` | `/api/tx/{tx_id}/category/{category_id}` | Active user | Apply category to transaction. |
| `POST` | `/api/tx/{tx_id}/tag/` | Active user | Add tag to transaction. |
| `GET` | `/api/tx/statistics` | Active user | Get transaction metrics state/result. |
| `POST` | `/api/tx/statistics/refresh` | Active user | Trigger transaction metrics recomputation. |
| `GET` | `/api/allegro/secrets` | Active user | List current user Allegro-type secrets. |
| `GET` | `/api/allegro/{secret_id}/payments` | Active user | Fetch Allegro payments for a secret. |
| `GET` | `/api/allegro/{secret_id}/matches` | Active user | Compute Allegro-to-Firefly matches. |
| `POST` | `/api/allegro/{secret_id}/apply` | Active user | Start async apply job with explicit decisions. |
| `POST` | `/api/allegro/{secret_id}/apply/auto` | Active user | Auto-apply one-candidate matches (optional limit). |
| `GET` | `/api/allegro/apply-jobs/{job_id}` | Active user | Read async Allegro apply job status/result. |
| `GET` | `/api/allegro/statistics` | Active user | Get Allegro metrics state/result. |
| `POST` | `/api/allegro/statistics/refresh` | Active user | Trigger Allegro metrics recomputation. |
| `POST` | `/api/user-secrets` | Active user | Store a user-owned secret (type + value). |
| `GET` | `/api/user-secrets` | Active user | List current user secrets (without secret value). |
| `DELETE` | `/api/user-secrets/{secret_id}` | Active user | Delete own secret. |
| `GET` | `/api/users` | Superuser | List users. |
| `POST` | `/api/users` | Superuser | Create user. |
| `POST` | `/api/users/{user_id}/disable` | Superuser | Disable user. |
| `POST` | `/api/users/{user_id}/enable` | Superuser | Enable user. |
| `POST` | `/api/users/{user_id}/promote` | Superuser | Promote to superuser. |
| `POST` | `/api/users/{user_id}/demote` | Superuser | Demote from superuser. |
| `DELETE` | `/api/users/{user_id}` | Superuser | Delete user. |
| `GET` | `/api/users/audit-log` | Superuser | Query audit-log entries. |

## Development
```bash
# run tests
uv run pytest

# coverage (local)
uv run pytest --cov

# lint + format
uv run ruff check . --fix
uv run ruff format .

# type checking
uv run env PYTHONPATH=src mypy .
uv run ty check src

# pre-commit (if installed)
uv run pre-commit run --all-files
```

Make shortcuts:
```bash
make dev
make test
make cov
make ruff
make mypy
make ty
make pre
```

## CI/CD
- `lint.yml`: runs Ruff on push (`main`, `dev`) and on pull requests.
- `ty.yml`: runs Astral ty on push (`main`, `dev`) and on pull requests.
- `pytest_coverage.yml`: runs tests with coverage on push to `main` and on pull requests; uploads to Codecov.
- `codeql.yml`: CodeQL analysis on push/PR to `main` and weekly schedule.
- `build.yml`: builds and pushes Docker image to GHCR on tag pushes matching `v*`.

Image tags from `build.yml` metadata:
- `sha` tag.
- Git ref tag (for example `v2.6.0b0`).
- `latest` is configured but currently gated by `main` branch condition while workflow triggers only on tag pushes.

## Security notes
- Access tokens are JWT bearer tokens; refresh tokens are HTTP-only cookies.
- `SECRET_KEY` must be strong and private.
- Set `REFRESH_TOKEN_SECURE=true` behind HTTPS.
- User secrets are persisted in DB and currently stored plaintext (`src/services/db/models.py` comment marks this as MVP).
- Firefly and external API tokens must be treated as secrets and never committed.
- CORS is fully configurable; avoid `*` in production unless intentional.

## Troubleshooting
- `500` with message about schema not initialized: run `uv run alembic upgrade head` (or let Docker entrypoint run migrations).
- `401` on protected endpoints: ensure `Authorization: Bearer <access_token>` is present and user is active.
- `403` on `/api/users/*`: route requires superuser.
- `401` on `/api/auth/refresh`: refresh cookie missing/expired/invalid.
- `404 File not found` for BLIK preview/matches: uploaded CSV temp file is missing from system temp dir.
- `400 No match data found`: run preview matching endpoint first; caches are in-memory and reset on restart.
- Firefly-related `502`: verify `FIREFLY_URL`, `FIREFLY_TOKEN`, and upstream Firefly availability.

## Contributing
1. Create a branch from `main`.
2. Run local quality checks (`pytest`, `ruff`, `mypy`) before opening a PR.
3. Keep API and model changes covered by tests under `tests/`.
4. Use conventional commits if you rely on the release/changelog flow (`commitizen` config is present).

## License
MIT. See [LICENSE](LICENSE).
