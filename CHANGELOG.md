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
