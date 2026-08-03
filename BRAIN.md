# Vulnova — Permanent Project Memory & Architectural Brain (BRAIN.md)

> **Mandatory Protocol**: This document MUST be inspected before starting any technical phase or making architectural decisions. It serves as the single source of truth for engineering integrity, project vision, design axioms, decision rules, and historical progress.

---

## 👁️ 1. Project Vision & Core Mission

**Vulnova** is an enterprise-grade AI-powered Application Security (AppSec) Platform. It is engineered from first principles as a commercial-quality, multi-tenant security solution capable of operating at enterprise scale.

### Strategic Objectives:
1. **Continuous Application Security Posture**: Shift from periodic point-in-time scanning to continuous, event-driven attack surface discovery and assessment.
2. **AI Security Analyst Parity**: Replace manual triage friction with autonomous AI analysis capable of CVSS 4.0 evaluation, exploit synthesis, false-positive reduction, and language-specific code remediation.
3. **Zero Compromise Architecture**: Never treat security, performance, or modularity as an afterthought. Every layer adheres to strict Clean Architecture, sandbox worker isolation, and defense-in-depth principles.

---

## 🏛️ 2. Immutable Engineering Axioms

The following axioms govern all software design, implementation, and code reviews in Vulnova:

### Axiom 1: Engineering Integrity Over Speed
- A phase, milestone, or Era is completed **ONLY** when all planned functionality is implemented, tested, verified, and integrated without bypassing code checks.
- "Making the build green" by commenting out tests, suppressing linting errors without justification, or returning mock/dummy fallbacks in production paths is strictly prohibited.

### Axiom 2: Clean Architecture & Domain Isolation
- Core domain logic MUST NOT depend on external frameworks, databases, or UI components.
- Interfaces (ports) define boundaries; adapters implement them.
- Future migration from monolithic FastAPI modules to independent microservices must be achievable with zero modification to core domain business logic.

### Axiom 3: Security as a First-Class Citizen
- All inputs are untrusted until validated by strict Pydantic / Zod schemas.
- Scanner workers execute in unprivileged container sandboxes (`UID 10001`, `read_only_rootfs: true`, CPU/RAM limits, egress firewalling).
- Mandatory legal target ownership and authorization confirmation before any scan dispatch.
- Authentication (JWT + OAuth2 + MFA) and fine-grained Role-Based Access Control (RBAC) are enforced at every endpoint.

### Axiom 4: Extensible Plugin Framework
- All dynamic security checks are self-contained plugins governed by standard `plugin.yaml` manifests. New assessment checks must be addable without modifying core scanning engine code.

### Axiom 5: Event-Driven System Evolution
- State transitions dispatch structured domain events (`ScanCreatedEvent`, `FindingCreatedEvent`, `AIAnalysisCompletedEvent`) over abstract event bus interfaces compatible with RabbitMQ, Kafka, or NATS.

### Axiom 6: Visual Completion Tracking Rule
- Every completed phase in `ROADMAP.md` must be marked with a green check emoji `✅`. Progress is updated synchronously in `BRAIN.md` and `ROADMAP.md` upon phase verification.

### Axiom 7: GitHub Actions Verification Gate
Vulnova development follows a CI/CD verification-first workflow.

For every implementation phase after documentation foundation:
1. Complete the planned implementation.
2. Run local validation and testing.
3. Ensure appropriate GitHub Actions workflows exist for the technology being implemented.
4. Push changes to GitHub.
5. Wait for GitHub Actions execution to complete.
6. A phase cannot be marked completed unless the related GitHub Actions checks pass successfully.

A successful phase requires:
- Code implemented correctly.
- Tests passing.
- Security checks passing.
- GitHub Actions showing successful green checks.

Never mark a phase complete by only verifying local execution.

If GitHub Actions fails:
- Investigate the root cause.
- Fix the actual issue.
- Re-run validation.
- Push again.
- Wait for successful CI completion.

Do not bypass failures by:
- commenting out code,
- disabling tests,
- removing security checks,
- ignoring workflow failures.

After CI success:
- Update ROADMAP.md completion status with ✅.
- Update BRAIN.md project state if required.
- Continue to the next phase only after verification.

This workflow represents Vulnova's enterprise engineering lifecycle.

### Axiom 8: Canonical Repository Blueprint Rule
`PROJECT_STRUCTURE.md` is the canonical repository blueprint.
Every future directory or architectural expansion must be reflected in `PROJECT_STRUCTURE.md` before implementation.
No undocumented repository structure changes are permitted.

---

## 🏗️ 3. System Architecture & Tech Stack Rules

### Frontend Stack Standards
- **Framework**: Next.js 14 (App Router) with TypeScript (Strict Mode enabled).
- **Styling**: Vanilla CSS / TailwindCSS with custom design system tokens.
- **Design Tokens**:
  - **Light Theme**: Dominant Clean White (`#FFFFFF`, `#F8FAFC`), Accent Crimson Red (`#DC2626`, `#EF4444`).
  - **Dark Theme**: Obsidian Black (`#09090B`, `#18181B`), Crimson Red Glow (`#EF4444`, `#F87171`).
- **UI Components**: custom components built on `shadcn/ui` primitives, animated with `Framer Motion`.
- **Public Pages**: Includes Enterprise Trust Center (`/trust`) for security posture & compliance transparency.

### Backend Stack Standards
- **Runtime**: Python 3.12+ with `asyncio` loop for non-blocking I/O.
- **API Framework**: FastAPI with Pydantic v2 schemas and OpenAPI 3.1 generation.
- **Task Orchestration**: Celery workers backed by Redis for distributed DAST scanning & AI background workloads (event bus bridge ready).
- **Database Layer**: PostgreSQL 16+ utilizing `pgvector` for embedding similarity search, Alembic for migrations, scan profiles, vulnerability history, and decoupled evidence management.

---

## ───────────────
## 🚦 4. Era Progression & Roadmap State

| Era | Focus Area | Status | Target Completion |
| :--- | :--- | :---: | :--- |
| **Era 0** | Architecture & Enterprise Documentation Foundation | ✅ **COMPLETED** | Sprint 0 |
| **Era 0.5**| Enterprise Architecture Refinement & Security Model Polish | ✅ **COMPLETED** | Sprint 0.5 |
| **Era 1** | Infrastructure, Monorepo & DevSecOps Foundation | ✅ **COMPLETED** (Phases 1.1–1.7 ✅) | Sprint 1 |
| **Era 2** | Core Platform & Tenant Management System | ✅ **COMPLETED** (Phases 2.1–2.6 ✅) | Sprint 2 |
| **Era 3** | Discovery Engine & Asset Surface Mapping | ✅ **COMPLETED** (Phases 3.1–3.5 ✅) | Sprint 3 |
| **Era 4** | Vulnerability Assessment Engine & Dynamic Testing | 🟡 **IN PROGRESS** (Phase 4.1 ✅, Phase 4.2 ✅, Phase 4.3 ✅, Phase 4.4 ✅) | Sprint 4 |
| **Era 5** | AI Security Analyst Engine & Vulnerability Intelligence | ⏳ Pending | Sprint 5 |
| **Era 6** | Scanning Orchestration & Execution Pipeline | ⏳ Pending | Sprint 6 |
| **Era 7** | Enterprise Web Application & Dashboard Interface | ⏳ Pending | Sprint 7 |
| **Era 8** | Reporting, Executive Metrics & Export System | ⏳ Pending | Sprint 8 |
| **Era 9** | Enterprise Integration & Developer Workflows | ⏳ Pending | Sprint 9 |
| **Era 10**| Advanced Security Hardening & OWASP Compliance | ⏳ Pending | Sprint 10 |
| **Era 11**| Enterprise Scale, Performance Tuning & Reliability | ⏳ Pending | Sprint 11 |
| **Era 12**| Final Security Audit, Production Deployment & Release | ⏳ Pending | Sprint 12 |

