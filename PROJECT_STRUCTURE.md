# Vulnova — Canonical Repository Structure Specification (PROJECT_STRUCTURE.md)

This document serves as the **single source of truth** for the physical directory layout, module boundaries, folder responsibilities, naming conventions, and structural evolution rules for **Vulnova**.

Every file and directory created in Vulnova must strictly conform to this specification. No new top-level or sub-level directory may be introduced without first documenting its architecture, owner, and purpose in this file.

---

## 🏛️ 1. Repository Philosophy & Architectural Axioms

Vulnova is engineered as an enterprise-grade AppSec platform designed to operate at commercial scale. Its repository structure reflects the following principles:

1. **Scalability & Monorepo Readiness**: Clear physical separation between frontend presentation, backend control plane, isolated scanner plugins, and deployment infrastructure.
2. **Clean Architecture Isolation**: Strict physical enforcement of Clean Architecture layers (`domain/`, `application/`, `infrastructure/`, `api/`).
3. **High Discoverability**: Intuitive folder naming and predictable file locations so new engineers can navigate the codebase immediately.
4. **Explicit Module Ownership**: Every directory has a defined owner (SecOps, Core Backend, Frontend, AI Engineering) and strict allowed/forbidden file rules.
5. **Zero Dumping Grounds**: Generic `/misc` or `/utils` dumping grounds are strictly banned. Utilities must be contextualized within their domain.

---

## 🌳 2. Master Repository Layout

Below is the canonical repository layout for Vulnova:

```text
Vulnova/
│
├── .github/                         # GitHub platform workflows and community templates
│   ├── workflows/                   # CI/CD pipelines (SAST, SCA, Pytest, Next.js, Docker)
│   ├── ISSUE_TEMPLATE/              # Structured bug report & feature request templates
│   └── PULL_REQUEST_TEMPLATE.md     # Mandatory PR review checklist & verification template
│
├── frontend/                        # Next.js 14 Web Application & Enterprise Trust Center
│   ├── app/                         # App Router pages (Public, Dashboard, Settings, Trust Center)
│   │   ├── (public)/                # Landing, Features, Pricing, Trust Center (/trust), Security
│   │   ├── (auth)/                  # Login, Registration, MFA, Password Reset
│   │   ├── (dashboard)/             # Scans, Findings, Asset Surface, Triage, Settings
│   │   └── api/                     # Next.js BFF (Backend For Frontend) API proxy handlers
│   ├── components/                  # UI Component Library
│   │   ├── ui/                      # Low-level atomic components (shadcn/ui primitives)
│   │   ├── dashboard/               # Risk cards, visual charts, live progress bars
│   │   ├── trust/                   # Trust Center badges, compliance cards, status indicator
│   │   ├── ai/                      # AI code patch viewers, attack graph renderers
│   │   └── common/                  # Shared layouts, headers, footers, theme switcher
│   ├── hooks/                       # Custom React hooks (useScanWebSocket, useAuth, useTheme)
│   ├── lib/                         # Frontend utility functions, API clients, TanStack Query
│   ├── styles/                      # Global CSS, Tailwind custom design tokens (Crimson/Obsidian)
│   ├── public/                      # Static web assets, branding SVGs, compliance badges
│   └── tests/                       # Playwright E2E UI tests & Vitest unit tests
│
├── backend/                         # FastAPI Control Plane & Core Application Logic
│   ├── app/                         # Main Python application package
│   │   ├── api/                     # FastAPI HTTP Routers, Middleware, & OpenAPI Schemas
│   │   │   ├── v1/                  # API Version 1 Routers (auth, targets, scans, plugins, findings)
│   │   │   ├── dependencies/        # FastAPI Auth & RBAC dependency injectors
│   │   │   └── schemas/             # Pydantic v2 request/response models
│   │   ├── application/             # Use Cases & Application Service Coordinators
│   │   │   ├── assessment/          # AssessmentService, RiskIntelligenceEngine, FindingDeduplicator, DTOs
│   │   │   ├── use_cases/           # Scan launch, finding triage, report generation workflows
│   │   │   └── services/            # Domain service orchestrators
│   │   ├── domain/                  # Pure Business Logic (No external framework dependencies)
│   │   │   ├── entities/            # User, Organization, Target, Finding, CVSS, EPSS, Evidence entities
│   │   │   ├── value_objects/       # CVSSScore, TargetURL, SeverityLabel value objects
│   │   │   └── ports/               # Abstract Interfaces (ScannerPort, AIProviderPort, EventBusPort)
│   │   ├── infrastructure/          # Adapters & External System Implementations
│   │   │   ├── assessment/          # 10 DAST Security Plugins, PluginRegistry, EvidenceCollectionEngine
│   │   │   ├── storage/             # EvidenceArtifactStorage (local filesystem & cloud object store adapter)
│   │   │   ├── db/                  # Async SQLAlchemy models, Alembic migrations, pgvector, Repositories
│   │   │   ├── cache/               # Redis caching client & token bucket rate limiter
│   │   │   ├── messaging/           # Celery task definitions & Event Bus publisher
│   │   │   ├── ai/                  # Multi-provider LLM gateway & RAG retrieval engine
│   │   │   └── logging/             # Structlog structured JSON logger & correlation tracing
│   │   ├── security/                # Cryptography, JWT tokens, Argon2id hashing, TOTP MFA
│   │   └── workers/                 # Celery background worker task entrypoints
│   ├── migrations/                  # Alembic database migration scripts
│   ├── scripts/                     # Local seed scripts & DB maintenance utilities
│   └── tests/                       # Pytest unit, integration, and security test suite (148 passed)
│
├── plugins/                         # Modular Security Assessment Plugins
│   ├── sqli_assessment/             # SQL Injection Plugin (plugin.yaml, plugin.py, payloads.json)
│   ├── xss_assessment/              # Cross-Site Scripting Plugin
│   ├── ssrf_assessment/             # Server-Side Request Forgery Plugin
│   ├── idor_assessment/             # Broken Object Level Authorization Plugin
│   └── jwt_analyzer/                # JWT Security Analyzer Plugin
│
├── infrastructure/                  # Production Infrastructure as Code (IaC) & Cloud Provisioning
│   ├── terraform/                   # AWS / GCP Infrastructure Provisioning (EKS, RDS, Redis)
│   └── helm/                        # Kubernetes Helm Charts for Vulnova services
│
├── docker/                          # Containerization Configurations
│   ├── Dockerfile.frontend          # Multi-stage Next.js production build
│   ├── Dockerfile.backend           # Multi-stage FastAPI production build
│   ├── Dockerfile.sandbox           # Unprivileged Scanner Worker Container build
│   ├── docker-compose.yml           # Development local orchestration
│   └── docker-compose.prod.yml      # Production stack composition
│
├── deployment/                      # Deployment Configurations & Reverse Proxy Settings
│   ├── traefik/                     # Traefik dynamic routing & TLS certificate configuration
│   └── nginx/                       # Nginx reverse proxy configuration
│
├── testing/                         # DAST Verification Benchmark Testbed
│   ├── benchmark_apps/              # Intentionally vulnerable benchmark apps (JuiceShop, DVWA)
│   └── regression_suite/            # Security regression verification test scripts
│
├── docs/                            # Internal Developer & Architecture Documentation
│   ├── architecture/                # Extended C4 diagrams and sequence flows
│   ├── security/                    # Security threat matrices and ASVS compliance checklists
│   └── api/                         # Exported OpenAPI specs and Postman collections
│
├── assets/                          # Official Project Assets & Visual Branding
│   ├── logo/                        # Vulnova logo vectors and icon kits
│   └── screenshots/                 # Dashboard UI visual previews
│
├── examples/                        # Integration Code Examples & SDK Usage Samples
│   ├── python_sdk_sample.py         # Sample Python client calling Vulnova API
│   └── github_action_pipeline.yml   # Sample CI/CD pipeline step integrating Vulnova CLI
│
├── README.md                        # Root Project Overview & Getting Started Guide
├── BRAIN.md                         # Permanent Memory, Architectural Axioms, & CI Rules
├── ROADMAP.md                       # 12-Era Master Roadmap (100+ phases with ✅ tracking)
├── PROJECT_STRUCTURE.md             # Canonical Repository Structure Blueprint (This file)
├── ARCHITECTURE.md                  # System Architecture, Sandbox Isolation, & Event Bus
├── TECH_STACK.md                    # Technology Matrix & Selection Justification
├── SECURITY.md                      # Security Policy, Sandbox Isolation, Legal Authorization
├── THREAT_MODEL.md                  # Formal STRIDE Threat Analysis & Mitigation Controls
├── DATABASE.md                      # PostgreSQL DDL Schemas, pgvector Indexing, & Redis
├── API_SPEC.md                      # REST OpenAPI 3.1 & WebSocket Protocol Specs
├── FRONTEND_GUIDELINES.md           # UI Design System Tokens & Trust Center Specs
├── BACKEND_GUIDELINES.md            # Clean Architecture Guidelines & Python Standards
├── TESTING.md                       # Test Strategy, Coverage Thresholds, & QA Benchmarks
├── DEVSECOPS.md                     # CI/CD Pipelines, SAST/SCA Gates, Container Hardening
├── DEPLOYMENT.md                    # Production Deployment & Helm Blueprint
├── STYLE_GUIDE.md                   # Linting Rules, Code Formatting, & Commit Specs
├── DECISIONS.md                     # Architectural Decision Records (ADRs 001–007)
├── CHANGELOG.md                     # Keep a Changelog Release History
├── CONTRIBUTING.md                  # Contributor Onboarding & Pull Request Guidelines
└── LICENSE                          # MIT Open Source License
```

---

## 📦 3. Directory Responsibilities & Governance

### A. `/frontend`
- **Purpose**: Hosts the Next.js 14 web application, interactive security dashboard, and Trust Center.
- **Allowed Files**: TypeScript (`.ts`, `.tsx`), CSS (`.css`), JSON configurations, SVG assets.
- **Forbidden Files**: Python backend code, raw SQL scripts, unencrypted private keys.
- **Dependencies**: React, Next.js, TailwindCSS, Framer Motion, TanStack Query, `shadcn/ui`.
- **Owner**: Staff Frontend Engineer.
- **Relationship**: Communicates exclusively with `/backend/app/api` via HTTP/REST and WebSockets.

