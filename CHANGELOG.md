# Vulnova — Project Changelog (CHANGELOG.md)

All notable changes to the Vulnova project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **CI Dependency Installation**: Configured `.github/workflows/ci.yml` backend verification step to install directly from the authoritative `backend/requirements.txt` source, ensuring `sqlalchemy`, `asyncpg`, `alembic`, `black`, and all backend dependencies are available during CI execution.
- **DevSecOps Security Pipeline Stabilization (Phase 1.6)**:
  - Replaced deprecated Semgrep `p/owasp-top-10` ruleset with active `p/default` and `p/security-audit` rulesets.
  - Corrected invalid commit SHA references for `actions/setup-python` and `actions/setup-node` (verified via `git ls-remote`).
  - Pinned all GitHub Actions to immutable 40-character commit SHAs for supply chain security.
  - Replaced Gitleaks, Semgrep, and Trivy third-party action wrappers with direct CLI binary installations for reliability.
  - Installed Trivy via official APT repository instead of fragile `curl | sh` script.
- **Auth CI Fix (`f9af674`)**: Added missing `email-validator>=2.1.0` to `requirements.txt` and `pyproject.toml`. Pydantic `EmailStr` requires this package at import time; omission caused `ModuleNotFoundError` in CI fresh environments.

### Added
- **Era 2 Phase 2.4 (API Key Management System)** (`9a66038`):
  - Implemented API key security module (`app/security/api_key.py`) with `vn_live_` prefix generation, SHA-256 hashing (raw key never stored), and constant-time `hmac.compare_digest` verification.
  - Created API key repository (`app/infrastructure/database/repositories/api_key_repository.py`) with CRUD operations, tenant-scoped queries, `selectinload` relationship loading, and type-safe `DELETE ... RETURNING` SQLAlchemy 2.0 pattern.
  - Created application DTOs (`app/application/api_keys/dto.py`) — `CreateAPIKeyRequest`, `APIKeyCreateResponse` (raw key returned once), `APIKeyResponse`, `APIKeyListResponse`.
  - Implemented API key service (`app/application/api_keys/services.py`) with creation (SHA-256 hash storage), authentication (prefix lookup + constant-time verification + expiry check), `last_used_at` tracking, listing, and revocation with structured audit logging.
  - Created dual-mode authentication dependency (`app/api/v1/dependencies/api_key.py`) — `get_api_key_user` (X-API-Key only) and `get_current_user_or_api_key` (JWT Bearer priority → X-API-Key fallback) using `typing.Annotated`.
  - Created API key router (`app/api/v1/routers/api_keys.py`) — `POST /api/v1/api-keys`, `GET /api/v1/api-keys`, `DELETE /api/v1/api-keys/{key_id}` with RBAC `require_permission()` guards.
  - Added comprehensive test suite (`tests/test_api_keys.py`) — 4 tests covering key generation/hashing/verification, full service lifecycle, dual-mode auth priority/fallback, and API-key-only authentication.
  - Removed redundant `cast()` calls in `password.py` (replaced by `types-passlib` stubs).
  - Added `types-passlib>=1.7.7.20240106` to dev dependencies.
  - Fixed `Callable` type hints in `rbac.py` to use `Callable[..., Any]`.
  - Fixed CI mypy step with `PYTHONPATH` env and removed `--config-file` flag.
- **Era 2 Phase 2.3 (Multi-Tenant RBAC Security Layer)** (`1238faf`):
  - Implemented domain `Role` hierarchy (`OWNER > ADMIN > SECURITY_ANALYST > VIEWER`) and centralized `PERMISSION_MAP` in `app/domain/entities/role.py`.
  - Implemented security authorization dependencies (`require_role()`, `require_permission()`, `require_same_organization()`, `verify_organization_access()`) in `app/security/rbac.py`.
  - Created API v1 dependency re-exporter `app/api/v1/dependencies/rbac.py`.
  - Implemented fail-safe invalid role fallback to `Role.VIEWER` to prevent privilege escalation.
  - Implemented tenant isolation enforcement blocking cross-organization resource access with HTTP 403 `ForbiddenException`.
  - Added comprehensive test suite (`tests/test_rbac.py`) — 15 tests covering role ordering, permission map resolution, invalid role defaults, FastAPI dependency authorization checks, and tenant boundary enforcement.