---

## 📝 5. Technical Debt & Workaround Register

*No technical debt or workarounds registered. Era 0 & Era 0.5 clean foundation state.*

---

## 🔒 6. Security & Audit Logging Rules

1. **Security Event Logging**: Every authentication attempt, target authorization declaration, scan launch, report generation, and organization setting modification MUST produce a structured audit event.
2. **Secret Hygiene**: Secrets must NEVER be hardcoded. They are loaded at runtime from environment variables using Pydantic `BaseSettings`.

---

## 🔑 7. Authentication Architecture Decisions (Phase 2.2)

The following security decisions were finalized during Phase 2.2 and are now immutable:

1. **Password Hashing**: Argon2id via `passlib[argon2]` adapter. No bcrypt, no scrypt. Argon2id is the OWASP-recommended memory-hard KDF.
2. **JWT Access Tokens**: HS256 signing using `SECRET_KEY` from Pydantic Settings. 15-minute expiry. Claims: `sub`, `user_id`, `organization_id`, `role`, `token_type`, `exp`.
3. **Refresh Token Strategy**: Cryptographically random tokens (64 bytes, `secrets.token_urlsafe`). Stored as SHA-256 hashes in `refresh_tokens` table. 7-day expiry.
4. **Refresh Token Rotation**: Every refresh issues a new token and revokes the old one. Family-based tracking via `family_id` UUID.
5. **Reuse Detection**: If a previously-revoked refresh token is presented, the entire token family is revoked immediately (compromised session defense).
6. **HTTP-Only Cookies**: Refresh tokens are delivered in `vulnova_refresh_token` HTTP-Only, Secure, SameSite=Lax cookies. Never exposed to JavaScript.
7. **Email Validation**: `email-validator>=2.1.0` is a production dependency. Pydantic `EmailStr` requires it at import time. This was identified as a CI-breaking omission and resolved in commit `f9af674`.
8. **Auth Endpoints**: `/api/v1/auth/register`, `/login`, `/refresh`, `/logout`, `/me` — all under OAuth2PasswordBearer FastAPI dependency injection.

---

## 🛡️ 8. Multi-Tenant RBAC & Tenant Isolation Decisions (Phase 2.3)

The following authorization rules were finalized during Phase 2.3 and are now immutable:

1. **Role Hierarchy**: Strict integer-ordered `Role(IntEnum)` hierarchy (`OWNER = 40 > ADMIN = 30 > SECURITY_ANALYST = 20 > VIEWER = 10`). Higher roles implicitly inherit all permissions of lower roles.
2. **Database Schema Compatibility**: Operates directly on the existing `users.role` `VARCHAR(50)` column without database migrations. String labels map bi-directionally to `Role` enum values via `parse_role()`.
3. **Fail-Closed Safe Fallback**: Unrecognized or corrupt role strings default safely to `Role.VIEWER` without escalating privilege or throwing uncaught internal server errors.
4. **Centralized Permission Map**: Permissions follow `resource:action` syntax (`"scans:create"`, `"organization:delete"`, `"users:read"`). Mapped centrally in `PERMISSION_MAP` to minimum required roles. Avoids ad-hoc scattered `if user.role == ...` conditionals.
5. **FastAPI Dependency Injectors**: `require_role(minimum_role)` and `require_permission("resource:action")` run strictly after `get_current_user` authentication. Unmet requirements raise `ForbiddenException` (HTTP 403) with `FORBIDDEN` code.
6. **Tenant Isolation Enforcement**: `verify_organization_access(user, target_org_id)` and `require_same_organization` enforce organization boundary checks. Never trusts request payload `organization_id` alone; compares against authenticated `user.organization_id`. Cross-org access raises `ForbiddenException` (HTTP 403).

---

## 🔐 9. API Key Management Architecture Decisions (Phase 2.4)

The following API key management decisions were finalized during Phase 2.4 and are now immutable:

1. **Key Format**: `vn_live_` prefix (8 characters) + 32-byte URL-safe cryptographic secret via `secrets.token_urlsafe(32)`. Prefix enables visual identification without exposing the secret.
2. **Storage Security**: Raw API keys are NEVER stored in the database. Only `key_prefix` (for lookup) and `key_hash` (SHA-256 hex digest) are persisted. The raw key is returned exactly once during creation and is unrecoverable thereafter.
3. **Verification**: Constant-time comparison via `hmac.compare_digest()` to prevent timing side-channel attacks during key authentication.
4. **Authentication Flow**: Prefix-based lookup (`key_prefix` index) → SHA-256 hash computation → constant-time hash comparison → expiry validation → `last_used_at` timestamp update.
5. **Dual-Mode Authentication**: `get_current_user_or_api_key` dependency supports both JWT Bearer and X-API-Key authentication. Priority order: (1) Bearer JWT, (2) X-API-Key fallback. If both headers are present, JWT is preferred and the choice is logged.
6. **Scope Management**: API keys carry `scopes` (JSON array, default `["read", "write"]`). Scope validation is checked during authentication against the requested operation.
7. **Expiry & Revocation**: Optional `expires_in_days` (1–365 days) sets `expires_at` timestamp. Expired keys are rejected during authentication. Revocation uses `DELETE ... RETURNING` for type-safe SQLAlchemy 2.0 compatibility with tenant isolation enforcement.
8. **RBAC Integration**: All API key endpoints (`create`, `list`, `revoke`) are protected by `require_permission()` guards (`api_keys:create`, `api_keys:read`, `api_keys:revoke`).
9. **Type Safety**: `types-passlib` stubs are a dev dependency. Mypy strict mode enforced without `type: ignore` suppressions. `Callable[..., Any]` used for FastAPI dependency factories. `typing.Annotated` used for FastAPI Header parameter injection.

---

## 👥 10. User & Organization Management Architecture Decisions (Phase 2.5)

The following user and organization management decisions were finalized during Phase 2.5 and are now immutable:

1. **Clean Architecture Isolation**: User and organization domain entities (`UserModel`, `OrganizationModel`) are managed through isolated application services (`UserService`, `OrganizationService`) and repositories (`UserRepository`, `OrganizationRepository`).
2. **Sole Owner Protection**: An organization MUST always maintain at least one active `OWNER`. Operations attempting to demote, deactivate, or remove the sole active `OWNER` of an organization raise a `ValidationException` (HTTP 422).
3. **Self-Action Safeguards**: Users are prohibited from deactivating or removing their own account via administrative management endpoints (`/api/v1/users/{user_id}/status`, `/api/v1/users/{user_id}`).
4. **Role Assignment Hierarchy**: Only `OWNER` users can update a team member's role (`users:update_role`). Non-owner callers attempting to assign the `OWNER` role during user invitation raise `ForbiddenException` (HTTP 403).
5. **Tenant Boundary Enforcement**: `UserRepository` and `OrganizationRepository` enforce strict tenant isolation via `get_by_id_and_org()` and `list_by_organization()`. All endpoints filter and restrict mutations strictly to `current_user.organization_id`.
6. **Exception Hierarchy Extension**: Added `ConflictException` (HTTP 409 `RESOURCE_CONFLICT`) to `app/core/exceptions.py` for handling duplicate resource creation attempts (e.g. duplicate email addresses).
7. **Type-Safe Database Mutations**: All record deletions leverage SQLAlchemy 2.0 `DELETE ... RETURNING` pattern instead of untyped `rowcount` attributes to maintain Mypy strict mode compliance.

---

## 📜 11. Security Audit Logging System Architecture Decisions (Phase 2.6)

The following security audit logging decisions were finalized during Phase 2.6 and are now immutable:

1. **Immutable Audit Trail**: Audit events are strictly append-only. No UPDATE or DELETE endpoints exist for `audit_logs` records.
2. **Centralized Service Recording**: All security operations across Auth, User, Org, and API Key services invoke `AuditLogService.record_event()` with structured event names (`auth.login_success`, `auth.login_failed`, `user.created`, `user.role_updated`, `organization.updated`, `api_key.revoked`).
3. **Fail-Safe Logging Design**: Errors inside `record_event()` log high-priority `structlog` warnings rather than crashing primary user-facing transactions.
4. **Tenant Boundary Enforcement**: `AuditLogRepository` and `/api/v1/audit-logs` endpoints strictly enforce `organization_id` boundary checks. Admins can only view audit logs for their own organization.
5. **Client Context Extraction**: `get_client_info` dependency extracts `client_ip` (supporting `X-Forwarded-For` proxy headers) and `user_agent` headers for forensic attribution.
6. **Zero Secret Storage**: Audit event `details` JSON payload is strictly sanitized. Passwords, token secrets, and raw API keys are NEVER stored in audit logs.
7. **RBAC Guarding**: Audit log retrieval APIs require `audit_logs:read` permission (minimum `ADMIN` role).

---

## 🔍 12. Discovery Engine & Asset Surface Mapping Decisions (Phase 3.1)

The following discovery engine architecture decisions were finalized during Phase 3.1 and are now immutable:

1. **SSRF & Egress Firewalling**: Every crawl target URL and resolved IP address is pre-validated by `ssrf_validator.py`. Only `http` and `https` schemes are permitted. Loopback (`127.0.0.0/8`, `::1`), AWS Metadata (`169.254.169.254`), RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and `0.0.0.0` IP addresses are strictly blocked, raising `ValidationException` (HTTP 422).
2. **Domain Scope Boundary Enforcement**: Crawling is strictly restricted to the target base domain scope (`is_url_in_scope()`). Outbound off-site links are ignored unless `allow_subdomains` is explicitly enabled by an authorized caller.
3. **Safety Caps & Timeout Handling**: Response body reading is capped at `MAX_BODY_BYTES = 5 MB` to prevent memory exhaustion / zip-bomb attacks. Redirects are capped at `MAX_REDIRECTS = 5`. Request timeouts are set to `10.0` seconds.
4. **Non-Blocking Concurrency**: Crawling uses `httpx.AsyncClient` with `asyncio.Semaphore(concurrency_limit)` (1–20) to ensure non-blocking concurrent request execution.
5. **Extensible Domain Asset Architecture**: Domain entities in `app/domain/entities/discovery.py` (`AssetType`, `DiscoveredAsset`, `DiscoveredURL`, `DiscoveredForm`, `DiscoveredScript`, `CrawlResult`) are designed as extensible base structures for future phases (subdomains, tech fingerprinting, API schemas).
6. **Audit Traceability**: Every crawl request logs structured audit events (`discovery.crawl_started`, `discovery.crawl_completed`, or `discovery.crawl_rejected`) capturing actor user ID, organization ID, target domain, page count, duration, and rejection reason.
7. **RBAC & Authorization**: `/api/v1/discovery/crawl` requires authentication (Bearer JWT or X-API-Key), valid organization context, and `targets:create` RBAC permission.
8. **Lazy Playwright Import**: `playwright.async_api` is imported lazily inside `SPADynamicCrawler.crawl()`. Zero top-level Playwright imports exist in the module layer, ensuring API server startup never crashes if Playwright is uninstalled.
9. **Graceful Static Fallback**: If Playwright package or Chromium binaries are missing (`PlaywrightUnavailableException`), `DiscoveryService` logs a warning (`discovery.playwright_unavailable_falling_back_to_static`) and executes `AsyncWebCrawler` (Phase 3.1).
10. **Background AJAX/Fetch Interception**: `SPADynamicCrawler` listens to `page.on("request", ...)` events to capture dynamic `fetch` and `XHR` calls, running SSRF checks (`is_safe_target_url`) on every intercepted endpoint.
11. **Enterprise IP Classification**: Rather than over-blocking and discarding internal IP findings, `classify_ip()` annotates IP addresses with `classification` (`PUBLIC`, `PRIVATE`, `LOOPBACK`, `LINK_LOCAL`, `RESERVED`), `is_internal`, and `is_egress_safe`. Enterprise ASM retains internal assets (e.g. `dev.company.local` -> `10.10.5.20`) for attack surface visibility while preventing SSRF during active HTTP scanning.
12. **Non-Blocking Async DNS Resolution**: `AsyncDNSResolver` uses `dnspython` to asynchronously query `A`, `AAAA`, `CNAME`, `MX`, `NS`, and `TXT` records in parallel across discovered subdomains.
13. **Passive Certificate Transparency Discovery**: `CTLogsClient` queries Certificate Transparency logs (`crt.sh`) via `httpx.AsyncClient` to discover active subdomains matching the target domain scope.
14. **Modular Technology Fingerprinting**: `TechFingerprinter` combines HTTP header signature parsing (Nginx, Apache, Express, PHP, Cloudflare), HTML meta generator tags (WordPress, Drupal), DOM structure markers (`__next`, `__nuxt`, `ng-version`, `data-reactroot`), and script paths (`react`, `vue`, `jquery`, `bootstrap`) into structured `DetectedTechnology` domain entities with version extraction and confidence scores.
15. **Security Header Compliance Auditing**: Automatically evaluates presence and configuration of `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy` headers during technology scans.
16. **Persistent Multi-Tenant Asset Graph**: `AssetNodeModel` (`asset_nodes`) and `AssetRelationshipModel` (`asset_relationships`) tables model asset nodes (`TARGET_DOMAIN`, `SUBDOMAIN`, `IP_ADDRESS`, `URL_ENDPOINT`, `FORM`, `SCRIPT`, `TECHNOLOGY`) and edge relationships (`BELONGS_TO`, `RESOLVES_TO`, `RUNS_TECH`, `HAS_ENDPOINT`, `DISCOVERED_FROM`).
17. **Automated Asset Graph Correlation**: `AssetGraphService.build_asset_graph` correlates crawling, DNS resolution, and technology stack fingerprints into a persistent, queryable graph topology with strict multi-tenant boundary checks.

