# Vulnova — Engineering Master Roadmap (ROADMAP.md)

This master roadmap outlines the **12 Engineering Eras** and **112 Implementation Phases** for building Vulnova into a commercial-grade Enterprise AI Application Security Platform.

> **Completion Tracking Rule**: Completed eras and phases receive a green check emoji `✅` indicating verified completion.

---

## 🏛️ ✅ Era 0: Architecture & Enterprise Documentation Foundation

### ✅ Phase 0.1: Project Setup & System Vision Document
- **Objective**: Establish project identity, vision, core goals, and repository foundation.
- **Deliverables**: Comprehensive `README.md` and `BRAIN.md`.
- **Dependencies**: None.
- **Completion Criteria**: Approved documentation files present in repository root.
- **Testing Requirements**: Markdown linting.

### ✅ Phase 0.2: Engineering Master Roadmap Specification
- **Objective**: Define granular 12-Era roadmap spanning discovery, scanning, AI, frontend, backend, security, and cloud deployment.
- **Deliverables**: `ROADMAP.md` with 100+ phases, dependencies, and verification criteria.
- **Dependencies**: Phase 0.1.
- **Completion Criteria**: Complete structured roadmap available for team tracking.
- **Testing Requirements**: Verification of links and phase completeness.

### ✅ Phase 0.3: Architectural Blueprint & Microservice Migration Plan
- **Objective**: Design System Architecture, domain boundaries, and event pipelines.
- **Deliverables**: `ARCHITECTURE.md` with system C4 diagrams and sequence flows.
- **Dependencies**: Phase 0.2.
- **Completion Criteria**: Architectural documentation covering components and event flows.
- **Testing Requirements**: Diagram syntax verification.

### ✅ Phase 0.4: Technology Stack & Tooling Matrix
- **Objective**: Select and document core tech stack components and versions.
- **Deliverables**: `TECH_STACK.md` detailing Next.js, FastAPI, PostgreSQL, Redis, Celery, and Vector DB.
- **Dependencies**: Phase 0.3.
- **Completion Criteria**: Technical specification document finalized.
- **Testing Requirements**: Tech stack constraint validation.

### ✅ Phase 0.5: Security Policy & ASVS Matrix
- **Objective**: Specify OWASP ASVS v4.0 alignment, authentication, RBAC, and disclosure rules.
- **Deliverables**: `SECURITY.md`.
- **Dependencies**: Phase 0.4.
- **Completion Criteria**: Security framework documented and approved.
- **Testing Requirements**: Security policy completeness audit.

### ✅ Phase 0.6: STRIDE Threat Model & Risk Analysis
- **Objective**: Build formal threat model across client, API gateway, scanner engines, and AI pipelines.
- **Deliverables**: `THREAT_MODEL.md`.
- **Dependencies**: Phase 0.5.
- **Completion Criteria**: STRIDE threat vectors and mitigations documented.
- **Testing Requirements**: Threat matrix coverage validation.

### ✅ Phase 0.7: PostgreSQL Relational & Vector Schema Design
- **Objective**: Model database schemas for multi-tenancy, scans, findings, embeddings, and audit logs.
- **Deliverables**: `DATABASE.md`.
- **Dependencies**: Phase 0.6.
- **Completion Criteria**: Entity relationship diagrams and Alembic migration strategy documented.
- **Testing Requirements**: SQL schema syntax validation.

### ✅ Phase 0.8: OpenAPI 3.1 REST API Specification
- **Objective**: Define REST API endpoints, schemas, authentication, and error codes.
- **Deliverables**: `API_SPEC.md`.
- **Dependencies**: Phase 0.7.
- **Completion Criteria**: Full API endpoint mapping documented.
- **Testing Requirements**: OpenAPI schema validation.

### ✅ Phase 0.9: Frontend & UI Design System Specification
- **Objective**: Design system guidelines, Light/Dark theme color palettes, and component hierarchy.
- **Deliverables**: `FRONTEND_GUIDELINES.md`.
- **Dependencies**: Phase 0.8.
- **Completion Criteria**: Design tokens and component specifications finalized.
- **Testing Requirements**: Design contrast accessibility check.

### ✅ Phase 0.10: Backend Clean Architecture Guidelines
- **Objective**: Establish Python FastAPI standards, Domain-Driven Design (DDD), and exception handling patterns.
- **Deliverables**: `BACKEND_GUIDELINES.md`.
- **Dependencies**: Phase 0.9.
- **Completion Criteria**: Backend coding standards documented.
- **Testing Requirements**: Code rule validation.

### ✅ Phase 0.11: Quality Assurance & Testing Strategy
- **Objective**: Define unit, integration, E2E, and DAST engine test frameworks.
- **Deliverables**: `TESTING.md`.
- **Dependencies**: Phase 0.10.
- **Completion Criteria**: Testing strategy and coverage benchmarks defined.
- **Testing Requirements**: Test execution flow validation.

### ✅ Phase 0.12: DevSecOps & CI/CD Pipeline Architecture
- **Objective**: Design GitHub Actions workflows for SAST, SCA, container scanning, and linting.
- **Deliverables**: `DEVSECOPS.md`.
- **Dependencies**: Phase 0.11.
- **Completion Criteria**: CI/CD security gate specifications ready.
- **Testing Requirements**: Workflow step validation.

