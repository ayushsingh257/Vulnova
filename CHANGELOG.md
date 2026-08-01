# Vulnova — Project Changelog (CHANGELOG.md)

All notable changes to the Vulnova project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **CI Dependency Installation**: Configured `.github/workflows/ci.yml` backend verification step to install directly from the authoritative `backend/requirements.txt` source, ensuring `sqlalchemy`, `asyncpg`, `alembic`, `black`, and all backend dependencies are available during CI execution.

### Added
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