---

## 13. Vulnerability Assessment Engine & Dynamic Testing Decisions

1. **Decoupled Abstract Plugin Interface**: `BaseAssessmentPlugin` (ABC in `app/domain/entities/assessment.py`) defines a strict, generic plugin contract. Every security plugin declares metadata (`id`, `name`, `version`, `supported_asset_types`, `required_permissions`) and implements `async execute(ctx: AssessmentContext) -> List[Finding]`.
2. **Generic Orchestration Architecture**: `AssessmentService` contains zero hardcoded scanner or vulnerability logic. It delegates plugin execution to `PluginRegistry`, receiving standardized `Finding` domain objects for database persistence.
4. **Safe Non-Destructive SQL Injection Probing**: `SQLInjectionPlugin` tests query parameters using safe SQL syntax markers (`'`, `''`, `' OR '1'='1`) and regex error pattern matching across 5 major database engines (PostgreSQL, MySQL, SQLite, Oracle, MSSQL) without performing destructive data modifications.
5. **Marker-Based Reflected XSS Detection**: `XSSPlugin` injects unique, non-executing marker tags (`"><vlnv_xss_probe_<uuid>>`) to confirm unescaped HTML reflection in HTTP responses without executing malicious scripts.
6. **Authentication & Session Flag Auditing**: `AuthSecurityPlugin` analyzes Set-Cookie directives for missing `HttpOnly`, `Secure`, or `SameSite` flags and flags unencrypted HTTP credential transmission.
7. **Exposed API Documentation Probing**: `APISecurityPlugin` probes target assets for exposed Swagger/OpenAPI/GraphQL documentation or schema endpoints (`/swagger`, `/swagger-ui`, `/openapi.json`, `/api-docs`, `/graphql`) and alerts on information disclosure risks.
8. **JWT Signature & Claims Analysis**: `JWTSecurityPlugin` inspects JSON Web Tokens for critical signing risks (`alg: none`), missing `exp` claims, excessive lifetime (> 24h), and missing `iss`/`aud` claims without requiring server secret keys.
9. **CORS Misconfiguration Detection**: `CORSPlugin` evaluates `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials` headers via custom `Origin` probes to flag wildcard origin credentials and arbitrary origin reflection.
10. **Non-Blocking Administrative Port Probing**: `NetworkServicePlugin` asynchronously checks for exposed high-risk administrative and database ports (SSH 22, RDP 3389, MySQL 3306, PostgreSQL 5432, MongoDB 27017, Redis 6379, Elasticsearch 9200) without stalling execution.
11. **TLS Certificate & Protocol Inspection**: `TLSSecurityPlugin` inspects SSL socket connections to audit certificate expiration, trust store verification, and deprecated protocol versions (TLS 1.0/1.1).
12. **Cloud Bucket & IMDS Exposure Auditing**: `CloudSecurityPlugin` detects public cloud storage bucket listing permissions (AWS S3, Azure Blob, GCP) and flags references to Cloud Metadata Service (169.254.169.254).
13. **Enterprise Platform Architectural Shift**: Vulnova has transitioned from a vulnerability plugin execution framework into an Enterprise Application Security Intelligence Platform. Future development prioritizes normalization, correlation, evidence, continuous monitoring, and AI-driven analysis over isolated vulnerability checks.
14. **Multi-Modal Evidence Capture & Proof Pipeline**: `EvidenceCollectionEngine` captures reproducible proof (masked HTTP request/response text dumps, header/cookie profiles, Playwright DOM snapshots, visual PNG screenshots) after finding normalization. Evidence artifacts are integrity-verified via SHA-256 checksums and saved to tenant-isolated storage paths (`EvidenceArtifactStorage`).
15. **Enterprise Scan Profile & Execution Policy Architecture**: Vulnova assessments are no longer directly plugin-triggered. The pipeline operates via profile resolution and policy validation:
    ```
    User Request ──► Scan Profile Resolution ──► Policy Validation ──► Plugin Execution ──► Risk Intelligence ──► Finding Deduplication ──► Evidence Collection ──► Assessment Storage
    ```
    - `ScanProfileRegistry` references `PluginRegistry` IDs only and does not duplicate plugin metadata or implementation logic.
    - `PluginRegistry` remains the single source of truth for plugin availability and capability verification.
    - `ScanPolicyEngine` is a stateless helper class independent of FastAPI/HTTP layers, ensuring full compatibility for reuse inside future Era 6 distributed Celery worker sandboxes.
16. **Multi-Source Finding Correlation & Asset Inventory Architecture**: Findings are no longer isolated scanner records. `AssessmentCorrelationEngine` maps normalized findings to Asset Graph nodes (`AssetNode`) and aggregates posture metrics:
    - `asset_node_id` remains an optional field (`Optional[UUID]`) on findings to preserve full backward compatibility with legacy scan data.
    - Findings are NOT duplicated as graph nodes; they remain stored in `security_findings` while linked via `asset_node_id` to prevent graph node explosion.
    - Asset posture risk scores reuse `RiskIntelligenceEngine` composite scores (`composite_risk_score`) rather than inventing secondary risk engines.
    - Every asset inventory query enforces mandatory `organization_id` filtering for strict multi-tenant boundary security.
17. **Attack Surface Posture Snapshotting & Continuous Monitoring Architecture**: Vulnova posture snapshots and change detection events:
    - `AssetSnapshotModel` (`asset_snapshots` table) records point-in-time posture aggregates (`total_assets`, `total_findings`, `critical_findings`, `high_findings`, `avg_risk_score`, `max_risk_score`) per organization assessment run.
    - Every posture snapshot is organization isolated (`organization_id`), assessment linked (`assessment_job_id`), and timestamped (`created_at`) to build immutable security audit history.
    - Risk score trajectory metrics reuse `RiskIntelligenceEngine` composite scores (`f.risk.composite_risk_score`) directly; zero secondary risk calculators are introduced.
    - `ChangeDetectionEngine` identifies vulnerability lifecycle state transitions (`FINDING_NEW`, `FINDING_RESOLVED`, `FINDING_REOPENED`) and records discrete audit timeline events in `AssetChangeEventModel` (`asset_change_events`).