### ✅ Phase 0.13: Production Deployment Blueprint
- **Objective**: Design multi-stage Docker Compose, reverse proxy, and cloud container deployment.
- **Deliverables**: `DEPLOYMENT.md`.
- **Dependencies**: Phase 0.12.
- **Completion Criteria**: Deployment guide and container architecture ready.
- **Testing Requirements**: Compose file schema check.

### ✅ Phase 0.14: Code Style Guide & Git Conventions
- **Objective**: Standardize linters, formatters, and commit conventions.
- **Deliverables**: `STYLE_GUIDE.md`.
- **Dependencies**: Phase 0.13.
- **Completion Criteria**: Commit guidelines and linting rules defined.
- **Testing Requirements**: Pre-commit hook configuration verification.

### ✅ Phase 0.15: Architectural Decision Records (ADRs)
- **Objective**: Document fundamental architecture choices and trade-offs.
- **Deliverables**: `DECISIONS.md`.
- **Dependencies**: Phase 0.14.
- **Completion Criteria**: Initial ADR set documented.
- **Testing Requirements**: ADR syntax validation.

### ✅ Phase 0.16: Release History & Change Management
- **Objective**: Setup initial changelog format.
- **Deliverables**: `CHANGELOG.md`.
- **Dependencies**: Phase 0.15.
- **Completion Criteria**: Sprint 0 version log documented.
- **Testing Requirements**: Markdown link check.

### ✅ Phase 0.17: Contributor Guide & Developer Setup
- **Objective**: Provide step-by-step developer environment onboarding guide.
- **Deliverables**: `CONTRIBUTING.md`.
- **Dependencies**: Phase 0.16.
- **Completion Criteria**: Onboarding documentation complete.
- **Testing Requirements**: Setup procedure validation.

### ✅ Phase 0.18: Era 0 Foundation Review & Approval Gate
- **Objective**: Audit all 18 documents for alignment, completeness, and enterprise readiness.
- **Deliverables**: Approved Sprint 0 foundation artifacts.
- **Dependencies**: Phases 0.1 - 0.17.
- **Completion Criteria**: 100% Sprint 0 documentation verification.
- **Testing Requirements**: Full repository documentation link and syntax audit.

---

## 🏛️ ✅ Era 0.5: Enterprise Architecture Refinement & Security Model Polish

### ✅ Phase 0.5.1: Scanner Sandbox Isolation Architecture Specification
- **Objective**: Specify container isolation, resource caps (1 vCPU, 512MB RAM), unprivileged execution (`UID 10001`), and egress firewalling.
- **Deliverables**: Sandbox updates in `ARCHITECTURE.md`, `SECURITY.md`, and `THREAT_MODEL.md`.
- **Dependencies**: Era 0.
- **Completion Criteria**: Dedicated scanner worker isolation model documented.
- **Testing Requirements**: Architecture diagram and threat validation.

### ✅ Phase 0.5.2: Extensible Security Plugin Framework Specification
- **Objective**: Design plugin engine and `plugin.yaml` manifest metadata schema for dynamic security checks.
- **Deliverables**: Plugin specifications in `ARCHITECTURE.md`, `ROADMAP.md`, `API_SPEC.md`, and `DECISIONS.md`.
- **Dependencies**: Phase 0.5.1.
- **Completion Criteria**: Plugin framework schema and APIs documented.
- **Testing Requirements**: YAML schema syntax validation.

### ✅ Phase 0.5.3: Event-Driven Evolution Roadmap & Legal Target Authorization
- **Objective**: Document event pipeline (`ScanCreatedEvent` -> `AIAnalysisCompletedEvent`) and legal scan authorization confirmation model.
- **Deliverables**: Event bus and legal safety updates in `ARCHITECTURE.md`, `SECURITY.md`, `THREAT_MODEL.md`, `DATABASE.md`, and `API_SPEC.md`.
- **Dependencies**: Phase 0.5.2.
- **Completion Criteria**: Event bus compatibility and target authorization specifications complete.
- **Testing Requirements**: Cross-document link audit.

### ✅ Phase 0.5.4: Database Extensions, Trust Center & Release Polish
- **Objective**: Add `scan_profiles`, `vulnerability_history`, `evidence_records`, Trust Center page specs, and README wording polish.
- **Deliverables**: Updates in `DATABASE.md`, `FRONTEND_GUIDELINES.md`, `README.md`, `BRAIN.md`, and `ROADMAP.md` (with `✅` tracking).
- **Dependencies**: Phase 0.5.3.
- **Completion Criteria**: All 10 Era 0.5 refinement tasks verified.
- **Testing Requirements**: Full document verification and GitHub release push.

---

## 🚀 Era 1: Infrastructure, Monorepo & DevSecOps Foundation

### ✅ Phase 1.1: Monorepo Structure & Workspace Configuration
- **Objective**: Initialize monorepo directory layout (`/frontend`, `/backend`, `/docker`, `/scripts`).
- **Deliverables**: Root `package.json`, Python `pyproject.toml`, workspace settings.
- **Dependencies**: Era 0.5.
- **Completion Criteria**: Clean directory structure with package management configured.
- **Testing Requirements**: Monorepo scripts initialization check.

