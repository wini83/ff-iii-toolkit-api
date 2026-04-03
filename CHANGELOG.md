## v2.12.0 (2026-04-03)

### Feat

- introduce encrypted user secrets with vault session flow & add internal transaction snapshot refresh endpoint

## v2.11.2 (2026-03-29)

### Refactor

- **citi-import**: shorten export filenames and include transaction date range (#50)

## v2.11.1 (2026-03-26)

### Refactor

- **system**: make transaction snapshot TTL configurable and expose /api/system/transaction-snapshot

## v2.11.0 (2026-03-22)

### Feat

- **citi**: add cached import preview and csv export endpoints (#44) (#45)

## v2.10.1 (2026-03-19)

### Refactor

- unify Firefly metrics around shared transaction snapshots

## v2.10.0 (2026-03-16)

### Feat

- **blik**: add async apply jobs and match selection flow
- **blik**: add async apply jobs and match selection flow
- **user-secrets**: add alias to secrets

### Fix

- **blik**: align txtag to changed signature
- **users**: align test to changed logic

## v2.9.0 (2026-03-15)

### Feat

- **user-secrets**: add alias to secrets (#36)

## v2.8.2 (2026-03-14)

### Fix

- **users**: align test to changed logic (#35)

## v2.8.1 (2026-03-13)

### Fix

- **users**: fixed link generation pattern

## v2.8.0 (2026-03-11)

## v2.7.0 (2026-03-11)

### Feat

- **users**: add invite-based password setup workflow
- **users**: add invite-based password setup workflow

### Fix

- **auth**: use HMAC for password set token digests

## v2.6.0 (2026-03-10)

### Refactor

- improve allegro matching preview and auth token handling
- **auth**: accept access tokens from bearer header or cookie
- **allegro**: expose match status and unmatched payments in preview

## v2.6.0rc1 (2026-03-08)

### Fix

- **allegro**: add paginated match cache and cache invalidation endpoint
- **allegro**: add paginated match cache and cache invalidation endpoint
- **main**: align docs url to production stack

### Refactor

- **allegro**: remove batch fetch and support order pagination

## v2.6.0rc0 (2026-02-28)

### Refactor

- unify job status enums across domain, stats, and API layers  and  added short id for secrets
- **secrets**: added short id for secrets

## v2.6.0b4 (2026-02-28)

### Fix

- **stats**: set RUNNING eagerly and clear stale metrics during recompute

## v2.6.0b3 (2026-02-27)

### Refactor

- unify job status enums across domain, stats, and API layers (#24)
- unify job status enums across domain, stats, and API layers

## v2.6.0b2 (2026-02-27)

### Fix

- recover version display in swagger docs

## v2.6.0b1 (2026-02-27)

### Feat

- **allegro**: auto-apply single matches with job tracking

### Refactor

- **allegro**: add auto-apply endpoint and detailed apply job outcomes
- **allegro**: add auto-apply for single matches and track apply job tx results

## v2.6.0b0 (2026-02-12)

### Refactor

- **allegro**: enrich payments with metadata and external ids
- **allegro**: add apply job workflow with state store and API endpoints
- **allegro**: enrich payments with metadata and external ids

## v2.6.0a1 (2026-02-08)

### Fix

- **docker**: fix(docker): run alembic using venv instead of uv in runtime

## v2.6.0a0 (2026-02-08)

### Feat

- **allegro**: add payment fetching and match preview endpoints
- **allegro**: add payment fetching and match preview endpoints

### Fix

- **alembic**: align env.py with src layout and sqlite batch mode

## v2.5.0 (2026-02-05)

### Feat

- **allegro**: add metrics endpoints and Firefly-backed stats service
- **user-secrets**: introduce secure user secrets management with audit trail
- **blik**: add snapshot-based BLIK statistics API alongside legacy endpoints
- **tx**: add tx stats
- **users**: add admin audit log endpoint and tests
- **users**: add enable, demote, and delete user actions with audit logs
- **db**: add alembic setup and initial migration
- **users**: add audit log for admin actions and adapt tests
- **api**: enrich simplified tx with currency, type, and fx fields
- add currency/fx context and tx type to Transaction, bump luciferin

### Refactor

- **api**: add metrics fetch duration and router-level auth deps
- **allegro**: add domain models and service layer with improved error handling
- **api**: add metrics fetch duration and router-level auth deps
- **api**: centralize Firefly dependencies and runtime services
- **tx**: switch to snapshot-based async metrics with generic runner
- **system**: addded bootstrap status to health endpoint
- **system**: enhanced boostrap and health endpoints
- **system**: move app version to app.state and remove router init side effects
- **db**: migration to alembic

## v2.4.0 (2026-02-01)

## v2.4.0b0 (2026-01-25)

### Feat

- **api**: enrich simplified tx with currency, type, and fx fields

## v2.3.1a0 (2026-01-19)

### Fix

- **docker**: fix in dockerfile

## v2.3.0 (2026-01-19)

### Feat

- add db engine
- **auth**: add /me endpoint and enforce active users
- **users**: add superuser-only user management API
- **system**: add bootstrap endpoint and switch to argon2
- **db**: dd user domain model and repository with SQLite support
- **allegro**: add Allegro API adapter

### Fix

- **blik**: fixed potential path traversal by validating file identifiers and enforcing temp directory confinement
- **blik**: prevent cache reset by using singleton BlikApplicationService

### Refactor

- **auth**: unify JWT config via settings to fix CI/local mismatch
- **app**: switch to application factory and uvicorn --factory to fix CI bootstrap issues
- **auth**: switch authentication from env users to database
- refactor tx flow to application service and add service tests
- reformat reflecting changes in ff client

## v2.2.7 (2026-01-16)

### Refactor

- refactor in service level

## v2.2.6 (2026-01-01)

### Refactor

- **logging**: add configurable log level and structured startup logs

## v2.2.5 (2025-12-31)

### Refactor

- **auth**: handle refresh token, added tests
- **auth**: move refresh token settings to config
- **auth**: add refresh flow; add pytest-cov config

## v2.2.4 (2025-12-29)

### Refactor

- **tx**: added tag eindpoint

## v2.2.3 (2025-12-27)

### Refactor

- **tx**: add monthly screening endpoint with date range filtering

## v2.2.2 (2025-12-27)

### Fix

- **tx**: remove processed items from cache

## v2.2.1 (2025-12-27)

### Fix

- **tx**: fixed problem with assign category

## v2.2.0 (2025-12-26)

### Feat

- add tx router and code refactor with ruff (tier 1 & tier 2)

## v2.1.3 (2025-12-22)

### Fix

- **ci**: force rebuild

## v2.1.2 (2025-12-22)

### Fix

- **blik**: fixed logic in stats calculation logic

## v2.1.1 (2025-12-22)

### Fix

- **blik**: add cached statistics with refresh endpoint

## v2.1.0 (2025-12-14)

### Feat

- **blik**: introduce stats and share models with pandas

### Fix

- **tx_processor**: fixes #3 - apply match
- **blik**: removed git artifacts

## v2.0.1 (2025-12-13)

### Feat

- **blik**: improve record pretty print and refresh docs

### Fix

- **auth**: update router prefix to /api/auth

## v2.0.0 (2025-12-07)

### Feat

- **test**: test

## 1.3.0 (2025-12-07)

### Feat

- **infra**: add full dockerization setup with reverse proxy and health-checked backend stack

## 1.2.0 (2025-12-07)

### Feat

- **settings**: refactor middleware configuration into centralized settings layer

### Refactor

- **settings**: remove legacy config.py and migrate all env access to unified settings

## 1.1.0 (2025-12-06)

### Feat

- **api**: add version endpoint, improve health response, and align BLIK models

## 1.0.0 (2025-12-06)

### BREAKING CHANGE

- api endpoints changed

### Feat

- **api**: restructure API into clear namespaces and introduce blik_files pipeline

### Refactor

- **api**: isort ruff black mypy

## 0.4.5 (2025-12-06)

### Refactor

- **api**: migrate backend to a clean src-based project layout and update imports
- **api**: -add response model to allpy matches endpoint

## 0.4.4 (2025-12-02)

### Refactor

- **auth**: - replace os.getenv usage with shared `settings` instance  - explicitly type JWT payload to resolve Pylance update() errors  - clean up auth flow and remove debug prints
- **ui**: deleted login and upload pages

## 0.4.3 (2025-12-01)

### Refactor

- **api**: introduce typed Pydantic response models for file and upload endpoints

## 0.4.2 (2025-11-30)

### Fix

- **api**: CORS middleware added
- **main**: Updated main.py to import settings first and remove deprecated dotenv calls


## 0.4.1 (2025-11-29)

### Refactor

- **config**: introduce Settings class and centralized .env loading
- **project**: reorganize project structure into backend + frontend architecture

## 0.4.0 (2025-11-27)

### Feat

- **frontend**: first working prototype

### Refactor

- **frontend**: improved ui
- **frontend**: new template introduced
- **frontend**: new template (wip)
- **frontend**: WIP
- **frontend**: new "file" endpoint
- **api+frontend**: -introduction of a new frontend file endpoint

## 0.3.0 (2025-11-22)

### Feat

- **api:file**: add csv preview, match processing and selective apply flow using in-memory storage
- **auth**: add X-Token header authentication with APIKeyHeader and env-based token validation

### Fix

- **api**: version form pyproject.toml
- **api**: overall small issues fix
- **api**: correction small error
- **api**: import error fix

### Refactor

- **all**: isort black ruff mypy
- **csv**: map additional fields: operation_amount, currencies, sender/recipient accounts
- **legacy-app-deleted**: legacy app deleted
- **api**: - extract upload and file endpoints into separate routers - move csv parsing and transaction processing to services/ - add centralized logging and encoding utilities - introduce config module for env settings - create clean app entrypoint with router registration - improve project structure for scalability and maintainability
- **all**: black isort ruff

## 0.2.0 (2025-11-20)

### Feat

- **auth**: add X-Token header authentication with APIKeyHeader and env-based token validation

### Refactor

- **csv**: map additional fields: operation_amount, currencies, sender/recipient accounts

## 0.1.1 (2025-11-17)

### Fix

- **api**: import error fix

### Refactor

- **legacy-app-deleted**: legacy app deleted
- **api**: - extract upload and file endpoints into separate routers - move csv parsing and transaction processing to services/ - add centralized logging and encoding utilities - introduce config module for env settings - create clean app entrypoint with router registration - improve project structure for scalability and maintainability
- **all**: black isort ruff

## v2.7.0 (2026-03-11)

### Feat

- **users**: add invite-based password setup workflow

## v2.6.0 (2026-03-10)

### Refactor

- improve allegro matching preview and auth token handling

## v2.6.0rc1 (2026-03-08)

### Fix

- **allegro**: add paginated match cache and cache invalidation endpoint
- **allegro**: add paginated match cache and cache invalidation endpoint
- **main**: align docs url to production stack

### Refactor

- **allegro**: remove batch fetch and support order pagination
- **secrets**: added short id for secrets
- unify job status enums across domain, stats, and API layers

## v2.6.0rc0 (2026-02-28)

### Refactor

- unify job status enums across domain, stats, and API layers  and  added short id for secrets

## v2.6.0b4 (2026-02-28)

### Fix

- **stats**: set RUNNING eagerly and clear stale metrics during recompute

## v2.6.0b3 (2026-02-27)

### Refactor

- unify job status enums across domain, stats, and API layers (#24)

## v2.6.0b2 (2026-02-27)

### Fix

- recover version display in swagger docs

### Refactor

- **allegro**: add auto-apply endpoint and detailed apply job outcomes
- **allegro**: add auto-apply for single matches and track apply job tx results

## v2.6.0b1 (2026-02-27)

### Feat

- **allegro**: auto-apply single matches with job tracking

## v2.6.0b0 (2026-02-12)

### Refactor

- **allegro**: enrich payments with metadata and external ids
- **allegro**: add apply job workflow with state store and API endpoints
- **allegro**: enrich payments with metadata and external ids

## v2.6.0a1 (2026-02-08)

### Fix

- **docker**: fix(docker): run alembic using venv instead of uv in runtime

## v2.6.0a0 (2026-02-08)

### Feat

- **allegro**: add payment fetching and match preview endpoints
- **allegro**: add payment fetching and match preview endpoints

### Fix

- **alembic**: align env.py with src layout and sqlite batch mode

## v2.5.0 (2026-02-05)

### Feat

- **allegro**: add metrics endpoints and Firefly-backed stats service
- **user-secrets**: introduce secure user secrets management with audit trail
- **blik**: add snapshot-based BLIK statistics API alongside legacy endpoints
- **tx**: add tx stats
- **users**: add admin audit log endpoint and tests
- **users**: add enable, demote, and delete user actions with audit logs
- **db**: add alembic setup and initial migration
- **users**: add audit log for admin actions and adapt tests
- **api**: enrich simplified tx with currency, type, and fx fields
- add currency/fx context and tx type to Transaction, bump luciferin

### Refactor

- **api**: add metrics fetch duration and router-level auth deps
- **allegro**: add domain models and service layer with improved error handling
- **api**: add metrics fetch duration and router-level auth deps
- **api**: centralize Firefly dependencies and runtime services
- **tx**: switch to snapshot-based async metrics with generic runner
- **system**: addded bootstrap status to health endpoint
- **system**: enhanced boostrap and health endpoints
- **system**: move app version to app.state and remove router init side effects
- **db**: migration to alembic

## v2.4.0 (2026-02-01)

## v2.4.0b0 (2026-01-25)

### Feat

- **api**: enrich simplified tx with currency, type, and fx fields

## v2.3.1a0 (2026-01-19)

### Fix

- **docker**: fix in dockerfile

## v2.3.0 (2026-01-19)

### Feat

- add db engine
- **auth**: add /me endpoint and enforce active users
- **users**: add superuser-only user management API
- **system**: add bootstrap endpoint and switch to argon2
- **db**: dd user domain model and repository with SQLite support
- **allegro**: add Allegro API adapter

### Fix

- **blik**: fixed potential path traversal by validating file identifiers and enforcing temp directory confinement
- **blik**: prevent cache reset by using singleton BlikApplicationService

### Refactor

- **auth**: unify JWT config via settings to fix CI/local mismatch
- **app**: switch to application factory and uvicorn --factory to fix CI bootstrap issues
- **auth**: switch authentication from env users to database
- refactor tx flow to application service and add service tests
- reformat reflecting changes in ff client

## v2.2.7 (2026-01-16)

### Refactor

- refactor in service level

## v2.2.6 (2026-01-01)

### Refactor

- **logging**: add configurable log level and structured startup logs

## v2.2.5 (2025-12-31)

### Refactor

- **auth**: handle refresh token, added tests
- **auth**: move refresh token settings to config
- **auth**: add refresh flow; add pytest-cov config

## v2.2.4 (2025-12-29)

### Refactor

- **tx**: added tag eindpoint

## v2.2.3 (2025-12-27)

### Refactor

- **tx**: add monthly screening endpoint with date range filtering

## v2.2.2 (2025-12-27)

### Fix

- **tx**: remove processed items from cache

## v2.2.1 (2025-12-27)

### Fix

- **tx**: fixed problem with assign category

## v2.2.0 (2025-12-26)

### Feat

- add tx router and code refactor with ruff (tier 1 & tier 2)

## v2.1.3 (2025-12-22)

### Fix

- **ci**: force rebuild

## v2.1.2 (2025-12-22)

### Fix

- **blik**: fixed logic in stats calculation logic

## v2.1.1 (2025-12-22)

### Fix

- **blik**: add cached statistics with refresh endpoint
- **tx_processor**: fixes #3 - apply match

## v2.1.0 (2025-12-14)

### Feat

- **blik**: introduce stats and share models with pandas
- **blik**: improve record pretty print and refresh docs

### Fix

- **blik**: removed git artifacts

## v2.0.1 (2025-12-13)

### Fix

- **auth**: update router prefix to /api/auth

## v2.0.0 (2025-12-07)

### BREAKING CHANGE

- api endpoints changed

### Feat

- **test**: test
- **infra**: add full dockerization setup with reverse proxy and health-checked backend stack
- **settings**: refactor middleware configuration into centralized settings layer
- **api**: add version endpoint, improve health response, and align BLIK models
- **api**: restructure API into clear namespaces and introduce blik_files pipeline
- **frontend**: first working prototype
- **api:file**: add csv preview, match processing and selective apply flow using in-memory storage
- **auth**: add X-Token header authentication with APIKeyHeader and env-based token validation

### Fix

- **api**: CORS middleware added
- **main**: Updated main.py to import settings first and remove deprecated dotenv calls
- **api**: version form pyproject.toml
- **api**: overall small issues fix
- **api**: correction small error
- **api**: import error fix

### Refactor

- **settings**: remove legacy config.py and migrate all env access to unified settings
- **api**: isort ruff black mypy
- **api**: migrate backend to a clean src-based project layout and update imports
- **api**: -add response model to allpy matches endpoint
- **auth**: - replace os.getenv usage with shared `settings` instance  - explicitly type JWT payload to resolve Pylance update() errors  - clean up auth flow and remove debug prints
- **ui**: deleted login and upload pages
- **api**: introduce typed Pydantic response models for file and upload endpoints
- **config**: introduce Settings class and centralized .env loading
- **project**: reorganize project structure into backend + frontend architecture
- **frontend**: improved ui
- **frontend**: new template introduced
- **frontend**: new template (wip)
- **frontend**: WIP
- **frontend**: new "file" endpoint
- **api+frontend**: -introduction of a new frontend file endpoint
- **all**: isort black ruff mypy
- **csv**: map additional fields: operation_amount, currencies, sender/recipient accounts
- **legacy-app-deleted**: legacy app deleted
- **api**: - extract upload and file endpoints into separate routers - move csv parsing and transaction processing to services/ - add centralized logging and encoding utilities - introduce config module for env settings - create clean app entrypoint with router registration - improve project structure for scalability and maintainability
- **all**: black isort ruff