18. **Enterprise Finding Triage & Automated Suppression Architecture**: Vulnova vulnerability lifecycle management and automated false-positive suppression:
- Update BRAIN.md project state if required.
- Continue to the next phase only after verification.

This workflow represents Vulnova's enterprise engineering lifecycle.

### Axiom 8: Canonical Repository Blueprint Rule
`PROJECT_STRUCTURE.md` is the canonical repository blueprint.
Every future directory or architectural expansion must be reflected in `PROJECT_STRUCTURE.md` before implementation.
No undocumented repository structure changes are permitted.

---

## 🏗️ 3. System Architecture & Tech Stack Rules

### Frontend Stack Standards
- **Framework**: Next.js 14 (App Router) with TypeScript (Strict Mode enabled).
- **Styling**: Vanilla CSS / TailwindCSS with custom design system tokens.
- **Design Tokens**:
  - **Light Theme**: Dominant Clean White (`#FFFFFF`, `#F8FAFC`), Accent Crimson Red (`#DC2626`, `#EF4444`).
  - **Dark Theme**: Obsidian Black (`#09090B`, `#18181B`), Crimson Red Glow (`#EF4444`, `#F87171`).
- **UI Components**: custom components built on `shadcn/ui` primitives, animated with `Framer Motion`.
- **Public Pages**: Includes Enterprise Trust Center (`/trust`) for security posture & compliance transparency.

### Backend Stack Standards
- **Runtime**: Python 3.12+ with `asyncio` loop for non-blocking I/O.
- **API Framework**: FastAPI with Pydantic v2 schemas and OpenAPI 3.1 generation.
- **Task Orchestration**: Celery workers backed by Redis for distributed DAST scanning & AI background workloads (event bus bridge ready).
- **Database Layer**: PostgreSQL 16+ utilizing `pgvector` for embedding similarity search, Alembic for migrations, scan profiles, vulnerability history, and decoupled evidence management.

---

## ───────────────
## 🚦 4. Era Progression & Roadmap State

| Era | Focus Area | Status | Target Completion |
| :--- | :--- | :---: | :--- |
| **Era 0** | Architecture & Enterprise Documentation Foundation | ✅ **COMPLETED** | Sprint 0 |
| **Era 0.5**| Enterprise Architecture Refinement & Security Model Polish | ✅ **COMPLETED** | Sprint 0.5 |
| **Era 1** | Infrastructure, Monorepo & DevSecOps Foundation | ✅ **COMPLETED** (Phases 1.1–1.7 ✅) | Sprint 1 |
| **Era 2** | Core Platform & Tenant Management System | ✅ **COMPLETED** (Phases 2.1–2.6 ✅) | Sprint 2 |
| **Era 3** | Discovery Engine & Asset Surface Mapping | ✅ **COMPLETED** (Phases 3.1–3.5 ✅) | Sprint 3 |
| **Era 4** | Vulnerability Assessment Engine & Dynamic Testing | 🟡 **IN PROGRESS** (Phase 4.1 ✅, Phase 4.2 ✅, Phase 4.3 ✅, Phase 4.4 ✅) | Sprint 4 |
| **Era 5** | AI Security Analyst Engine & Vulnerability Intelligence | ⏳ Pending | Sprint 5 |
| **Era 6** | Scanning Orchestration & Execution Pipeline | ⏳ Pending | Sprint 6 |
| **Era 7** | Enterprise Web Application & Dashboard Interface | ⏳ Pending | Sprint 7 |
| **Era 8** | Reporting, Executive Metrics & Export System | ⏳ Pending | Sprint 8 |
| **Era 9** | Enterprise Integration & Developer Workflows | ⏳ Pending | Sprint 9 |
| **Era 10**| Advanced Security Hardening & OWASP Compliance | ⏳ Pending | Sprint 10 |
| **Era 11**| Enterprise Scale, Performance Tuning & Reliability | ⏳ Pending | Sprint 11 |
| **Era 12**| Final Security Audit, Production Deployment & Release | ⏳ Pending | Sprint 12 |

---

## 📝 5. Technical Debt & Workaround Register

*No technical debt or workarounds registered. Era 0 & Era 0.5 clean foundation state.*

---

## 🔒 6. Security & Audit Logging Rules

1. **Security Event Logging**: Every authentication attempt, target authorization declaration, scan launch, report generation, and organization setting modification MUST produce a structured audit event.
2. **Secret Hygiene**: Secrets must NEVER be hardcoded. They are loaded at runtime from environment variables using Pydantic `BaseSettings`.

---

## 🔑 7. Authentication Architecture Decisions (Phase 2.2)

The following security decisions were finalized during Phase 2.2 and are now immutable:

1. **Password Hashing**: Argon2id via `passlib[argon2]` adapter. No bcrypt, no scrypt. Argon2id is the OWASP-recommended memory-hard KDF.
2. **JWT Access Tokens**: HS256 signing using `SECRET_KEY` from Pydantic Settings. 15-minute expiry. Claims: `sub`, `user_id`, `organization_id`, `role`, `token_type`, `exp`.
3. **Refresh Token Strategy**: Cryptographically random tokens (64 bytes, `secrets.token_urlsafe`). Stored as SHA-256 hashes in `refresh_tokens` table. 7-day expiry.
4. **Refresh Token Rotation**: Every refresh issues a new token and revokes the old one. Family-based tracking via `family_id` UUID.
5. **Reuse Detection**: If a previously-revoked refresh token is presented, the entire token family is revoked immediately (compromised session defense).
6. **HTTP-Only Cookies**: Refresh tokens are delivered in `vulnova_refresh_token` HTTP-Only, Secure, SameSite=Lax cookies. Never exposed to JavaScript.
7. **Email Validation**: `email-validator>=2.1.0` is a production dependency. Pydantic `EmailStr` requires it at import time. This was identified as a CI-breaking omission and resolved in commit `f9af674`.
8. **Auth Endpoints**: `/api/v1/auth/register`, `/login`, `/refresh`, `/logout`, `/me` — all under OAuth2PasswordBearer FastAPI dependency injection.

---

## 🛡️ 8. Multi-Tenant RBAC & Tenant Isolation Decisions (Phase 2.3)

The following authorization rules were finalized during Phase 2.3 and are now immutable:

1. **Role Hierarchy**: Strict integer-ordered `Role(IntEnum)` hierarchy (`OWNER = 40 > ADMIN = 30 > SECURITY_ANALYST = 20 > VIEWER = 10`). Higher roles implicitly inherit all permissions of lower roles.
2. **Database Schema Compatibility**: Operates directly on the existing `users.role` `VARCHAR(50)` column without database migrations. String labels map bi-directionally to `Role` enum values via `parse_role()`.
3. **Fail-Closed Safe Fallback**: Unrecognized or corrupt role strings default safely to `Role.VIEWER` without escalating privilege or throwing uncaught internal server errors.
4. **Centralized Permission Map**: Permissions follow `resource:action` syntax (`"scans:create"`, `"organization:delete"`, `"users:read"`). Mapped centrally in `PERMISSION_MAP` to minimum required roles. Avoids ad-hoc scattered `if user.role == ...` conditionals.
5. **FastAPI Dependency Injectors**: `require_role(minimum_role)` and `require_permission("resource:action")` run strictly after `get_current_user` authentication. Unmet requirements raise `ForbiddenException` (HTTP 403) with `FORBIDDEN` code.
6. **Tenant Isolation Enforcement**: `verify_organization_access(user, target_org_id)` and `require_same_organization` enforce organization boundary checks. Never trusts request payload `organization_id` alone; compares against authenticated `user.organization_id`. Cross-org access raises `ForbiddenException` (HTTP 403).

---

## 🔐 9. API Key Management Architecture Decisions (Phase 2.4)

The following API key management decisions were finalized during Phase 2.4 and are now immutable:

1. **Key Format**: `vn_live_` prefix (8 characters) + 32-byte URL-safe cryptographic secret via `secrets.token_urlsafe(32)`. Prefix enables visual identification without exposing the secret.
2. **Storage Security**: Raw API keys are NEVER stored in the database. Only `key_prefix` (for lookup) and `key_hash` (SHA-256 hex digest) are persisted. The raw key is returned exactly once during creation and is unrecoverable thereafter.
3. **Verification**: Constant-time comparison via `hmac.compare_digest()` to prevent timing side-channel attacks during key authentication.
4. **Authentication Flow**: Prefix-based lookup (`key_prefix` index) → SHA-256 hash computation → constant-time hash comparison → expiry validation → `last_used_at` timestamp update.
5. **Dual-Mode Authentication**: `get_current_user_or_api_key` dependency supports both JWT Bearer and X-API-Key authentication. Priority order: (1) Bearer JWT, (2) X-API-Key fallback. If both headers are present, JWT is preferred and the choice is logged.
6. **Scope Management**: API keys carry `scopes` (JSON array, default `["read", "write"]`). Scope validation is checked during authentication against the requested operation.
7. **Expiry & Revocation**: Optional `expires_in_days` (1–365 days) sets `expires_at` timestamp. Expired keys are rejected during authentication. Revocation uses `DELETE ... RETURNING` for type-safe SQLAlchemy 2.0 compatibility with tenant isolation enforcement.
8. **RBAC Integration**: All API key endpoints (`create`, `list`, `revoke`) are protected by `require_permission()` guards (`api_keys:create`, `api_keys:read`, `api_keys:revoke`).
9. **Type Safety**: `types-passlib` stubs are a dev dependency. Mypy strict mode enforced without `type: ignore` suppressions. `Callable[..., Any]` used for FastAPI dependency factories. `typing.Annotated` used for FastAPI Header parameter injection.

---

## 👥 10. User & Organization Management Architecture Decisions (Phase 2.5)

The following user and organization management decisions were finalized during Phase 2.5 and are now immutable:

1. **Clean Architecture Isolation**: User and organization domain entities (`UserModel`, `OrganizationModel`) are managed through isolated application services (`UserService`, `OrganizationService`) and repositories (`UserRepository`, `OrganizationRepository`).
2. **Sole Owner Protection**: An organization MUST always maintain at least one active `OWNER`. Operations attempting to demote, deactivate, or remove the sole active `OWNER` of an organization raise a `ValidationException` (HTTP 422).
3. **Self-Action Safeguards**: Users are prohibited from deactivating or removing their own account via administrative management endpoints (`/api/v1/users/{user_id}/status`, `/api/v1/users/{user_id}`).
4. **Role Assignment Hierarchy**: Only `OWNER` users can update a team member's role (`users:update_role`). Non-owner callers attempting to assign the `OWNER` role during user invitation raise `ForbiddenException` (HTTP 403).
5. **Tenant Boundary Enforcement**: `UserRepository` and `OrganizationRepository` enforce strict tenant isolation via `get_by_id_and_org()` and `list_by_organization()`. All endpoints filter and restrict mutations strictly to `current_user.organization_id`.
6. **Exception Hierarchy Extension**: Added `ConflictException` (HTTP 409 `RESOURCE_CONFLICT`) to `app/core/exceptions.py` for handling duplicate resource creation attempts (e.g. duplicate email addresses).
7. **Type-Safe Database Mutations**: All record deletions leverage SQLAlchemy 2.0 `DELETE ... RETURNING` pattern instead of untyped `rowcount` attributes to maintain Mypy strict mode compliance.

---

## 📜 11. Security Audit Logging System Architecture Decisions (Phase 2.6)

The following security audit logging decisions were finalized during Phase 2.6 and are now immutable:

1. **Immutable Audit Trail**: Audit events are strictly append-only. No UPDATE or DELETE endpoints exist for `audit_logs` records.
2. **Centralized Service Recording**: All security operations across Auth, User, Org, and API Key services invoke `AuditLogService.record_event()` with structured event names (`auth.login_success`, `auth.login_failed`, `user.created`, `user.role_updated`, `organization.updated`, `api_key.revoked`).
3. **Fail-Safe Logging Design**: Errors inside `record_event()` log high-priority `structlog` warnings rather than crashing primary user-facing transactions.
4. **Tenant Boundary Enforcement**: `AuditLogRepository` and `/api/v1/audit-logs` endpoints strictly enforce `organization_id` boundary checks. Admins can only view audit logs for their own organization.
5. **Client Context Extraction**: `get_client_info` dependency extracts `client_ip` (supporting `X-Forwarded-For` proxy headers) and `user_agent` headers for forensic attribution.
6. **Zero Secret Storage**: Audit event `details` JSON payload is strictly sanitized. Passwords, token secrets, and raw API keys are NEVER stored in audit logs.
7. **RBAC Guarding**: Audit log retrieval APIs require `audit_logs:read` permission (minimum `ADMIN` role).

---

## 🔍 12. Discovery Engine & Asset Surface Mapping Decisions (Phase 3.1)

The following discovery engine architecture decisions were finalized during Phase 3.1 and are now immutable:

1. **SSRF & Egress Firewalling**: Every crawl target URL and resolved IP address is pre-validated by `ssrf_validator.py`. Only `http` and `https` schemes are permitted. Loopback (`127.0.0.0/8`, `::1`), AWS Metadata (`169.254.169.254`), RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and `0.0.0.0` IP addresses are strictly blocked, raising `ValidationException` (HTTP 422).
2. **Domain Scope Boundary Enforcement**: Crawling is strictly restricted to the target base domain scope (`is_url_in_scope()`). Outbound off-site links are ignored unless `allow_subdomains` is explicitly enabled by an authorized caller.
3. **Safety Caps & Timeout Handling**: Response body reading is capped at `MAX_BODY_BYTES = 5 MB` to prevent memory exhaustion / zip-bomb attacks. Redirects are capped at `MAX_REDIRECTS = 5`. Request timeouts are set to `10.0` seconds.
4. **Non-Blocking Concurrency**: Crawling uses `httpx.AsyncClient` with `asyncio.Semaphore(concurrency_limit)` (1–20) to ensure non-blocking concurrent request execution.
5. **Extensible Domain Asset Architecture**: Domain entities in `app/domain/entities/discovery.py` (`AssetType`, `DiscoveredAsset`, `DiscoveredURL`, `DiscoveredForm`, `DiscoveredScript`, `CrawlResult`) are designed as extensible base structures for future phases (subdomains, tech fingerprinting, API schemas).
6. **Audit Traceability**: Every crawl request logs structured audit events (`discovery.crawl_started`, `discovery.crawl_completed`, or `discovery.crawl_rejected`) capturing actor user ID, organization ID, target domain, page count, duration, and rejection reason.
7. **RBAC & Authorization**: `/api/v1/discovery/crawl` requires authentication (Bearer JWT or X-API-Key), valid organization context, and `targets:create` RBAC permission.
8. **Lazy Playwright Import**: `playwright.async_api` is imported lazily inside `SPADynamicCrawler.crawl()`. Zero top-level Playwright imports exist in the module layer, ensuring API server startup never crashes if Playwright is uninstalled.
9. **Graceful Static Fallback**: If Playwright package or Chromium binaries are missing (`PlaywrightUnavailableException`), `DiscoveryService` logs a warning (`discovery.playwright_unavailable_falling_back_to_static`) and executes `AsyncWebCrawler` (Phase 3.1).
10. **Background AJAX/Fetch Interception**: `SPADynamicCrawler` listens to `page.on("request", ...)` events to capture dynamic `fetch` and `XHR` calls, running SSRF checks (`is_safe_target_url`) on every intercepted endpoint.
11. **Enterprise IP Classification**: Rather than over-blocking and discarding internal IP findings, `classify_ip()` annotates IP addresses with `classification` (`PUBLIC`, `PRIVATE`, `LOOPBACK`, `LINK_LOCAL`, `RESERVED`), `is_internal`, and `is_egress_safe`. Enterprise ASM retains internal assets (e.g. `dev.company.local` -> `10.10.5.20`) for attack surface visibility while preventing SSRF during active HTTP scanning.
12. **Non-Blocking Async DNS Resolution**: `AsyncDNSResolver` uses `dnspython` to asynchronously query `A`, `AAAA`, `CNAME`, `MX`, `NS`, and `TXT` records in parallel across discovered subdomains.
13. **Passive Certificate Transparency Discovery**: `CTLogsClient` queries Certificate Transparency logs (`crt.sh`) via `httpx.AsyncClient` to discover active subdomains matching the target domain scope.
14. **Modular Technology Fingerprinting**: `TechFingerprinter` combines HTTP header signature parsing (Nginx, Apache, Express, PHP, Cloudflare), HTML meta generator tags (WordPress, Drupal), DOM structure markers (`__next`, `__nuxt`, `ng-version`, `data-reactroot`), and script paths (`react`, `vue`, `jquery`, `bootstrap`) into structured `DetectedTechnology` domain entities with version extraction and confidence scores.
15. **Security Header Compliance Auditing**: Automatically evaluates presence and configuration of `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy` headers during technology scans.
16. **Persistent Multi-Tenant Asset Graph**: `AssetNodeModel` (`asset_nodes`) and `AssetRelationshipModel` (`asset_relationships`) tables model asset nodes (`TARGET_DOMAIN`, `SUBDOMAIN`, `IP_ADDRESS`, `URL_ENDPOINT`, `FORM`, `SCRIPT`, `TECHNOLOGY`) and edge relationships (`BELONGS_TO`, `RESOLVES_TO`, `RUNS_TECH`, `HAS_ENDPOINT`, `DISCOVERED_FROM`).
17. **Automated Asset Graph Correlation**: `AssetGraphService.build_asset_graph` correlates crawling, DNS resolution, and technology stack fingerprints into a persistent, queryable graph topology with strict multi-tenant boundary checks.

---

## 13. Vulnerability Assessment Engine & Dynamic Testing Decisions

1. **Decoupled Abstract Plugin Interface**: `BaseAssessmentPlugin` (ABC in `app/domain/entities/assessment.py`) defines a strict, generic plugin contract. Every security plugin declares metadata (`id`, `name`, `version`, `supported_asset_types`, `required_permissions`) and implements `async execute(ctx: AssessmentContext) -> List[Finding]`.
2. **Generic Orchestration Architecture**: `AssessmentService` contains zero hardcoded scanner or vulnerability logic. It delegates plugin execution to `PluginRegistry`, receiving standardized `Finding` domain objects for database persistence.
4. **Safe Non-Destructive SQL Injection Probing**: `SQLInjectionPlugin` tests query parameters using safe SQL syntax markers (`'`, `''`, `' OR '1'='1`) and regex error pattern matching across 5 major database engines (PostgreSQL, MySQL, SQLite, Oracle, MSSQL) without performing destructive data modifications.
5. **Marker-Based Reflected XSS Detection**: `XSSPlugin` injects unique, non-executing marker tags (`"><vlnv_xss_probe_<uuid>>`) to confirm unescaped HTML reflection in HTTP responses without executing malicious scripts.
6. **Authentication & Session Flag Auditing**: `AuthSecurityPlugin` analyzes Set-Cookie directives for missing `HttpOnly`, `Secure`, or `SameSite` flags and flags unencrypted HTTP credential transmission.
7. **Exposed API Documentation Probing**: `APISecurityPlugin` probes target assets for exposed Swagger/OpenAPI/GraphQL documentation or schema endpoints (`/swagger`, `/swagger-ui`, `/openapi.json`, `/api-docs`, `/graphql`) and alerts on information disclosure risks.
8. **JWT Signature & Claims Analysis**: `JWTSecurityPlugin` inspects JSON Web Tokens for critical signing risks (`alg: none`), missing `exp` claims, excessive lifetime (> 24h), and missing `iss`/`aud` claims without requiring server secret keys.
9. **CORS Misconfiguration Detection**: `CORSPlugin` evaluates `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials` headers via custom `Origin` probes to flag wildcard origin credentials and arbitrary origin reflection.
10. **Non-Blocking Administrative Port Probing**: `NetworkServicePlugin` asynchronously checks for exposed high-risk administrative and database ports (SSH 22, RDP 3389, MySQL 3306, PostgreSQL 5432, MongoDB 27017, Redis 6379, Elasticsearch 9200) without stalling execution.
11. **TLS Certificate & Protocol Inspection**: `TLSSecurityPlugin` inspects SSL socket connections to audit certificate expiration, trust store verification, and deprecated protocol versions (TLS 1.0/1.1).
12. **Cloud Bucket & IMDS Exposure Auditing**: `CloudSecurityPlugin` detects public cloud storage bucket listing permissions (AWS S3, Azure Blob, GCP) and flags references to Cloud Metadata Service (169.254.169.254).
13. **Enterprise Platform Architectural Shift**: Vulnova has transitioned from a vulnerability plugin execution framework into an Enterprise Application Security Intelligence Platform. Future development prioritizes normalization, correlation, evidence, continuous monitoring, and AI-driven analysis over isolated vulnerability checks.
14. **Multi-Modal Evidence Capture & Proof Pipeline**: `EvidenceCollectionEngine` captures reproducible proof (masked HTTP request/response text dumps, header/cookie profiles, Playwright DOM snapshots, visual PNG screenshots) after finding normalization. Evidence artifacts are integrity-verified via SHA-256 checksums and saved to tenant-isolated storage paths (`EvidenceArtifactStorage`).
15. **Enterprise Scan Profile & Execution Policy Architecture**: Vulnova assessments are no longer directly plugin-triggered. The pipeline operates via profile resolution and policy validation:
    ```
    User Request ──► Scan Profile Resolution ──► Policy Validation ──► Plugin Execution ──► Risk Intelligence ──► Finding Deduplication ──► Evidence Collection ──► Assessment Storage
    ```
    - `ScanProfileRegistry` references `PluginRegistry` IDs only and does not duplicate plugin metadata or implementation logic.
    - `PluginRegistry` remains the single source of truth for plugin availability and capability verification.
    - `ScanPolicyEngine` is a stateless helper class independent of FastAPI/HTTP layers, ensuring full compatibility for reuse inside future Era 6 distributed Celery worker sandboxes.