### ✅ Phase 1.2: Development Toolchain & Dependency Management
- **Objective**: Establish professional dependency management, developer tooling (Ruff, Black, Mypy, ESLint, Prettier), DEVELOPMENT.md handbook, and pre-commit hooks.
- **Deliverables**: `DEVELOPMENT.md`, root `package.json`, `.pre-commit-config.yaml`, updated `pyproject.toml`, updated `.github/workflows/ci.yml`.
- **Dependencies**: Phase 1.1.
- **Completion Criteria**: Tooling commands pass cleanly; pre-commit hooks validated; CI pipeline green.
- **Testing Requirements**: Verification of `npm run build`, `pytest`, `mypy`, `ruff`, `black --check`.

### ✅ Phase 1.3: Containerization & Local Infrastructure Environment
- **Objective**: Docker Compose orchestration for local development stack (PostgreSQL 16 pgvector, Redis 7, FastAPI backend, Next.js frontend).
- **Deliverables**: Multi-stage hardened `backend/Dockerfile` and `frontend/Dockerfile`, `docker-compose.yml` with healthchecks & `vulnova_net` bridge, `DEVELOPMENT.md` Docker commands.
- **Dependencies**: Phase 1.2.
- **Completion Criteria**: Containers build and run under non-root users (`appuser`, `nextjs`), healthchecks pass, `docker compose config` passes.
- **Testing Requirements**: Verification of backend `/health`, frontend response, Docker config syntax check.

### ✅ Phase 1.4: Database Foundation & Migration Infrastructure
- **Objective**: Initialize Alembic database migrations, PostgreSQL async engine, connection pooling, and extension scripts (`uuid-ossp`, `pgvector`).
- **Deliverables**: SQLAlchemy 2.0 async engine in `backend/app/infrastructure/database/`, Alembic config (`alembic.ini`, `alembic/env.py`), initial migration `0001_enable_postgresql_extensions.py`, `/ready` DB health check.
- **Dependencies**: Phase 1.3.
- **Completion Criteria**: Alembic migrations run cleanly; DB connectivity probes succeed; unit tests pass.
- **Testing Requirements**: Async DB session test suite (`pytest tests/test_database.py`), Alembic heads validation.

### ✅ Phase 1.5: Backend Application Foundation & API Architecture
- **Objective**: Establish production-grade FastAPI application foundation, Clean Architecture boundaries, `/api/v1` routers, structured JSON logging, security middleware, and global error handlers.
- **Deliverables**: Config (`pydantic-settings`), Security middleware (`RequestIDMiddleware`, `SecurityHeadersMiddleware`), `/api/v1/status` endpoint, enterprise exception hierarchy (`VulnovaException`), unit test suite.
- **Dependencies**: Phase 1.4.
- **Completion Criteria**: Clean Architecture boundaries established; all health & status endpoints pass; pytest, Ruff, Black, and Mypy pass cleanly.
- **Testing Requirements**: Verification of API status endpoints, custom exceptions, and middleware stack.

### ✅ Phase 1.6: DevSecOps GitHub Actions Pipelines & Automated Scanners
- **Objective**: Configure automated CI/CD security pipelines for secret scanning (Gitleaks), SAST (Semgrep), dependency vulnerability audits (`pip-audit`, `npm audit`), and container scanning (Trivy).
- **Deliverables**: `.github/workflows/security.yml`, updated `.github/workflows/ci.yml`, `pip-audit` dependency in `backend/requirements.txt`, updated `DEVELOPMENT.md`.
- **Dependencies**: Phase 1.5.
- **Completion Criteria**: Automated security pipelines active; no secrets or critical vulnerabilities detected; GitHub Actions passes green check.
- **Testing Requirements**: Gitleaks secret detection, Semgrep OWASP ruleset, `pip-audit` scan, Trivy container config scan.

### ✅ Phase 1.7: Structured Logging & Correlation ID Middleware
- **Objective**: Implement structlog JSON logging with HTTP request correlation IDs.
- **Deliverables**: Structlog configuration (`app/core/logging.py`), contextvars correlation ID module (`app/core/correlation.py`), structlog-bound `RequestIDMiddleware`, HTTP `RequestLoggingMiddleware`, comprehensive unit tests (`tests/test_logging.py`).
- **Dependencies**: Phase 1.2.
- **Completion Criteria**: All logs emitted as structured JSON with trace IDs; correlation IDs auto-bound to structlog context; pytest, Ruff, Black, and Mypy pass cleanly.
- **Testing Requirements**: Test trace ID persistence across async contexts, structlog BoundLogger factory, HTTP request lifecycle logging.

---

## 🏢 Era 2: Core Platform & Tenant Management System

### Phase 2.1: Database Entity Models & SQLAlchemy Mappings
- **Objective**: Implement Users, Organizations, Memberships, Scan Profiles, Evidence, and Audit Logs models.
- **Deliverables**: `backend/app/models/user.py`, `organization.py`, `scan_profile.py`, `evidence.py`.
- **Dependencies**: Phase 1.6.
- **Completion Criteria**: Database tables created with correct foreign keys and indexes.
- **Testing Requirements**: Model unit tests and migration verification.