### B. `/backend`
- **Purpose**: Contains the core FastAPI application, business domain models, security checks, and AI workflows.
- **Allowed Files**: Python source (`.py`), Alembic migrations (`.py`, `.ini`), SQL DDL (`.sql`).
- **Forbidden Files**: React/TSX files, raw web template frameworks.
- **Dependencies**: Python 3.12+, FastAPI, Pydantic v2, AsyncIO, SQLAlchemy, Celery, structlog.
- **Owner**: Lead Backend Architect & Principal Security Engineer.
- **Relationship**: Exposes REST APIs to `/frontend`, dispatches background tasks to `/plugins` and Celery workers, queries PostgreSQL/Redis.

### C. `/plugins`
- **Purpose**: Holds self-describing, modular security assessment plugins.
- **Allowed Files**: `plugin.yaml`, Python scanner modules (`plugin.py`), payload data files (`.json`, `.txt`).
- **Forbidden Files**: Direct DB access drivers, core control plane routing code.
- **Dependencies**: Vulnova `AssessmentPluginPort` abstract interface.
- **Owner**: Security Research Team.
- **Relationship**: Loaded dynamically by `/backend/app/infrastructure/plugins`.

### D. `/docker` & `/infrastructure`
- **Purpose**: Manages container build specs, local orchestration, and Terraform/Helm deployment assets.
- **Allowed Files**: `Dockerfile`, `docker-compose.yml`, `.tf`, `.yaml` Helm templates.
- **Forbidden Files**: Application domain source code.
- **Owner**: DevSecOps Engineer.

---

## 📐 4. File & Directory Naming Standards

1. **Python Files & Folders**: Lowercase `snake_case` (e.g., `scan_orchestrator.py`, `user_entity.py`).
2. **TypeScript / React Components**: `PascalCase` for components (e.g., `RiskScoreCard.tsx`), `camelCase` for hooks & utility functions (e.g., `useScanWebSocket.ts`).
3. **Plugin Folders**: Lowercase `snake_case` with explicit `_assessment` suffix (e.g., `sqli_assessment/`).
4. **Markdown Documents**: Uppercase `SNAKE_CASE` in root directory (e.g., `PROJECT_STRUCTURE.md`), lowercase `kebab-case` in `/docs/`.
5. **Database Migrations**: Timestamped prefix followed by descriptive snake_case (e.g., `20260801_create_scan_profiles_table.py`).
6. **Dockerfiles**: `Dockerfile.<service>` format (e.g., `Dockerfile.backend`, `Dockerfile.sandbox`).

---

## 🚧 5. Architectural Communication Boundaries

To guarantee maintainability, Vulnova enforces strict communication rules across layers:

```
 [Frontend Web UI]
         │ (HTTP REST / WebSockets)
         ▼
 [FastAPI Control Plane: API Gateway]
         │
         ▼
 [Application Layer: Use Cases & Orchestration]
         │
         ▼
 [Domain Layer: Pure Entities & Value Objects] ◄──┐ (Implements Interfaces)
                                                  │
 [Infrastructure Layer: DB, Redis, Celery, AI] ───┘
```

### Forbidden Direct Communication Paths:
- ❌ `Domain Layer` MUST NEVER import from `API Gateway`, `SQLAlchemy`, `FastAPI`, or `Next.js`.
- ❌ `Frontend` MUST NEVER connect directly to PostgreSQL or Redis.
- ❌ `Scanner Sandbox Plugins` MUST NEVER execute inside the API Gateway process.
- ❌ `AI Analyst Engine` MUST NEVER directly mutate relational database entities without going through Domain Use Cases.

---

## 📈 6. Repository Growth & Refactoring Rules

1. **Rule of Contextual Grouping**: Never create a generic `/utils` or `/misc` directory. Utility functions must reside near their domain consumer (e.g., `backend/app/application/utils/` or `frontend/lib/`).
2. **Plugin Isolation**: Every security plugin must be self-contained within `/plugins/<plugin_name>/`. Plugins must not depend on other plugins.
3. **Documentation Precedence**: If a feature requires introducing a new top-level directory or reorganizing a core subsystem, `PROJECT_STRUCTURE.md` MUST be updated and committed prior to starting implementation.

---

## 🔮 7. Future Repository Expansion Reserved Paths

The following directory paths are reserved for future engineering eras:

- `enterprise/`: Enterprise Edition proprietary features (SAML/Single Sign-On, Advanced Compliance Reports).
- `cloud/`: Cloud SaaS platform multi-region management services.
- `cli/`: `vulnova-cli` command-line scanner client for CI/CD pipelines.
- `sdk/`: Official Python and TypeScript client SDKs.
- `marketplace/`: Security Plugin Marketplace submission pipeline.
- `research/`: Security vulnerability research, exploit benchmarks, and novel DAST detection papers.