16. **Multi-Source Finding Correlation & Asset Inventory Architecture**: Findings are no longer isolated scanner records. `AssessmentCorrelationEngine` maps normalized findings to Asset Graph nodes (`AssetNode`) and aggregates posture metrics:
    - `asset_node_id` remains an optional field (`Optional[UUID]`) on findings to preserve full backward compatibility with legacy scan data.
    - Findings are NOT duplicated as graph nodes; they remain stored in `security_findings` while linked via `asset_node_id` to prevent graph node explosion.
    - Asset posture risk scores reuse `RiskIntelligenceEngine` composite scores (`composite_risk_score`) rather than inventing secondary risk engines.
    - Every asset inventory query enforces mandatory `organization_id` filtering for strict multi-tenant boundary security.
17. **Attack Surface Posture Snapshotting & Continuous Monitoring Architecture**: Vulnova posture snapshots and change detection events:
    - `AssetSnapshotModel` (`asset_snapshots` table) records point-in-time posture aggregates (`total_assets`, `total_findings`, `critical_findings`, `high_findings`, `avg_risk_score`, `max_risk_score`) per organization assessment run.
    - Every posture snapshot is organization isolated (`organization_id`), assessment linked (`assessment_job_id`), and timestamped (`created_at`) to build immutable security audit history.
    - Risk score trajectory metrics reuse `RiskIntelligenceEngine` composite scores (`f.risk.composite_risk_score`) directly; zero secondary risk calculators are introduced.
    - `ChangeDetectionEngine` identifies vulnerability lifecycle state transitions (`FINDING_NEW`, `FINDING_RESOLVED`, `FINDING_REOPENED`) and records discrete audit timeline events in `AssetChangeEventModel` (`asset_change_events`).
18. **Enterprise Finding Triage & Automated Suppression Architecture**: Vulnova vulnerability lifecycle management and automated false-positive suppression:
    - Preserves full backward compatibility: original `security_findings` records, risk scores, evidence dumps, and asset graph correlations from Phase 4.5 – Phase 4.9 remain completely intact. Triage operates as an additional intelligence layer on top of findings.
    - `FindingTriageHistoryModel` (`finding_triage_history` table) captures an immutable audit history of analyst finding triage actions (`UNREVIEWED`, `CONFIRMED`, `FALSE_POSITIVE`, `RISK_ACCEPTED`, `REMEDIATED`, `REOPENED`) with timestamps, actor attribution (`actor_user_id`), comments, and optional risk acceptance expiration dates (`risk_accepted_until`).
    - `FindingSuppressionRuleModel` (`finding_suppression_rules` table) persists tenant-isolated automated false-positive suppression rules (`EXACT_CWE`, `TARGET_PATTERN`, `PLUGIN_ID`, `COMPOSITE`).
    - `FindingTriageService.evaluate_suppression_rules` automatically matches active suppression rules against findings post-assessment, overlaying suppression metadata without corrupting underlying CVSS/EPSS risk scores or evidence proof.
    - Reuses existing `AuditLogService` event recording (`finding.triaged`, `suppression_rule.created`, `suppression_rule.deleted`) for audit compliance traceability.
    - RBAC permissions strictly enforce authorization boundary controls (`findings:triage` requires `SECURITY_ANALYST` role, while `findings:suppress` requires `ADMIN` role). Every query in `FindingTriageRepository` enforces mandatory `organization_id` tenant filtering.
19. **Multi-Provider LLM Gateway & Prompt Orchestration Architecture (Phase 5.1)**: Vulnova AI gateway and prompt engineering architecture:
    - **Provider Independence & Zero Mandatory SDK Dependencies**: Provider adapters (`OpenAIAdapter`, `AnthropicAdapter`, `GoogleAdapter`, `LocalOllamaAdapter`) inherit from abstract `BaseLLMAdapter` and execute HTTP requests via `httpx.AsyncClient` REST calls. Zero third-party LLM SDK packages are required as mandatory dependencies, ensuring Vulnova application startup remains unhindered in air-gapped or local Ollama environments.
    - **Reusable Secret Encryption Service**: API keys and external integration credentials are encrypted at rest using AES-256-GCM (`SecretEncryptionService` in `app/security/encryption.py`), providing a reusable abstraction for future cloud, SIEM, and threat intelligence secrets.
    - **Priority-Based Fallback & Provider Health Cooldown Tracking**: `LLMGatewayService` attempts provider execution by priority. If a provider encounters HTTP 5xx errors or rate limits, the gateway records failure counts and puts the failing provider into a health cooldown period (e.g. 5 minutes), automatically routing traffic to secondary providers (or local Ollama fallback) without repeatedly invoking failing endpoints.
    - **Immutable Security Prompt Versioning**: Prompt templates (`PromptTemplateModel`) are strictly immutable after creation. Modifying a prompt for a category and name automatically assigns `version = max_version + 1`, preserving historical prompt versions to guarantee audit reproducibility for security AI analyses.
    - **Sensitive Prompt Context Sanitization**: `PromptOrchestratorService` automatically strips/masks Authorization Bearer tokens, cookies, API keys, and passwords from security finding and evidence dumps before formatting prompt payloads (`mask_sensitive_prompt_context`).
    - **Internal Gateway Foundation for AI Agents**: `/ai/chat/completions` and `LLMGatewayService` act as an internal infrastructure gateway foundation. Downstream Era 5 AI agents (`AIFindingExplainerService`, `AttackPathSynthesizer`, `AIRemediationEngine`) consume `LLMGatewayService` and `PromptOrchestratorService` internally.