### Phase 2.2: JWT & OAuth2 Authentication Framework
- **Objective**: Build secure user registration, login, password hashing (Argon2id), and JWT access/refresh token rotation.
- **Deliverables**: Auth router endpoints (`/api/v1/auth/login`, `/api/v1/auth/refresh`).
- **Dependencies**: Phase 2.1.
- **Completion Criteria**: Users can register, log in, refresh tokens, and receive secure cookies.
- **Testing Requirements**: Unit & API tests for auth endpoints.

### Phase 2.3: Multi-Tenant RBAC Security Layer
- **Objective**: Enforce organization-level role permissions (Owner, Admin, Security Analyst, Viewer).
- **Deliverables**: RBAC dependency injectors (`require_permission`) in FastAPI.
- **Dependencies**: Phase 2.2.
- **Completion Criteria**: Unauthorized tenant access blocked with HTTP 403.
- **Testing Requirements**: Security tenant isolation tests.

### Phase 2.4: API Key Management System
- **Objective**: Provision and validate hashed API keys for machine-to-machine integrations.
- **Deliverables**: API key generation, revocation, and scope validation endpoints.
- **Dependencies**: Phase 2.3.
- **Completion Criteria**: Service accounts can authenticate via `X-API-Key` headers.
- **Testing Requirements**: API key authentication suite.

### Phase 2.5: User & Organization Management Endpoints
- **Objective**: CRUD endpoints for profiles, organization settings, and member invitations.
- **Deliverables**: `/api/v1/users` and `/api/v1/organizations` routers.
- **Dependencies**: Phase 2.3.
- **Completion Criteria**: Organization owners can manage team members and settings.
- **Testing Requirements**: Integration tests for tenant management.

### Phase 2.6: Security Audit Logging System
- **Objective**: Synchronous and asynchronous logging of critical security events to immutable database table.
- **Deliverables**: Audit logger service, `/api/v1/audit-logs` endpoint.
- **Dependencies**: Phase 2.5.
- **Completion Criteria**: Administrative actions recorded in audit log with client metadata.
- **Testing Requirements**: Audit log creation verification tests.

---

## 🔍 Era 3: Discovery Engine & Asset Surface Mapping

### Phase 3.1: Async HTTP Web Crawler Core
- **Objective**: Build high-performance async crawler for asset links, scripts, and forms.
- **Deliverables**: `backend/app/services/discovery/crawler.py` using `httpx` & `BeautifulSoup`.
- **Dependencies**: Era 2.
- **Completion Criteria**: Crawler recursively traverses web pages up to configurable depth limits.
- **Testing Requirements**: Unit tests with mock web targets.

### Phase 3.2: SPA Dynamic DOM Renderer (Playwright Integration)
- **Objective**: Integrate headless Chromium rendering for JavaScript-heavy single page applications.
- **Deliverables**: Playwright crawler module for DOM rendering and event triggers.
- **Dependencies**: Phase 3.1.
- **Completion Criteria**: Captures rendered DOM nodes, dynamic routes, and AJAX endpoints.
- **Testing Requirements**: SPA rendering test against sample React web app.

### Phase 3.3: Endpoint & REST/GraphQL API Discovery
- **Objective**: Extract API routes, URL parameters, headers, and GraphQL schemas from client scripts.
- **Deliverables**: Regex and AST API route parser module.
- **Dependencies**: Phase 3.2.
- **Completion Criteria**: Identifies hidden API endpoints and generates route parameter trees.
- **Testing Requirements**: Test route extraction against sample JS bundles.

### Phase 3.4: Technology Stack Fingerprinting Engine
- **Objective**: Detect web server, CMS, frontend framework, and backend library versions.
- **Deliverables**: Fingerprint engine leveraging Wappalyzer rules and header signatures.
- **Dependencies**: Phase 3.1.
- **Completion Criteria**: Accurately maps target technologies and known CVE versions.
- **Testing Requirements**: Verification against benchmark technology stacks.

### Phase 3.5: Asset Inventory & Attack Surface Mapper
- **Objective**: Store and organize target hosts, subdomains, endpoints, and components in DB.
- **Deliverables**: Target asset database models and attack surface mapping logic.
- **Dependencies**: Phase 3.4.
- **Completion Criteria**: Aggregates target assets into queryable surface tree.
- **Testing Requirements**: Target inventory integration tests.

---

## 🛡️ Era 4: Vulnerability Assessment Engine & Dynamic Testing

### Phase 4.1: Security Assessment Plugin Framework Core
- **Objective**: Implement dynamic plugin loading engine evaluating `plugin.yaml` manifests.
- **Deliverables**: `AssessmentPlugin` base class, plugin loader, test runner context.
- **Dependencies**: Era 3.
- **Completion Criteria**: Plugins load dynamically from directory and execute in isolation.
- **Testing Requirements**: Plugin loader unit tests.

### Phase 4.2: Security Headers & Server Misconfiguration Checks
- **Objective**: Detect missing or insecure CSP, HSTS, CORS, X-Frame-Options, and Server signatures.
- **Deliverables**: Headers assessment plugin module.
- **Dependencies**: Phase 4.1.
- **Completion Criteria**: Identifies header vulnerabilities and returns standardized findings.
- **Testing Requirements**: Test against vulnerable web server instances.

