# Vulnova — Project Changelog (CHANGELOG.md)

All notable changes to the Vulnova project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
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