- **Era 2 Phase 2.2 (JWT & OAuth2 Authentication Framework)** (`6682970`, `f9af674`):
  - Implemented Argon2id password hashing adapter (`app/security/password.py`) via `passlib[argon2]`.
  - Implemented HS256 JWT access token creation and validation (`app/security/jwt.py`) with 15-minute expiry and claims (`sub`, `user_id`, `organization_id`, `role`, `token_type`, `exp`).
  - Implemented SHA-256 refresh token hashing for secure database storage.
  - Created auth repositories (`UserRepository`, `OrganizationRepository`, `RefreshTokenRepository`) with family-based token revocation for reuse detection.
  - Created application-layer DTOs (`RegisterRequest`, `LoginRequest`, `RefreshRequest`, `TokenResponse`, `UserResponse`) in `app/application/auth/dto.py`.
  - Implemented `AuthService` (`app/application/auth/services.py`) with register, login, refresh (rotation + reuse detection), logout, and get_me use cases.
  - Created FastAPI OAuth2PasswordBearer dependencies (`app/api/v1/dependencies/auth.py`) with `get_current_user` injection.
  - Created auth router (`app/api/v1/routers/auth.py`) with `/api/v1/auth/register`, `/login`, `/refresh`, `/logout`, `/me` endpoints and HTTP-Only `vulnova_refresh_token` secure cookies.
  - Added comprehensive test suite (`tests/test_auth.py`) — 48 tests covering password hashing, JWT round-trips, token hashing, AuthService integration, and API endpoint behavior.
  - Added `email-validator>=2.1.0`, `pyjwt>=2.8.0`, `passlib[argon2]>=1.7.4`, `argon2-cffi>=23.1.0`, `python-multipart>=0.0.9` to production dependencies.
- **Era 2 Phase 2.1 (Database Entity Models & Alembic Migration)**:
  - Created pure domain entity dataclasses (`Organization`, `User`, `RefreshToken`, `APIKey`, `AuditLog`) in `app/domain/entities/`.
  - Implemented SQLAlchemy 2.0 ORM models (`OrganizationModel`, `UserModel`, `RefreshTokenModel`, `APIKeyModel`, `AuditLogModel`) in `app/infrastructure/database/models/` with typed `Mapped` attributes and foreign keys.
  - Created Alembic migration `0002_create_core_platform_tables.py` generating database tables, foreign keys, cascading rules, and indexes.
  - Added unit test suites (`tests/test_domain_entities.py`, `tests/test_models.py`) verifying domain entity instantiation, ORM metadata registration, and Alembic revision chain integrity.
- **Era 1 Phase 1.7 (Structured Logging & Correlation ID Middleware)**:
  - Replaced hand-rolled stdlib JSON logging with production-grade `structlog` configuration (`app/core/logging.py`).
  - Added async-safe contextvars correlation ID module (`app/core/correlation.py`).
  - Extended `RequestIDMiddleware` (`app/security/middleware/request_id.py`) to automatically bind `request_id` into structlog contextvars.
  - Added HTTP request/response lifecycle logging middleware (`app/security/middleware/request_logging.py`) capturing method, path, status, and execution duration.
  - Updated FastAPI application (`app/main.py`) to use `structlog` key-value logging and registered request logging middleware.
  - Created comprehensive test suite (`tests/test_logging.py`) validating structlog BoundLogger factory, contextvars propagation, and request logging.
  - Updated `DEVELOPMENT.md` with Section 9 structured logging conventions.
- **Era 1 Phase 1.6 (DevSecOps GitHub Actions Pipelines & Automated Scanners)**:
  - Created `.github/workflows/security.yml` enforcing automated DevSecOps scanners.
  - Integrated Gitleaks secret detection (`gitleaks/gitleaks-action@v2`).
  - Integrated Semgrep SAST scanning (`semgrep/semgrep` OWASP Top 10 ruleset).
  - Integrated `pip-audit` for backend dependency vulnerability checking.
  - Integrated `npm audit` for frontend package vulnerability checking.
  - Integrated Trivy container security scanning (`aquasecurity/trivy-action@master`).
  - Added `pip-audit>=2.7.0` to `backend/requirements.txt` and `pyproject.toml`.
  - Updated `DEVELOPMENT.md` with Section 8 local security verification tools and security gate enforcement rules.