### Phase 4.3: OWASP Injection Assessment (SQLi & Commandi)
- **Objective**: Automated detection of error-based, time-based, and blind SQL injection flaws.
- **Deliverables**: SQLi assessment plugin (`plugin.yaml` + payload engine).
- **Dependencies**: Phase 4.1.
- **Completion Criteria**: Safely detects injection points without destroying database integrity.
- **Testing Requirements**: Verification against OWASP Juice Shop / DVWA injection endpoints.

### Phase 4.4: Cross-Site Scripting (XSS) Detection Plugin
- **Objective**: Reflection and DOM-based XSS vulnerability scanner.
- **Deliverables**: XSS assessment plugin module.
- **Dependencies**: Phase 4.1.
- **Completion Criteria**: Identifies unescaped user input reflections in HTML/JS context.
- **Testing Requirements**: Test against reflected and DOM XSS benchmarks.

### Phase 4.5: SSRF & Request Forgery Tester
- **Objective**: Server-Side Request Forgery testing using callback listeners (out-of-band detection).
- **Deliverables**: SSRF assessment plugin with callback interaction hook.
- **Dependencies**: Phase 4.1.
- **Completion Criteria**: Detects internal network access and out-of-band HTTP/DNS hits.
- **Testing Requirements**: Mock out-of-band listener test.

### Phase 4.6: Authentication, Session & JWT Analyzer
- **Objective**: Test for weak JWT algorithms, missing signature checks, expired sessions, and missing flags.
- **Deliverables**: Auth & JWT security assessment plugin.
- **Dependencies**: Phase 4.1.
- **Completion Criteria**: Flags unverified JWT signatures, weak secrets, and insecure session cookies.
- **Testing Requirements**: JWT weakness verification test suite.

### Phase 4.7: Broken Object Level Authorization (IDOR) Checker
- **Objective**: Test for unauthorized object reference manipulation across user session contexts.
- **Deliverables**: Dual-token IDOR assessment plugin.
- **Dependencies**: Phase 4.1.
- **Completion Criteria**: Detects resource access leakage when swapping user tokens.
- **Testing Requirements**: Dual-user session IDOR test suite.

### Phase 4.8: Rate Limiting & Sensitive Data Exposure Checks
- **Objective**: Inspect endpoint rate limits and detect exposed PII, API keys, and credentials in responses.
- **Deliverables**: Rate limit & data exposure assessment plugin.
- **Dependencies**: Phase 4.1.
- **Completion Criteria**: Identifies unthrottled login endpoints and leaked secrets in response body.
- **Testing Requirements**: Secret detection regex & throttling test suite.

---

## 🤖 Era 5: AI Security Analyst Engine & Vulnerability Intelligence

### Phase 5.1: LLM Integration Gateway & Provider Abstraction
- **Objective**: Build multi-provider LLM gateway supporting OpenAI, Anthropic, and local Ollama models.
- **Deliverables**: `backend/app/services/ai/gateway.py` with fallback and retry logic.
- **Dependencies**: Era 4.
- **Completion Criteria**: Sends prompts to configured LLM providers with automatic retry on failure.
- **Testing Requirements**: Provider mock unit tests.

### Phase 5.2: Vulnerability Context & Business Impact Explainer
- **Objective**: Prompt engineering pipeline to synthesize technical impact, business risk, and CVSS 4.0 vectors.
- **Deliverables**: AI vulnerability analysis service.
- **Dependencies**: Phase 5.1.
- **Completion Criteria**: Produces detailed vulnerability explanations personalized to target application domain.
- **Testing Requirements**: Test explanation quality against standard CVE dataset.

### Phase 5.3: Attack Path & Exploit Scenario Generator
- **Objective**: Generate realistic multi-step attack scenarios based on discovered vulnerability combinations.
- **Deliverables**: Attack path synthesizer module.
- **Dependencies**: Phase 5.2.
- **Completion Criteria**: Visualizes attack progression from initial access to data exfiltration.
- **Testing Requirements**: Verification of synthesized attack trees.

### Phase 5.4: Contextual Remediation & Secure Code Fix Engine
- **Objective**: Produce exact code patches and configuration snippets (Python, JS, Go, Java, Nginx).
- **Deliverables**: AI code remediation generator.
- **Dependencies**: Phase 5.2.
- **Completion Criteria**: Emits syntactically valid code patches addressing the root cause.
- **Testing Requirements**: Code generation validation tests.

### Phase 5.5: False-Positive Reduction & Noise Filtering Engine
- **Objective**: AI correlation engine analyzing response bodies, execution contexts, and target signatures.
- **Deliverables**: False-positive scoring module.
- **Dependencies**: Phase 5.2.
- **Completion Criteria**: Assigns confidence scores and filters scanner noise prior to ticketing.
- **Testing Requirements**: Verification against labeled false-positive benchmark datasets.

### Phase 5.6: Vector Database (pgvector) RAG Knowledge Base
- **Objective**: Index OWASP Cheat Sheets, CWE databases, and security advisories into pgvector.
- **Deliverables**: Vector store embedding pipeline & RAG retrieval service.
- **Dependencies**: Phase 5.1, Phase 1.6.
- **Completion Criteria**: Queries retrieve relevant security context to augment LLM prompts.
- **Testing Requirements**: RAG recall and similarity evaluation tests.

---

## ⚡ Era 6: Scanning Orchestration & Isolated Worker Sandbox

### Phase 6.1: Celery & Isolated Worker Sandbox Cluster
- **Objective**: Deploy unprivileged scanner worker containers with resource caps (1 vCPU, 512MB RAM) and egress filtering.
- **Deliverables**: `backend/app/tasks/scan_tasks.py`, Docker worker sandbox configuration.
- **Dependencies**: Era 4, Era 5.
- **Completion Criteria**: Workers execute tasks in isolated sandbox environments.
- **Testing Requirements**: Sandbox container boundary verification test.

### Phase 6.2: Target Scan Configuration & Authorized Assessment Contract
- **Objective**: Scan profile selection and mandatory "Authorized Security Assessment Confirmation" verification.
- **Deliverables**: Scan creation router with legal scope declaration validation.
- **Dependencies**: Phase 6.1.
- **Completion Criteria**: Scans reject execution if user confirmation declaration is missing.
- **Testing Requirements**: Legal authorization declaration validation tests.

### Phase 6.3: Scan Execution Lifecycle State Machine
- **Objective**: Implement state transitions (`QUEUED` -> `CRAWLING` -> `ASSESSING` -> `AI_ANALYSIS` -> `COMPLETED`).
- **Deliverables**: Scan lifecycle manager service and database status updater.
- **Dependencies**: Phase 6.2.
- **Completion Criteria**: Scan state advances reliably and handles failure/cancel hooks cleanly.
- **Testing Requirements**: Lifecycle state transition test suite.

### Phase 6.4: Real-time Scan Progress & WebSocket Stream
- **Objective**: WebSocket connection manager streaming live progress, target URLs, and finding alerts to client.
- **Deliverables**: `/api/v1/ws/scans/{scan_id}` WebSocket endpoint.
- **Dependencies**: Phase 6.3.
- **Completion Criteria**: Real-time event updates delivered to connected clients with <100ms latency.
- **Testing Requirements**: WebSocket streaming integration test.

### Phase 6.5: Scan Scheduling & Recurrence Engine
- **Objective**: Support automated recurring scans (daily, weekly, custom cron) via Celery Beat.
- **Deliverables**: Celery Beat schedule manager & scan scheduler APIs.
- **Dependencies**: Phase 6.3.
- **Completion Criteria**: Scheduled scans launch automatically according to configured cron expressions.
- **Testing Requirements**: Scheduler verification tests.

---

## 🖥️ Era 7: Enterprise Web Application, Dashboard & Trust Center

### Phase 7.1: UI Design System Tokens & Component Library Setup
- **Objective**: Implement Tailwind design tokens for Crimson/Obsidian color system and core UI components.
- **Deliverables**: `frontend/components/ui/` (buttons, cards, badges, dialogs, tables).
- **Dependencies**: Era 1, Era 6.
- **Completion Criteria**: UI components render with consistent light/dark theme styling.
- **Testing Requirements**: Component visual & accessibility tests.

### Phase 7.2: Public Marketing Pages & Enterprise Trust Center
- **Objective**: Build animated public pages including dedicated Trust Center (`/trust`).
- **Deliverables**: Public page routes in `frontend/app/(public)/trust/page.tsx`.
- **Dependencies**: Phase 7.1.
- **Completion Criteria**: Trust Center renders security practices grid, encryption details, and status widget.
- **Testing Requirements**: Next.js Lighthouse SEO & accessibility audits.

### Phase 7.3: Enterprise Dashboard Overview Interface
- **Objective**: Executive overview dashboard displaying risk scores, vulnerability distribution, and active scans.
- **Deliverables**: `frontend/app/(dashboard)/dashboard/page.tsx`, metrics widgets.
- **Dependencies**: Phase 7.1, Era 6.
- **Completion Criteria**: Displays real-time security posture metrics and high-priority alerts.
- **Testing Requirements**: Frontend integration tests with mock API data.

### Phase 7.4: Scan Management & Live Monitor Portal
- **Objective**: Interfaces to launch scans, confirm target authorization, view progress, and control execution.
- **Deliverables**: `frontend/app/(dashboard)/scans/` routes, live WebSocket progress bar.
- **Dependencies**: Phase 7.3, Phase 6.4.
- **Completion Criteria**: User can launch authorized scans and observe live vulnerability feeds.
- **Testing Requirements**: End-to-End Playwright scan control test.

### Phase 7.5: Vulnerability Triage & Evidence Record Viewer
- **Objective**: Vulnerability detail view displaying CVSS score, decoupled evidence dumps, and AI code fix.
- **Deliverables**: `frontend/app/(dashboard)/vulnerabilities/[id]/page.tsx`, evidence viewer drawer.
- **Dependencies**: Phase 7.4.
- **Completion Criteria**: Analysts can inspect raw HTTP dumps, screenshots, and AI remediation patches.
- **Testing Requirements**: Interactive UI state test for finding triage.