- **Era 1 Phase 1.5 (Backend Application Foundation & API Architecture)**:
  - Clean Architecture package layout (`api/v1/`, `application/`, `domain/`, `infrastructure/`, `security/`, `core/`).
  - Enhanced Pydantic `Settings` configuration (`app/core/config.py`).
  - Structured JSON logging module with request correlation ID tracking (`app/core/logging.py`).
  - Enterprise exception hierarchy (`VulnovaException`, `ResourceNotFoundException`, `UnauthorizedException`, `ForbiddenException`, `ValidationException`).
  - Security middleware: `RequestIDMiddleware` (`X-Request-ID`), `SecurityHeadersMiddleware` (OWASP security headers).
  - API v1 router aggregator and system operational status endpoint (`GET /api/v1/status`).
  - Unit & integration test suites (`test_api_v1.py`, `test_middleware.py`, `test_config.py`).
- **Era 1 Phase 1.4 (Database Foundation & Migration Infrastructure)**:
  - Created SQLAlchemy 2.0 Async engine, `async_sessionmaker` session factory (`backend/app/infrastructure/database/session.py`), and Declarative `Base` (`base.py`).
  - Added Alembic database migration system (`alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`).
  - Implemented initial migration `0001_enable_postgresql_extensions.py` enabling PostgreSQL `uuid-ossp` and `vector` (`pgvector`) extensions.
  - Extended `/ready` health probe in `backend/app/main.py` to test database connectivity (`SELECT 1`).
  - Created database test suite (`backend/tests/test_database.py`) verifying DB session lifecycle and readiness probes.
- **Era 1 Phase 1.3 (Containerization & Local Infrastructure Environment)**:
  - Hardened multi-stage `backend/Dockerfile` (`python:3.12-slim`, unprivileged `appuser` UID 10001, `/health` probe).
  - Hardened multi-stage `frontend/Dockerfile` (`node:20-alpine`, `output: 'standalone'`, unprivileged `nextjs` UID 10001).
  - Orchestrated `docker-compose.yml` with PostgreSQL 16 (`pgvector/pgvector:pg16`), Redis 7 (`redis:7.2-alpine`), `vulnova_net` bridge network, persistent volumes, and healthchecks.
  - Canonical Docker build specs in `docker/Dockerfile.backend` and `docker/Dockerfile.frontend`.
  - Updated `DEVELOPMENT.md` with Docker Compose lifecycle commands and database/cache CLI access.
  - Added Docker Compose syntax validation job step to `.github/workflows/ci.yml`.
- **Era 1 Phase 1.2 (Development Toolchain & Dependency Management)**:
  - Created `DEVELOPMENT.md` developer onboarding handbook and command reference guide.
  - Added root `package.json` for monorepo script orchestration (`npm run dev`, `npm run build`, `npm run lint`, `npm run type-check`, `npm run test`, `npm run format`).
  - Added `format` and `format:check` scripts to `frontend/package.json`.
  - Configured `.pre-commit-config.yaml` for pre-commit verification (Black, Ruff, ESLint, Prettier, check-yaml).
  - Enhanced `.github/workflows/ci.yml` CI pipeline with Black formatting check, ESLint, type checking, and Next.js build verification.
- **Era 1 Phase 1.1 (Monorepo Structure & Workspace Configuration)**:
  - Physical monorepo directory layout (`frontend/`, `backend/`, `infrastructure/`, `docker/`, `deployment/`, `scripts/`, `testing/`, `plugins/`, `docs/`, `assets/`, `examples/`).
  - Next.js 14 App Router + TypeScript + TailwindCSS frontend foundation with strict mode enabled.
  - Python 3.12+ FastAPI Clean Architecture backend skeleton with `/health` and `/ready` endpoints.
  - Tooling configurations: Ruff, Black, Mypy for backend; ESLint, Prettier for frontend.
  - `.env.example` placeholder configuration and `docker-compose.yml` infrastructure setup.
  - GitHub Actions CI workflow pipeline (`.github/workflows/ci.yml`).

---

## [0.0.0-sprint0] - 2026-08-01

### Added
- Project initialization & Sprint 0 / Era 0 architectural design blueprint.
- Defined 12 Engineering Eras spanning 100+ implementation phases.
- Designed system C4 architecture, Clean Architecture guidelines, and microservice migration path.
- Established PostgreSQL (`pgvector`) schema, REST API OpenAPI 3.1 specifications, and WebSocket streaming contracts.
- Defined Crimson Red & Obsidian Black enterprise frontend design system.