### Phase 7.6: User, Organization & Role Management UI
- **Objective**: Settings interface for managing team invitations, RBAC roles, MFA, and API keys.
- **Deliverables**: `frontend/app/(dashboard)/settings/` pages.
- **Dependencies**: Phase 7.3, Era 2.
- **Completion Criteria**: Admins can invite users, assign permissions, and revoke access keys.
- **Testing Requirements**: RBAC UI management tests.

---

## 📊 Era 8: Reporting, Executive Metrics & Export System

### Phase 8.1: PDF & HTML Executive Security Report Generator
- **Objective**: Build template engine generating downloadable CISO executive reports.
- **Deliverables**: `backend/app/services/reporting/pdf_generator.py` using Jinja2 & WeasyPrint.
- **Dependencies**: Era 7.
- **Completion Criteria**: Generates polished PDF executive reports with charts, summary metrics, and top risks.
- **Testing Requirements**: PDF layout and content generation test.

### Phase 8.2: Developer Technical Remediation Export (Markdown / CSV / JSON)
- **Objective**: Export raw findings and AI remediation patches in machine-readable formats.
- **Deliverables**: Export endpoints (`/api/v1/reports/export`).
- **Dependencies**: Phase 8.1.
- **Completion Criteria**: Downloads findings formatted in JSON, CSV, or Markdown.
- **Testing Requirements**: Export format schema validation tests.

### Phase 8.3: Compliance Framework Mapping (OWASP, PCI-DSS, ISO 27001)
- **Objective**: Map discovered vulnerabilities to compliance requirements and generate compliance checklists.
- **Deliverables**: Compliance mapping engine & report view.
- **Dependencies**: Phase 8.1.
- **Completion Criteria**: Reports display compliance score percentage against PCI-DSS and OWASP Top 10.
- **Testing Requirements**: Mapping accuracy tests against compliance standards.

---

## 🔗 Era 9: Enterprise Integration & Developer Workflows

### Phase 9.1: Jira & GitHub Issues Integration Plugin
- **Objective**: Bi-directional integration pushing triaged findings into Jira tickets or GitHub Issues.
- **Deliverables**: Jira/GitHub API integration module.
- **Dependencies**: Era 8.
- **Completion Criteria**: Creating a ticket in Vulnova opens an issue in target issue tracker.
- **Testing Requirements**: Mock integration API tests.

### Phase 9.2: Slack & Teams Security Alert Webhooks
- **Objective**: Real-time notification system dispatching alerts for Critical/High findings to chat channels.
- **Deliverables**: Webhook dispatcher service for Slack & Microsoft Teams.
- **Dependencies**: Phase 9.1.
- **Completion Criteria**: Critical finding alerts arrive formatted in configured Slack channels.
- **Testing Requirements**: Webhook payload validation tests.

### Phase 9.3: CI/CD Pipeline Scanning CLI Tool
- **Objective**: Standalone Python CLI / GitHub Action for triggering Vulnova scans from build pipelines.
- **Deliverables**: `vulnova-cli` package with fail-on-severity threshold options.
- **Dependencies**: Phase 9.1.
- **Completion Criteria**: Pipeline fails if critical vulnerabilities are discovered on target URL.
- **Testing Requirements**: CLI integration test suite.

---

## 🛡️ Era 10: Complete Security Validation Lifecycle & OWASP Verification

### Phase 10.1: OWASP Top 10 (2021) Security Validation Suite
- **Objective**: Automated security validation confirming Vulnova controls against OWASP Top 10 vulnerabilities.
- **Deliverables**: OWASP Top 10 verification suite.
- **Dependencies**: Era 9.
- **Completion Criteria**: 100% pass rate on OWASP Top 10 internal validation tests.
- **Testing Requirements**: Automated OWASP verification runner.

### Phase 10.2: OWASP API Security Top 10 (2023) Validation Suite
- **Objective**: Validation suite targeting BOLA, broken authentication, rate limiting, and API misconfigurations.
- **Deliverables**: API security validation test suite.
- **Dependencies**: Phase 10.1.
- **Completion Criteria**: 100% pass rate on API security controls.
- **Testing Requirements**: Automated API security test execution.

### Phase 10.3: OWASP ASVS v4.0 Level 2 Verification & Audit
- **Objective**: Comprehensive security audit against ASVS Level 2 security requirements across all endpoints.
- **Deliverables**: ASVS Level 2 audit report and remediation proof.
- **Dependencies**: Phase 10.2.
- **Completion Criteria**: Complete compliance with mandatory ASVS Level 2 items.
- **Testing Requirements**: ASVS audit test suite.

### Phase 10.4: Platform Penetration Testing & Exploit Verification
- **Objective**: Internal penetration test simulating external threat actors targeting API Gateway and Web UI.
- **Deliverables**: Penetration test execution report and remediations.
- **Dependencies**: Phase 10.3.
- **Completion Criteria**: Zero unhandled exploit vectors remaining on platform core.
- **Testing Requirements**: Pen test verification suite.

### Phase 10.5: Dependency Security Audit & SCA Enforcement
- **Objective**: Continuous Software Composition Analysis (SCA) blocking vulnerable third-party packages.
- **Deliverables**: `pip-audit` & `npm audit` automated enforcement.
- **Dependencies**: Phase 10.4.
- **Completion Criteria**: Zero Known Critical/High CVEs in application dependencies.
- **Testing Requirements**: Automated SCA pipeline check.

### Phase 10.6: Container Image Security Audit & Runtime Hardening
- **Objective**: Hardening Docker container images (Trivy scans, distroless bases, unprivileged execution).
- **Deliverables**: Hardened Dockerfiles and runtime container profiles.
- **Dependencies**: Phase 10.5.
- **Completion Criteria**: Zero High/Critical image vulnerabilities in Trivy scan.
- **Testing Requirements**: Container image scan audit.

### Phase 10.7: Secrets & Cryptographic Management Audit
- **Objective**: Verification of envelope encryption (AES-256-GCM), secret scanning (Gitleaks), and key rotation.
- **Deliverables**: Cryptographic security verification audit.
- **Dependencies**: Phase 10.6.
- **Completion Criteria**: Zero hardcoded secrets; AES-256-GCM verification pass.
- **Testing Requirements**: Secret audit script.

### Phase 10.8: Threat Model Review & STRIDE Verification
- **Objective**: Audit application against THREAT_MODEL.md STRIDE vectors and sandbox boundary protections.
- **Deliverables**: Updated threat model verification report.
- **Dependencies**: Phase 10.7.
- **Completion Criteria**: 100% of defined STRIDE mitigations verified in code.
- **Testing Requirements**: STRIDE verification matrix audit.

### Phase 10.9: Automated Security Regression Testing Framework
- **Objective**: Continuous security regression pipeline preventing reintroduction of fixed vulnerabilities.
- **Deliverables**: Security regression test suite in CI pipeline.
- **Dependencies**: Phase 10.8.
- **Completion Criteria**: Regression suite executes cleanly on all PRs.
- **Testing Requirements**: Security regression CI execution.

### Phase 10.10: Content Security Policy (CSP) & Header Hardening
- **Objective**: Enforce strict nonced CSP, HSTS preloading, CORS origin policies, and cookie flags.
- **Deliverables**: Hardened security middleware and HTTP response headers.
- **Dependencies**: Phase 10.9.
- **Completion Criteria**: Zero CSP evaluation errors; A+ rating on securityheaders.com.
- **Testing Requirements**: Automated header audit test.

### Phase 10.11: Multi-Factor Authentication (MFA / TOTP)
- **Objective**: Implement TOTP-based two-factor authentication for user logins.
- **Deliverables**: MFA setup, verification, and recovery code endpoints and UI.
- **Dependencies**: Phase 10.10.
- **Completion Criteria**: Users can enroll TOTP authenticators and are prompted during login.
- **Testing Requirements**: MFA flow integration test suite.

---

## ⚡ Era 11: Enterprise Scale, Performance Tuning & Reliability

### Phase 11.1: Database Query Optimization & Index Tuning
- **Objective**: Optimize PostgreSQL execution plans, add missing composite indexes, and setup connection pooling.
- **Deliverables**: PgBouncer configuration and optimized DB index migrations.
- **Dependencies**: Era 10.
- **Completion Criteria**: Database query response times stay below 20ms under high payload.
- **Testing Requirements**: PostgreSQL query load benchmarking.

### Phase 11.2: Redis Caching Strategy & Rate Limit Tuning
- **Objective**: Implement multi-layer caching for tenant lookups, static assets, and user sessions.
- **Deliverables**: Redis cache layer and distributed token bucket rate limiter.
- **Dependencies**: Phase 11.1.
- **Completion Criteria**: API Gateway handles 2000+ requests/sec with rate limiting protection.
- **Testing Requirements**: Locust load testing for API endpoints.

---

## 🚀 Era 12: Final Security Audit, Production Deployment & Release

### Phase 12.1: Final Static & Dynamic Security Penetration Audit
- **Objective**: Internal penetration test and automated SAST/DAST verification of Vulnova infrastructure.
- **Deliverables**: Remediation of all identified internal security findings.
- **Dependencies**: Era 11.
- **Completion Criteria**: Zero Critical or High severity vulnerabilities remaining in codebase.
- **Testing Requirements**: Full regression & vulnerability scan of platform.

### Phase 12.2: Production Docker Compose & Kubernetes Manifests
- **Objective**: Final production deployment configuration with TLS certificates, auto-scaling, and health monitors.
- **Deliverables**: Production `docker-compose.prod.yml` and Kubernetes Helm chart templates.
- **Dependencies**: Phase 12.1.
- **Completion Criteria**: Clean single-command production deployment with HTTPS enabled.
- **Testing Requirements**: Production deployment dry-run test.

### Phase 12.3: Final Documentation Review & Release Announcement (v1.0.0)
- **Objective**: Audit all documentation, finalize release notes, and tag v1.0.0 release.
- **Deliverables**: Tagged v1.0.0 release, updated CHANGELOG.md, verified production deployment.
- **Dependencies**: Phase 12.2.
- **Completion Criteria**: Vulnova platform fully deployed and available for enterprise use.
- **Testing Requirements**: Final production smoke test suite.
