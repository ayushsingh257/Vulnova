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

31. **Enterprise Administration Workspace & Control Plane Architecture (Phase 7.6)**: Enterprise control plane & RBAC governance workspace:
    - **Zero Parallel Auth / User System Safeguard**: Reuses existing `OrganizationModel`, `UserModel`, `APIKeyModel`, `AuditLogModel`, `PERMISSION_MAP`, and `Role` enum across Era 2 foundations. Zero duplicate database schemas or permission engines created.
    - **`AdminService` Aggregator (`app/application/admin/admin_service.py`)**: Assembles organization profile metadata, team user management workflows, role-permission matrix visualization data, machine-to-machine API key governance, and security posture overview states.
    - **Sole Owner Demotion & Self-Deactivation Protections**: `update_user_role` and `deactivate_user` enforce active owner count checks (`count_owners_in_org <= 1`) and self-deactivation guards (`target_user_id != current_user.id`), preventing accidental lockout of organization control.
    - **Raw API Key Show-Once Governance**: Machine-to-machine API keys generated via `create_api_key` return raw secret token (`vn_live_...`) ONCE in creation response payload. Only `key_prefix` and SHA-256 `key_hash` are stored in database. Detailed audit events (`api_key.created`, `api_key.revoked`) capture `actor_user_id`, `organization_id`, `resource_id`, `timestamp`, and `action`.
    - **Canonical Permission Consistency**: Endpoints enforce canonical permissions (`organization:read`, `organization:update`, `users:read`, `users:invite`, `users:update_role`, `users:remove`, `api_keys:read`, `api_keys:create`, `api_keys:revoke`) matching `PERMISSION_MAP` across backend, `SECURITY.md`, and `API_SPEC.md`.
    - **Frontend Service & Next.js Settings Routes**: `AdminService` (`frontend/services/admin.service.ts`), 5 Next.js settings routes (`frontend/app/(dashboard)/settings/` for `organization`, `users`, `roles`, `api-keys`, `security`), and 5 reusable UI components (`UserManagementTable`, `InviteUserModal`, `RolePermissionMatrix`, `APIKeyManagementPanel` with raw secret key dialog, `SecuritySettingsCard` with MFA enrollment tracking).

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

25. **Enterprise AI Security Copilot Architecture (Phase 5.7)**: AI Security Copilot architecture rules:
    - `SecurityCopilotService` acts as the primary conversational SOC assistant, unifying intelligence from LLM Gateway, Finding Explainer/Impact Engine, Attack Path Engine, Remediation Engine, False Positive/Confidence Engine, and pgvector RAG Knowledge Base.
    - Multi-agent intent classification (`AgentOrchestrator`) routes queries to specialized sub-agent personas (`SECURITY_ANALYST`, `EXPLAINER`, `ATTACK_PATH`, `REMEDIATION`, `FALSE_POSITIVE`, `KNOWLEDGE_RAG`).
    - Tool execution (`CopilotToolRegistry`) is strictly restricted to read-only security tools (`get_finding_details`, `get_asset_topology`, `get_risk_summary`, `search_rag_knowledge`, `get_remediation_plan`, `get_confidence_analysis`, `get_attack_path`) under a strict **Human-in-the-Loop Only** policy with tool audit logging (`ai_copilot_tool_executions`).
    - Grounding explainability metadata (`response_confidence_score`, `sources_used`, `knowledge_chunks_used`, `tools_called`, `reasoning_summary`, `model_used`, `prompt_version`, `response_evaluation_metadata`) MUST be tracked on every assistant message.
    - Data is stored across a 5-table normalized schema (`ai_copilot_sessions`, `ai_copilot_messages`, `ai_copilot_context_memories`, `ai_copilot_tool_executions`, `ai_copilot_feedback`) with strict multi-tenant boundary checks (`organization_id = tenant_id`) and RBAC authorization (`copilot:read`, `copilot:chat`, `copilot:manage`, `copilot:feedback`).

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
20. **AI Finding Explainer & Impact Analysis Architecture (Phase 5.2)**: Autonomous AI Security Analyst capability:
    - **Domain Entity Classification**: `AIFindingExplanation` and `AIImpactAnalysis` are classified as **Domain Entities** with persistent identity (`UUID`), lifecycle status (`COMPLETED`, `FAILED`, `STALE`), timestamps, and audit history.
    - **Structured Output JSON Repair Recovery**: In the event of malformed LLM JSON output, `AIFindingExplainerService` and `ImpactAnalysisService` execute a single repair retry using a strict JSON repair prompt before recording a `FAILED` status, preventing corrupt records from entering database tables.
    - **Reuse Existing Risk Scores**: AI analysis services read composite risk scores (`composite_risk_score`) directly from `SecurityFindingModel.risk_score` without recalculation or override.
    - **Tenant Isolation & Non-Repudiation Audit Trail**: Explanations (`ai_finding_explanations`) and impact reports (`ai_impact_analyses`) enforce mandatory `organization_id` foreign keys and query filters, with generation events recorded via `AuditLogService.record_event` (`finding.ai_explained`, `finding.impact_analyzed`).
21. **AI Attack Path Synthesis Architecture (Phase 5.3)**: Graph-aware attack chain reasoning engine:
    - **Option A Relational Storage Selection**: Stores attack paths using Option A normalized relational tables (`ai_attack_paths` + `ai_attack_path_steps`) rather than JSON blobs, allowing sub-millisecond relational queries by MITRE technique ID, step sequence filtering, and step-level correlation.
    - **MITRE ATT&CK Registry Validation**: Validates step technique IDs against `KNOWN_MITRE_TECHNIQUES` registry. Invalid or non-standard technique IDs are flagged as `Unverified` to prevent corrupting framework analytics.
    - **Path & Step Level Confidence Scoring**: Every attack path calculates and persists an overall path `confidence_score` (Float 0.0–1.0) along with individual step confidence ratings to communicate reliability to SOC analysts.
    - **SOC Analyst Feedback Loop**: Supports analyst review state transitions (`GENERATED`, `REVIEWED`, `ACCEPTED`, `REJECTED`, `STALE`) and captures reviewer feedback notes (`review_notes`, `reviewed_by`, `reviewed_at`) via `PATCH /api/v1/ai/attack-paths/{id}/review`.
    - **Evidence Grounding Safeguard**: Attack context is constructed strictly from verified asset graph nodes (`AssetNode`), edge relationships (`AssetRelationshipModel`), and evidence artifacts. LLM system prompts strictly forbid hallucinating unsupported target assets or vulnerabilities.
22. **AI Remediation Engine & Fix Recommendation Architecture (Phase 5.4)**: Autonomous fix guidance engine:
    - **Strict Non-Executable Human Approval Safety Policy**: Generated remediation guidance, code diffs, and configuration patches are stored purely as advisory text strings. The service contains zero shell execution, git commit, or cloud API auto-mutation triggers, ensuring all remediations require human analyst review.
    - **3-Table Normalized Relational Storage**: Persists plans across `ai_remediation_plans`, `ai_remediation_steps`, and `ai_patch_suggestions` tables for language-specific indexing (`language`), step order sorting, and step-level queryability.
    - **Dual Confidence & Operational Risk Tracking**: Records separate `ai_confidence_score` (LLM generation accuracy) and `effectiveness_confidence_score` (estimated fix resolution confidence) alongside operational risk flags (`requires_backup`, `requires_downtime`, `rollback_available`) and version targets (`cve_id`, `cwe_id`, `affected_version`, `fixed_version`).
    - **Analyst Review State Machine**: Supports review workflows (`GENERATED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `IMPLEMENTED`, `VERIFIED`, `VALIDATION_FAILED`) with reviewer attribution (`reviewed_by`, `review_notes`) via `PATCH /api/v1/ai/remediation/{id}/review`.
    - **Multi-Layer Intelligence Context Assembly**: Assembles context across 7 verified intelligence layers (finding, evidence proof, asset graph, triage state, Phase 5.2 explanations, Phase 5.2 impact analysis, Phase 5.3 attack paths) with secret context masking (`mask_sensitive_prompt_context`).
23. **AI False Positive Filter & Finding Confidence Architecture (Phase 5.5)**: Non-suppression analyst-assisted confidence engine:
    - **Strict Non-Suppression Safety Policy**: AI confidence assessments (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `NEEDS_REVIEW`) and evidence quality scores serve as advisory analyst intelligence. The service contains zero automated finding closure, deletion, or suppression execution code.
    - **2-Table Normalized Relational Storage**: Persists analyses across `ai_finding_confidence_analyses` and `ai_finding_similarity_matches` tables for classification and similarity score indexing.
    - **Score Calibration Feedback Loop**: Analyst review feedback (`PATCH /api/v1/ai/confidence-analysis/{id}/review`) records calibration tracking metadata (`predicted_confidence_score`, `analyst_final_decision`, `confidence_accuracy_delta`, `feedback_timestamp`) to feed future AI Copilot learning loops.
    - **Multi-Signal Duplicate Correlation**: Evaluates 8 distinct matching signals (`CVE`, `CWE`, `ENDPOINT`, `ASSET_NODE`, `PLUGIN_ID`, `VULNERABILITY_TITLE`, `AFFECTED_COMPONENT`, `ATTACK_TECHNIQUE`) to compute similarity scores (0.0–1.0).
    - **8-Layer Intelligence Context Assembly**: Assembles context across 8 verified intelligence layers (finding, evidence, asset topology, triage history, Phase 5.2 explanation, Phase 5.2 impact, Phase 5.3 attack path, Phase 5.4 remediation plan) with prompt injection protection (`<untrusted_security_context>`) and secret context masking (`mask_sensitive_prompt_context`).
24. **Security Knowledge Base & RAG Vector Engine Architecture (Phase 5.6)**: Vector-indexed security knowledge retrieval:
    - **PostgreSQL pgvector & HNSW Indexing**: Stores 1536-dimensional embeddings in `security_knowledge_chunks` with HNSW cosine similarity indexing (`vector_cosine_ops`, `m=16`, `ef_construction=64`).
    - **Source-Type Configurable Chunking**: Document text splitting applies source-type chunk size and overlap parameters (`OWASP`/`CWE`/`CAPEC`: 512/64, `CVE_NVD`: 256/32, `INTERNAL_POLICY`: 768/128, `CUSTOM`: configurable).
    - **Embedding Migration & Citation Tracking**: Tracks `embedding_model` (`"text-embedding-3-small"`) and `embedding_dimension` (`1536`) alongside source citations (`source_url`, `source_author`, `published_date`, `last_updated_date`) for exact citation formatting.
    - **Governance Approval Workflow**: Internal security policies uploaded to tenant knowledge bases start in `UNDER_REVIEW` and require explicit analyst governance approval (`PATCH /api/v1/ai/knowledge/documents/{id}/review`) before vector indexing into search stores.
    - **Hybrid Tenant Boundary Protection**: Tenant isolation strictly enforces `organization_id IS NULL OR organization_id = tenant_id`. Shared global standards (OWASP/CWE) are accessible across all tenants while private organizational security guidelines remain strictly isolated.
25. **Celery Worker Sandbox & Distributed Orchestration Architecture (Phase 6.1)**: Distributed scan execution engine:
    - **Container Sandbox Resource Caps**: Celery worker task executions enforce container sandbox resource caps: `cpu_limit_vcpu=1.0`, `memory_limit_mb=512`, `read_only_rootfs=True`, `no_new_privs=True`, unprivileged UID/GID `10001`, dropped `ALL` capabilities, and network egress filtering.
    - **Execution Isolation Safeguard**: Celery workers do NOT execute raw OS commands directly. All job executions pass through: `Celery Worker -> Task Queue -> Sandbox Executor -> Job Dispatch`.
    - **Priority Queue Routing**: Distributed tasks are routed across priority task queues: `scans.high`, `scans.default`, `scans.low`, and `ai.priority` with `task_ack_late=True` and `worker_prefetch_multiplier=1`.
    - **Multi-Tenant Database Tracking**: `WorkerNodeModel` (`worker_nodes`) and `WorkerTaskModel` (`worker_task_executions`) include `organization_id` and `requested_by` fields for multi-tenant isolation and capacity metrics calculation.
    - **RBAC & Audit Logging**: Worker cluster operations enforce permissions (`workers:read`, `workers:manage`, `scans:dispatch`) and audit events (`worker_task.dispatched`, `worker_task.cancelled`).
26. **Security Operations Dashboard & Analyst Experience Architecture (Phase 7.1)**: Unified analyst SOC dashboard & metrics engine:
    - **`DashboardAnalyticsService` Aggregator**: Computes composite risk scores (0–100), posture status classifications (`SECURE`, `ELEVATED_RISK`, `CRITICAL_RISK`), vulnerability severity breakdowns, active scan telemetry, target asset risk leaderboards, and schedule summaries.
    - **Sub-20ms Redis Caching Layer (`dashboard:metrics:{org_id}`)**: 30s TTL buffers PostgreSQL against high-frequency browser refreshes.
    - **Tenant Isolation Safeguard**: Every SQL query enforces `organization_id = current_user.organization_id`.
    - **FastAPI REST Router (`/api/v1/dashboard`)**: `GET /overview` (`dashboard:read`), `GET /posture` (`analytics:read`), `GET /scans/active` (`scans:read`).
    - **Next.js SOC Dashboard Components**: `DashboardLayout`, `SecurityPostureCard`, `ActiveScanMonitor` (WebSocket event subscription), `VulnerabilityChart`, `AssetRiskOverview`, `SchedulesOverview`.
27. **Public Marketing Pages, Enterprise Trust Center & Security Disclosure Gateway Architecture (Phase 7.2)**: Public compliance & disclosure gateway:
    - **`TrustCenterService` Aggregator**: Aggregates high-level system operational status (`OPERATIONAL`, `DEGRADED_PERFORMANCE`, `UNDER_MAINTENANCE`), OWASP ASVS v4.0 control mappings across 7 core categories, AES-256-GCM envelope encryption specifications, container sandbox isolation bounds, and RFC 9116 security disclosure policies.
    - **RFC 9116 `security.txt` Support**: Generates plain text `/.well-known/security.txt` and `/api/v1/public/security.txt` directives with security contact email (`security@vulnova.com`), PGP encryption key URL, canonical URL, and expiration date.
    - **300s Redis Caching Layer (`trust_center:public_summary`)**: Buffers backend services against automated public crawler traffic.
    - **Strict Public Data Boundary Safeguard**: Public endpoints expose ONLY static platform architecture specifications, compliance frameworks, and high-level health indicators. ZERO tenant data, target URLs, vulnerability findings, or credentials are exposed.
    - **SEO, OpenGraph & Next.js Public Pages**: `frontend/app/(public)/trust/page.tsx`, `frontend/app/(public)/security/page.tsx`, `frontend/app/robots.ts`, and redesigned root landing page `frontend/app/page.tsx`.
28. **Enterprise Executive Analytics, Risk Snapshot Engine & Threat Advisory System (Phase 7.3)**: Decoupled executive intelligence platform:
    - **Decoupled Application Services Architecture**: Separates executive concerns across specialized services — `ExecutiveAnalyticsService` (historical trends, velocity, MTTR, attack surface coverage), `ThreatAdvisoryService` (CVSS 9.0+ alerts, SLA breaches, target contract expirations), and `ExecutiveReportService` (report payload assembly & JSON/CSV exports).
    - **Database-Backed Persistent Snapshots (`risk_posture_snapshots`)**: `RiskPostureSnapshotModel` records daily posture snapshots (`organization_id`, `composite_risk_score`, `posture_status`, `total_targets_count`, `total_open_findings`, `critical_count`, `high_count`, `medium_count`, `low_count`, `info_count`, `mttr_hours`, `snapshot_date`) with composite index `idx_risk_snapshots_org_date`.
    - **Celery Beat Daily Snapshot Scheduler (`capture_daily_risk_snapshots`)**: Periodic background worker task running every 24 hours (midnight UTC) to snapshot posture metrics across active tenant organizations.
    - **300s Redis Caching (`dashboard:trends:{org_id}:{timeframe}`)**: Caches historical risk trajectory points and velocity classifications (`STABLE`, `IMPROVING`, `DETERIORATING`).
    - **Executive Report Export Engine**: Exposes `/api/v1/dashboard/export` for JSON and CSV exports (`reports:export` permission) with rate limiting (`rate_limit:export:{org_id}`, 10 req/min). *Roadmap Note*: Future Executive Reporting Engine extensions will add native PDF rendering and compliance packages (SOC 2, ISO 27001).
    - **Next.js Executive Widgets**: `HistoricalRiskChart` (7d/30d/90d selector, velocity badge, MTTR meter), `AttackSurfaceCoverageWidget` (environment breakdown), `ThreatAdvisoriesDrawer` (SLA warning alerts), and `ExecutiveReportExportButton`.
29. **Scan Management Portal & Live Telemetry Stream Architecture (Phase 7.4)**: Operations portal & real-time telemetry engine:
    - **Target Data Exposure Protection**: Exposes ONLY masked target URL domain labels (`https://a***.s***.e***.com`) in summary list endpoints (`GET /api/v1/assessments`). Full raw target URLs are restricted to authorized detail endpoints (`GET /api/v1/assessments/{id}/telemetry`) with `scans:read` permissions.
    - **Decoupled `ScanManagementService`**: `ScanManagementService` handles paginated queries (`list_assessments_paginated`), telemetry payload assembly (`get_assessment_telemetry_summary`), and lifecycle state control delegation (`pause`, `resume`, `cancel`, `retry`), keeping `AssessmentService` focused strictly on assessment creation and dispatch logic.
    - **Frontend Service Abstraction (`frontend/services/scans.service.ts`)**: Encapsulates all backend REST API calls (`listScans`, `getScanTelemetry`, `dispatchScan`, `pauseScan`, `resumeScan`, `cancelScan`, `retryScan`) and WebSocket stream setup outside React components.
    - **Next.js Scan Management UI Routes & Components**: `ScansPage` (`frontend/app/(dashboard)/scans/page.tsx`), `ScanDetailPage` (`frontend/app/(dashboard)/scans/[id]/page.tsx`), `ScanListTable`, `ScanDispatchModal` (with CFAA legal consent check), `ScanActivityTimeline` (step progression milestones), `ScanExecutionTelemetry`, `LiveEventConsole` (WebSocket log stream), and `ScanControlsBar`.
30. **Vulnerability Triage, Evidence Record Viewer & AI Remediation Drawer Architecture (Phase 7.5)**: Analyst investigation workspace & intelligence aggregator:
    - **Zero Duplicate Architecture Safeguard**: Reuses existing `SecurityFindingModel`, `EvidenceArtifactModel`, `AssessmentJobModel`, `FindingTriageHistoryModel`, `AIFindingExplanationModel`, `AIAttackPathModel`, and `AIRemediationPlanModel` across 9 database models. Introduces zero duplicate vulnerability tables or risk scoring engines.
    - **Read-Only `FindingIntelligenceService` Aggregator (`app/application/finding/finding_intelligence_service.py`)**: Assembles unified vulnerability intelligence responses (`get_finding_details`), proof evidence lists with normalized type labels (`get_finding_evidence`), attack chain node visualizations (`get_finding_attack_paths`), and AI fix guidance (`get_finding_remediation`).
    - **On-Demand AI Remediation Integration**: Triggering `POST /api/v1/vulnerabilities/{id}/remediation-ai` invokes existing `AIRemediationService.generate_remediation_plan()` (Phase 5.4) to synthesize advisory fix guidance under a strict non-executable human-in-the-loop approval safety policy.
    - **Frontend Service Abstraction (`frontend/services/vulnerabilities.service.ts`)**: Encapsulates all `/api/v1/vulnerabilities` REST API calls outside React components.
    - **Next.js Vulnerability Investigation UI Routes & Components**: `VulnerabilityDetailPage` (`frontend/app/(dashboard)/vulnerabilities/[id]/page.tsx`), `VulnerabilityHeader` (CVSS & EPSS gauges, CVE/CWE tags), `CVSSRiskCard` (exploitability/impact sub-scores, SLA breach meter), `EvidenceViewerDrawer` (tabbed HTTP request/response payloads, screenshots, DOM snapshots, plugin output, SHA-256 integrity badges), `AttackPathGraph` (vertical attack chain node sequence), and `AIRemediationDrawer` (AI explanation summary, step-by-step fix guides, syntax-highlighted code patches, verification checklist).
31. **Enterprise Administration Workspace & Control Plane Architecture (Phase 7.6)**: Enterprise control plane & RBAC governance workspace:
    - **Zero Parallel Auth / User System Safeguard**: Reuses existing `OrganizationModel`, `UserModel`, `APIKeyModel`, `AuditLogModel`, `PERMISSION_MAP`, and `Role` enum across Era 2 foundations. Zero duplicate database schemas or permission engines created.
    - **`AdminService` Aggregator (`app/application/admin/admin_service.py`)**: Assembles organization profile metadata, team user management workflows, role-permission matrix visualization data, machine-to-machine API key governance, and security posture overview states.
    - **Sole Owner Demotion & Self-Deactivation Protections**: `update_user_role` and `deactivate_user` enforce active owner count checks (`count_owners_in_org <= 1`) and self-deactivation guards (`target_user_id != current_user.id`), preventing accidental lockout of organization control.
    - **Raw API Key Show-Once Governance**: Machine-to-machine API keys generated via `create_api_key` return raw secret token (`vn_live_...`) ONCE in creation response payload. Only `key_prefix` and SHA-256 `key_hash` are stored in database. Detailed audit events (`api_key.created`, `api_key.revoked`) capture `actor_user_id`, `organization_id`, `resource_id`, `timestamp`, and `action`.
    - **Canonical Permission Consistency**: Endpoints enforce canonical permissions (`organization:read`, `organization:update`, `users:read`, `users:invite`, `users:update_role`, `users:remove`, `api_keys:read`, `api_keys:create`, `api_keys:revoke`) matching `PERMISSION_MAP` across backend, `SECURITY.md`, and `API_SPEC.md`.
    - **Frontend Service & Next.js Settings Routes**: `AdminService` (`frontend/services/admin.service.ts`), 5 Next.js settings routes (`frontend/app/(dashboard)/settings/` for `organization`, `users`, `roles`, `api-keys`, `security`), and 5 reusable UI components (`UserManagementTable`, `InviteUserModal`, `RolePermissionMatrix`, `APIKeyManagementPanel` with raw secret key dialog, `SecuritySettingsCard` with MFA enrollment tracking).
32. **PDF & HTML Executive Security Report Generator Architecture (Phase 8.1)**: Enterprise CISO report generation engine:
    - **Dual Template & Document Generation Engine**: Integrates Jinja2 HTML rendering (`HTMLRendererService` using `templates/executive_report.html` and print-ready CSS `templates/style.css`) and WeasyPrint PDF generation (`PDFGeneratorService`). Supports graceful fallback to a compliant binary PDF/1.4 container wrapper if underlying C-libraries (`libgobject`, `libcairo`) are missing in lightweight container environments, guaranteeing HTTP 200/500 stability.
    - **Zero Database Duplication & Multi-Service Aggregator (`ExecutiveSecurityReportService`)**: Aggregates posture metrics, time-series risk trends, attack surface environment coverage, vulnerability severity breakdowns, top findings, and threat advisories from existing `DashboardAnalyticsService`, `ExecutiveAnalyticsService`, and `ThreatAdvisoryService`. Zero new database tables created for report generation.
    - **Tenant Isolation & Audit Trail Non-Repudiation**: Enforces strict tenant boundary isolation (`organization_id = current_user.organization_id`). Every report payload generation and PDF stream download records immutable security audit events (`report.generated`, `report.downloaded`) via `AuditLogService`.
    - **Canonical Permissions & REST API Router (`/api/v1/reports`)**: REST endpoints enforce canonical RBAC permissions (`reports:create`, `reports:read`, `reports:export`) matching `PERMISSION_MAP`: `POST /executive`, `GET /{id}`, `GET /{id}/html`, `GET /{id}/pdf`.
    - **Frontend Service & Next.js CISO Reporting Workspace**: `ReportsService` (`frontend/services/reports.service.ts`), Next.js routes (`frontend/app/(dashboard)/reports/` for `page.tsx` and `[id]/page.tsx`), and 5 reusable UI components (`SecurityMetricsSummary`, `ExecutiveReportCard`, `ReportGenerationModal`, `ReportPreview`, `ReportDownloadActions`).
33. **Enterprise Production Reliability & Operational Maturity Roadmap Evolution (Era 11 Planning)**: Strategic expansion beyond functional feature development into enterprise SaaS production reliability:
    - **Rationale & Operating Paradigm**: Operating thousands of enterprise tenant scans requires evolving Vulnova beyond feature completeness into full operational maturity under the operational lifecycle paradigm: **Build → Secure → Monitor → Recover → Scale**.
    - **Pillar 1 — Observability & Telemetry**: Prometheus time-series metrics exporter (`/metrics`), Grafana operational dashboard visualization, Loki/ELK centralized log aggregation, Sentry exception tracking, automated alert rules, and synthetic `/health` liveness/readiness probes.
    - **Pillar 2 — Database Backup Strategy & PITR**: Automated PostgreSQL WAL archiving, daily full backup scheduling, 30-day retention policies, AES-256 backup encryption at rest, and daily automated restore verification dry-runs.
    - **Pillar 3 — Disaster Recovery & Failover**: Recovery Time Objective (RTO < 1 hour), Recovery Point Objective (RPO < 5 minutes), multi-region DB failover workflows, and single-command zero-downtime deployment rollback strategies.
    - **Pillar 4 — Incident Response Lifecycle**: 4-tier severity classification (`SEV-1 Critical` to `SEV-4 Low`), automated PagerDuty/Slack alert escalation rules, forensic audit log investigation workflows (`AuditLogService`), and mandatory post-incident review (PIR) root cause analysis templates.
34. **Developer Technical Remediation Export Architecture (Phase 8.2)**: Developer-focused technical export subsystem:
    - **Zero Database Table Duplication & Zero Archival Storage**: Introduces **zero new database tables** and **zero document archival storage** (no MinIO/S3 or export history tables). Reuses existing PostgreSQL repositories (`security_findings`, `evidence_artifacts`, `ai_remediation_plans`, `ai_finding_explanations`, `ai_attack_paths`, `assessment_jobs`). All exports are generated on demand from authoritative data models.
    - **Memory-Efficient Chunking & Streaming Engine (`DeveloperExportService`)**: Implements streaming generators (`_stream_findings`) fetching findings in batches of 50 via limit/offset pagination. Exporters stream output directly into `StreamingResponse` objects (`export_json_stream`, `export_csv_stream`, `export_markdown_stream`), eliminating worker OOM memory crashes when exporting large enterprise finding datasets.
    - **Multi-Format Technical Exporters**:
      - **JSON Exporter**: Generates structured machine-readable JSON packages containing finding metadata, CVSS/EPSS scores, CVE/CWE details, evidence references, attack path node chains, AI explanations, and recommended code patch diffs.
      - **CSV Exporter**: Formats finding records into spreadsheet-ready CSV tables for engineering vulnerability tracking workflows.
      - **Markdown Exporter**: Formats finding details into GitHub Issue / Jira / GitLab ticket-ready Markdown documentation with formatted sections (`# Vulnerability Report`, `## Finding Summary`, `## Risk Details`, `## Evidence & Payloads`, `## Attack Path Sequence`, `## Recommended AI Fix & Code Patches`, `## Remediation Verification Steps`).
    - **Single Finding Export Package**: `export_single_finding` compiles detailed intelligence, evidence payloads, attack path graphs, and AI fix recommendations into ticket-ready Markdown, JSON, or CSV files. Automatically redacts sensitive tokens, Bearer headers, and session cookies (`sanitize_sensitive_data`).
    - **Tenant Isolation & Audit Trail**: All queries enforce strict tenant boundaries (`organization_id = current_user.organization_id`). Every bulk export or single finding download dispatches immutable security audit events (`report.exported`, `vulnerability.exported`) with format, target ID, finding count, and timestamp via `AuditLogService`.
    - **REST API Router (`/api/v1/reports/export`)**: REST endpoints enforce canonical RBAC permission `reports:export` (`Role.SECURITY_ANALYST` level 20+): `GET /json`, `GET /csv`, `GET /markdown`, `GET /{finding_id}?format=...`.
    - **Frontend Service & Technical Export Panel**: `ExportService` (`frontend/services/export.service.ts`) for browser Blob downloads, `TechnicalExportPanel` component (`frontend/components/reports/TechnicalExportPanel.tsx`) with format selection tabs, scope controls, one-click file download, and one-click copy-to-clipboard for Markdown ticket snippets integrated into `/reports/[id]` and `/vulnerabilities/[id]`.
35. **Compliance Intelligence Layer & Framework Mapping Architecture (Phase 8.3)**: Compliance framework mapping engine evaluating security findings against enterprise compliance standards:
    - **Supported Enterprise Frameworks & Version Metadata**: Maps vulnerability intelligence to 4 explicit framework specifications: `OWASP Top 10 2021` (A01:2021-A10:2021), `OWASP ASVS 4.0.3` (V2-V8 verification requirements), `PCI DSS 4.0` (Req-6, Req-7, Req-8, Req-10, Req-11), and `ISO 27001:2022` (Annex A.5, A.8, A.9, A.12, A.14, A.16).
    - **Zero Database Table Duplication & On-Demand Evaluation**: Introduces **zero new database tables** and **zero report archival storage**. Evaluates compliance posture dynamically from existing `security_findings` using static CWE and category mapping definitions (`owasp_top10.py`, `asvs_v4.py`, `pci_dss.py`, `iso27001.py`).
    - **Active Finding Filter & Score Arithmetic**: Compliance score percentage is calculated as `(passed_controls / total_controls) * 100.0`. Evaluator strictly filters for active open findings (`OPEN`, `CONFIRMED`, `NEW`, `UNREAD`, `TRIAGED`, `IN_REMEDIATION`). Resolved, verified fixed, and false-positive findings do not impact compliance scores.
    - **Full Control-to-Evidence Traceability**: Maintains end-to-end traceability chain: `Framework Control -> Vulnerability Finding -> Evidence Artifact Checksum -> Target Asset -> Remediation Guidance` (`ComplianceFindingMappingDTO`).
    - **REST Router (`/api/v1/compliance`) & Granular RBAC**: REST endpoints backed by `compliance:read` (`Role.VIEWER` level 10+) and `compliance:export` (`Role.SECURITY_ANALYST` level 20+): `GET /{framework}/overview`, `GET /{framework}/controls`, `GET /{framework}/export`. Dispatches immutable audit events (`compliance.viewed`, `compliance.exported`) via `AuditLogService`.
    - **Next.js Compliance Workspace**: Compliance dashboard (`/compliance`), framework detail route (`/compliance/[framework]`), framework selector tabs (`FrameworkSelector`), posture score card (`ComplianceScoreCard`), controls evaluation table (`ComplianceControlTable`), slide-in evidence drawer (`ComplianceEvidenceDrawer`), and JSON report downloader (`ComplianceExportButton`).
36. **External Security Workflow Integration Layer Architecture (Phase 9.1)**: Enterprise integration plugin enabling bi-directional vulnerability synchronization with Atlassian Jira Cloud and GitHub Issues:
    - **Zero Database Table Duplication & Plaintext Secret Protection**: Introduces **zero new database tables** and **zero schema migrations**. Reuses existing PostgreSQL models (`OrganizationModel`, `security_findings`, `audit_logs`). Provider credentials (API tokens and PATs) are encrypted at rest using AES-256-GCM / Fernet via `SecretEncryptionService` and masked in all API responses.
    - **Controlled State Transition Layer**: External status updates pass through controlled state transition mappers (`ControlledJiraStatusMapper`, `ControlledGitHubStatusMapper`) before modifying internal Vulnova finding lifecycle states (`DONE`/`CLOSED` -> `RESOLVED`, `IN_PROGRESS` -> `IN_REMEDIATION`, `OPEN` -> `CONFIRMED`). Prevents external systems from directly mutating security state without validation.
    - **Provider Clients & Format Mappers**: `JiraClient` & `JiraFindingMapper` format issues into Atlassian Document Format (ADF) JSON; `GitHubClient` & `GitHubFindingMapper` format issues into GitHub-Flavored Markdown with risk details, proof evidence, and AI remediation diffs.
    - **REST API Router (`/api/v1/integrations`) & Granular RBAC**: REST endpoints backed by `integrations:read` (`Role.VIEWER` level 10+), `integrations:create` and `integrations:update` (`Role.SECURITY_ANALYST` level 20+), and `integrations:manage` (`Role.ADMIN` level 30+). Dispatches non-repudiable audit events (`integration.configuration_updated`, `integration.issue_created`, `integration.issue_synced`) via `AuditLogService`.
    - **Next.js Integration Control Plane**: Integration dashboard (`/integrations`), provider settings (`/integrations/settings`), `IntegrationsService`, `IntegrationSettingsCard`, `CreateIssueModal`, `IntegrationHistoryPanel`, and sidebar navigation integration under "Operations Control".
37. **Real-Time Security Notification & Webhook Framework Architecture (Phase 9.2)**: Enterprise security alert dispatching system for Slack Workspaces and Microsoft Teams Channels:
    - **Slack Block Kit & MS Teams Adaptive Cards**: `SlackWebhookProvider` formats security events into **Slack Block Kit** JSON with severity color indicators (`#DC2626` for CRITICAL, `#F97316` for HIGH); `TeamsWebhookProvider` formats security events into **Microsoft Teams Adaptive Cards** (`MessageCard` schema).
    - **Resilient & Non-Blocking Dispatching**: `NotificationService` dispatches alert webhooks asynchronously without blocking scan execution, vulnerability processing, or compliance workflows. External HTTP errors or timeouts are logged cleanly without causing application failure.
    - **Secret Token Encryption & URL Masking**: Incoming Webhook URLs are encrypted at rest using AES-256-GCM / Fernet (`SecretEncryptionService`) and masked in all API responses (`https://hooks.slack.com/services/T00/B00/*****XXXX`).
    - **REST API Router (`/api/v1/notifications`) & Granular RBAC**: REST endpoints backed by `notifications:read` (`Role.VIEWER` level 10+), `notifications:create` and `notifications:update` (`Role.SECURITY_ANALYST` level 20+), and `notifications:manage` (`Role.ADMIN` level 30+). Dispatches audit log events (`notification.channel_created`, `notification.channel_updated`, `notification.channel_deleted`, `notification.sent`, `notification.failed`) via `AuditLogService`.
    - **Next.js Notification Control Plane**: Notification dashboard (`/notifications`), workspace (`/notifications/settings`), `NotificationsService`, `NotificationChannelCard`, `WebhookConfigurationModal`, `NotificationRuleEditor`, `NotificationHistoryPanel`, `TestNotificationButton`, and sidebar navigation integration.
38. **CI/CD Pipeline Scanning CLI Tool & Build Security Gate Architecture (Phase 9.3)**: Independent distributable Python CLI tool and CI/CD integration suite for software delivery pipelines:
    - **Independent Distributable CLI Package (`vulnova-cli`)**: Python CLI package (`cli/vulnova_cli.py`, `pyproject.toml`) providing `vulnova auth login`, `vulnova project register`, `vulnova scan start`, `vulnova scan status`, `vulnova findings summary`, `vulnova gate check`, `vulnova report export`. Features zero DB/frontend dependencies, `--json` machine-readable output mode, and `--quiet` CI runner mode.
    - **CI/CD Integration Templates**: Ready-to-use templates for `.github/workflows/vulnova-security-scan.yml`, `.gitlab-ci.yml`, and `Jenkinsfile`.
    - **Build Security Gate Evaluation**: Evaluates build security gate thresholds (`max_critical`, `max_high`, `max_medium`) returning standard CI exit codes (`0` = Pass, `1` = Gate Failure, `2` = Error).
    - **REST API Router (`/api/v1/cli`) & Granular RBAC**: REST endpoints backed by `cli:read` (`Role.VIEWER` level 10+), `cli:trigger` (`Role.SECURITY_ANALYST` level 20+), and `cli:manage` (`Role.ADMIN` level 30+). Dispatches audit events (`cli.token_created`, `cli.token_revoked`, `cli.scan_started`, `cli.scan_completed`, `cli.pipeline_failed`) via `AuditLogService`.
    - **Next.js CI/CD Workspace**: Dashboard `/integrations/ci-cd`, `CLIService`, `CLIIntegrationCard`, `TokenManagementPanel`, `PipelineExampleViewer`, and `ScanGateConfiguration`.
39. **OWASP Top 10 (2021) Security Validation Suite Architecture (Phase 10.1)**: Automated in-memory security validation framework verifying tenant application posture and active platform security controls against all 10 OWASP Top 10 (2021) categories (A01 - A10):
    - **Zero Database Table Duplication & In-Memory Execution**: Operates with **zero new database tables** and **zero schema migrations**. `OWASPValidationRunnerService` evaluates category assertions dynamically against authoritative PostgreSQL repositories (`security_findings`, `evidence_artifacts`, `assessment_jobs`, `api_keys`, `AuditLogService`).
    - **Ephemeral Audit Correlation (`suite_id`)**: Generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log events (`validation.owasp_suite_started`, `validation.owasp_suite_completed`) for cross-system SIEM correlation matching Era 8 compliance design patterns.
    - **Explainable Failure Diagnostics**: Every category result returns explicit diagnostic feedback: `failure_reason`, target `affected_subsystem` (e.g. `SecretEncryptionService`, `SSRFValidator`, `RBACPolicy`), and actionable `remediation_guidance`.
    - **Deep SSRF Egress Firewall Verification**: Direct integration with `is_safe_target_url` verifying private IP range blocking (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`, AWS IMDS `169.254.169.254`) and DNS rebinding protections.
    - **REST API Router (`/api/v1/validation/owasp-top-10`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js OWASP Validation Workspace**: Dashboard `/validation/owasp`, `OWASPValidationService`, `OWASPPassRateCard` (pass rate gauge & health status badge), `OWASPCategoryGrid` (interactive grid for A01 - A10), `OWASPValidationRunButton` (automated suite trigger button), `OWASPTestDetailsModal` (slide-in detail view), and sidebar navigation integration.
40. **OWASP API Security Top 10 (2023) Validation Suite Architecture (Phase 10.2)**: Automated in-memory API security assertion framework verifying tenant REST API routes and active platform security controls against all 10 OWASP API Security Top 10 (2023) categories (API1 BOLA through API10 Unsafe API Consumption):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `APISecurityValidationRunnerService` evaluates API category assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.api_security_suite_started`, `validation.api_security_suite_completed`).
    - **Explainable API Failure Diagnostics**: Every API category result returns diagnostic `failure_reason`, target `affected_endpoint` (e.g. `/api/v1/vulnerabilities/{id}`), `affected_subsystem` (e.g. `OrganizationIsolation`, `RateLimiter`), and actionable `remediation_guidance`.
    - **Deep BOLA & Security Control Verification**: Verifies BOLA tenant boundaries (`organization_id`), JWT expiration enforcement, API key prefix rules (`vn_live_`, `vn_cli_`), rate limiting (`RateLimiter`), CORS/headers, and third-party integration payload sanitization.
    - **REST API Router (`/api/v1/validation/api-security`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js API Security Workspace**: Dashboard `/validation/api-security`, `APISecurityValidationService`, `APIValidationPassRateCard`, `APIValidationCategoryGrid`, `APIValidationRunButton`, `APITestDetailsModal`, and sidebar navigation integration.
41. **Security Configuration & Infrastructure Validation Suite Architecture (Phase 10.3)**: Automated in-memory infrastructure security assertion framework verifying tenant deployment posture, container security, supply chain lockfiles, CI/CD pipelines, database security, logging, RBAC access controls, network SSRF firewalls, cloud metadata, and operational security readiness across all 10 Infrastructure Security categories (INFRA1 - INFRA10):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `InfrastructureSecurityValidationRunnerService` evaluates infrastructure category assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.infrastructure_suite_started`, `validation.infrastructure_suite_completed`).
    - **Explainable Infrastructure Failure Diagnostics**: Every infrastructure category result returns diagnostic `failure_reason`, target `affected_component` (e.g. `Dockerfile & Docker Compose Runtime`, `Dependency Lockfiles`), and actionable `remediation_guidance`.
    - **Deep Container, Supply Chain & Cloud Control Verification**: Verifies non-root container execution (`USER appuser`), supply chain lockfiles (`pyproject.toml`, `package-lock.json`), CI/CD pipeline gate enforcement, database connection encryption, `AuditLogService` & alert webhooks (Slack/Teams), and AWS IMDS cloud metadata blocking.
    - **REST API Router (`/api/v1/validation/infrastructure`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js Infrastructure Workspace**: Dashboard `/validation/infrastructure`, `InfrastructureValidationService`, `InfrastructurePassRateCard`, `InfrastructureCategoryGrid`, `InfrastructureValidationRunButton`, `InfrastructureTestDetailsModal`, and sidebar navigation integration.
42. **Platform Penetration Testing & Exploit Verification Suite Architecture (Phase 10.4)**: Automated in-memory penetration test assertion framework executing active exploit verification scenarios simulating real-world attack vectors against platform API Gateway, Auth, Multi-Tenant Boundaries, Injections, SSRF Egress, Mass Assignment, Rate Limits, CORS, Error Leakages, and Webhooks across all 10 PenTest categories (PEN1 - PEN10):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `PenTestValidationRunnerService` evaluates exploit category assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.pentest_suite_started`, `validation.pentest_suite_completed`).
    - **Explainable Exploit Diagnostics**: Every PenTest category result returns diagnostic `failure_reason`, target `affected_target` (e.g. `/api/v1/auth/login`, `/api/v1/vulnerabilities/{id}`), and actionable `remediation_guidance`.
    - **Deep Exploit Vector Verification**: Verifies JWT signature tampering rejection, multi-tenant IDOR boundaries (`organization_id`), SQL/Command injection protection, AWS IMDS metadata exfiltration blocking (`is_safe_target_url`), rate limit DoS protection (`RateLimiter`), CORS origin whitelisting, production stack trace suppression, and webhook HMAC signature verification.
    - **REST API Router (`/api/v1/validation/pentest`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js PenTest Workspace**: Dashboard `/validation/pentest`, `PenTestValidationService`, `PenTestPassRateCard`, `PenTestCategoryGrid`, `PenTestValidationRunButton`, `PenTestDetailsModal`, and sidebar navigation integration.
43. **Dependency Security Audit & SCA Enforcement Suite Architecture (Phase 10.5)**: Automated in-memory Software Composition Analysis framework verifying tenant third-party dependencies, lockfile integrity, outdated packages, CI/CD pipeline gates (`pip-audit`, `npm audit`), open-source license compliance, typosquatting, transitive tree depth, version pinning guards, DB drivers, and 30-day CVE remediation SLAs across all 10 SCA categories (SCA1 - SCA10):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `SCAValidationRunnerService` evaluates SCA category assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.sca_suite_started`, `validation.sca_suite_completed`).
    - **Explainable SCA Diagnostics**: Every SCA category result returns diagnostic `failure_reason`, target `affected_package` (e.g. `PyPI & NPM Dependencies`, `Dependency Lockfiles`), and actionable `remediation_guidance`.
    - **Deep Supply Chain & License Verification**: Verifies lockfile cryptographic hash pins (`pyproject.toml`, `package-lock.json`), CI/CD `pip-audit`/`npm audit` gate rules, open-source license compliance (MIT, Apache, GPL), typosquatting detection, strict version pinning syntax (`==`), and database driver security (asyncpg, psycopg).
    - **REST API Router (`/api/v1/validation/sca`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js SCA Workspace**: Dashboard `/validation/sca`, `SCAValidationService`, `SCAPassRateCard`, `SCACategoryGrid`, `SCAValidationRunButton`, `SCADetailsModal`, and sidebar navigation integration.
44. **Container Image Security Audit & Runtime Hardening Suite Architecture (Phase 10.6)**: Automated in-memory container security assertion framework evaluating base image OS package CVEs (Trivy), unprivileged non-root execution (`USER appuser`), minimal distroless footprints, Linux capability drops (`cap_drop: [ALL]`), `HEALTHCHECK` directives, secret exposure in layers, cgroup resource throttling, custom bridge network isolation (`vulnova-network`), Seccomp profiles, and SHA-256 image digest pinning across all 10 Container categories (CONTAINER1 - CONTAINER10):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `ContainerValidationRunnerService` evaluates container category assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.container_suite_started`, `validation.container_suite_completed`).
    - **Explainable Container Diagnostics & Controlled Warnings**: Every Container category result returns diagnostic `failure_reason`, target `affected_container` (e.g. `Dockerfile & Docker Compose Runtime User`, `Seccomp & AppArmor Security Profiles`), and actionable `remediation_guidance`. Emits controlled `WARNING` status if binary scanner tools are absent.
    - **Deep Container Hardening Verification**: Verifies unprivileged execution (`USER appuser`), Linux capability dropping (`cap_drop: [ALL]`), `no-new-privileges` flag, cgroup CPU/memory limits (`memory: 1g`), `/health` probes, and SHA-256 image digest pinning.
    - **REST API Router (`/api/v1/validation/container`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js Container Workspace**: Dashboard `/validation/container`, `ContainerValidationService`, `ContainerPassRateCard`, `ContainerCategoryGrid`, `ContainerValidationRunButton`, `ContainerDetailsModal`, and sidebar navigation integration.
45. **Secrets & Cryptographic Management Audit Suite Architecture (Phase 10.7)**: Automated in-memory secrets and cryptographic verification framework evaluating Gitleaks hardcoded secret scanning (with controlled warning status when Gitleaks binary is uninstalled), AES-256-GCM authenticated envelope encryption (`CryptoService`), JWT signing key entropy (min 256-bit entropy), machine-to-machine SHA-256 API key hashing & constant-time `hmac.compare_digest` verification, webhook HMAC-SHA256 signatures (`X-Vulnova-Signature`), TLS 1.2/1.3 in-transit encryption standards, secret key rotation policies & versioning metadata (without inventing fake rotation history), Argon2id/bcrypt password hashing work factors, CI/CD pipeline secret masking, and 90-day secrets governance SLAs across all 10 Secrets categories (SECRET1 - SECRET10):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `SecretsValidationRunnerService` evaluates secrets category assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.secrets_suite_started`, `validation.secrets_suite_completed`).
    - **Explainable Secrets Diagnostics & Controlled Warnings**: Every Secrets category result returns diagnostic `failure_reason`, target `affected_secret` (e.g. `Database Sensitive Field Encryption (CryptoService AES-256-GCM)`, `JWT Auth Signing Key & Algorithm Enforcement`), and actionable `remediation_guidance`. Emits controlled `WARNING` status if Gitleaks binary scanner is uninstalled and validates rotation policy metadata without fake historical records.
    - **Deep Cryptographic Verification**: Verifies AES-256-GCM envelope encryption, SHA-256 API key digests, HMAC-SHA256 webhook signatures, TLS 1.2/1.3 transport standards, and key rotation policy metadata.
    - **REST API Router (`/api/v1/validation/secrets`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js Secrets Workspace**: Dashboard `/validation/secrets`, `SecretsValidationService`, `SecretsPassRateCard`, `SecretsCategoryGrid`, `SecretsValidationRunButton`, `SecretsDetailsModal`, and sidebar navigation integration.
46. **Threat Model Review & STRIDE Verification Suite Architecture (Phase 10.8)**: Automated in-memory threat model verification framework evaluating all 6 Microsoft STRIDE threat categories: Spoofing (JWT identity validation, API key SHA-256 hashing & `vn_live_` prefixes), Tampering (Pydantic payload schema sanitization, SQL ORM parameterization, webhook HMAC-SHA256 signatures), Repudiation (mandatory `AuditLogService` event tracking), Information Disclosure (multi-tenant `organization_id` boundary isolation, AES-256-GCM field encryption, production stack trace masking, SSRF egress blocking), Denial of Service (Redis-backed `RateLimiter`, Celery worker concurrency limits), and Elevation of Privilege (RBAC role hierarchy `VIEWER` < `ANALYST` < `ADMIN`, IDOR prevention, container sandbox `cap_drop: [ALL]` & `USER appuser`) across all 10 STRIDE categories (STRIDE1 - STRIDE10):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `ThreatValidationRunnerService` evaluates STRIDE category assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.threat_suite_started`, `validation.threat_suite_completed`).
    - **Explainable Threat Diagnostics**: Every STRIDE category result returns diagnostic `failure_reason`, target `affected_component` (e.g. `User JWT Bearer Authentication & Token Expiration`, `Multi-Tenant Database Queries (organization_id Scope)`), and actionable `remediation_guidance`.
    - **Deep Architectural STRIDE Verification**: Verifies identity authentication guards, API key hashing, input sanitization, webhook signatures, audit event tracking, multi-tenant boundaries, field encryption & SSRF egress blocking, Redis rate limiting, RBAC permission hierarchy, and container sandbox capability dropping.
    - **REST API Router (`/api/v1/validation/threat`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js Threat Workspace**: Dashboard `/validation/threat`, `ThreatValidationService`, `ThreatPassRateCard`, `ThreatCategoryGrid`, `ThreatValidationRunButton`, `ThreatDetailsModal`, and sidebar navigation integration.
47. **Automated Security Regression Testing Framework Architecture (Phase 10.9)**: Automated in-memory security regression engine evaluating all 10 Security Regression categories: REGRESSION1 (OWASP Web Top 10), REGRESSION2 (OWASP API Security Top 10), REGRESSION3 (Security Config & Infrastructure), REGRESSION4 (Penetration Exploits), REGRESSION5 (SCA Supply Chain), REGRESSION6 (Container Hardening), REGRESSION7 (Secrets & Cryptography), REGRESSION8 (STRIDE Threat Model), REGRESSION9 (RBAC Hierarchy & Privilege Escalation), and REGRESSION10 (Audit Logging Non-Repudiation):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `RegressionValidationRunnerService` evaluates security regression assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.regression_suite_started`, `validation.regression_suite_completed`).
    - **Explainable Regression Diagnostics**: Every category result returns diagnostic `failure_reason`, target `affected_component` (e.g. `FastAPI Web Routers & Middleware`, `AuditLogService Mandatory Event Dispatcher`), and actionable `remediation_guidance`.
    - **Continuous Protection Matrix**: Verifies zero active SQLi/XSS/SSRF/RCE regressions, BOLA/BFLA guards, header hardening, pentest exploit re-execution blocking, supply chain lockfile hash integrity, container capability dropping, secret entropy, tenant isolation boundaries, RBAC decorators, and non-repudiation audit tracking.
    - **REST API Router (`/api/v1/validation/regression`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js Security Regression Workspace**: Dashboard `/validation/regression`, `RegressionValidationService`, `RegressionPassRateCard`, `RegressionCategoryGrid`, `RegressionValidationRunButton`, `RegressionDetailsModal`, and sidebar navigation integration.
48. **Security Control Plane Final Certification & Compliance Readiness Suite Architecture (Phase 10.10)**: Automated in-memory security control plane final certification engine evaluating all 10 Security Control Plane domains completed during Era 10: CERTIFICATION1 (OWASP Web & API Top 10 Security Control Plane Certification), CERTIFICATION2 (Infrastructure & Configuration Certification), CERTIFICATION3 (Penetration Testing Readiness Certification), CERTIFICATION4 (Dependency & SCA Supply Chain Certification), CERTIFICATION5 (Container Security Certification), CERTIFICATION6 (Secrets & Cryptographic Certification), CERTIFICATION7 (Threat Model & STRIDE Certification), CERTIFICATION8 (Security Regression Certification), CERTIFICATION9 (Governance & Access Control Certification), and CERTIFICATION10 (Enterprise Compliance Readiness Certification):
    - **Zero Database Table Duplication & Ephemeral Audit Correlation**: Operates with **zero new database tables** and **zero schema migrations**. `CertificationValidationRunnerService` evaluates security certification assertions dynamically in memory and generates a runtime `uuid4()` token string (`suite_id`) recorded in audit events (`validation.certification_suite_started`, `validation.certification_suite_completed`).
    - **Explainable Certification Diagnostics**: Every category result returns diagnostic `failure_reason`, target `affected_control` (e.g. `OWASP Web Top 10 & API Security Top 10 Validation Engines`, `CryptoService AES-256-GCM Envelope Encryption & SHA-256 Key Hashing`), and actionable `remediation_guidance`.
    - **Comprehensive Control Plane Assertion Matrix**: Evaluates OWASP Web/API engines, infrastructure header hardening, pentest exploit readiness, SCA supply chain lockfile cryptographic pins, container unprivileged execution & capability drops, secret scanning entropy, STRIDE threat mitigations, regression guards, RBAC hierarchy, and enterprise compliance readiness score.
    - **REST API Router (`/api/v1/validation/certification`) & Granular RBAC**: REST endpoints backed by `validation:read` (`Role.VIEWER` level 10+) and `validation:execute` (`Role.SECURITY_ANALYST` level 20+): `POST /run`, `GET /results`, `GET /summary`.
    - **Next.js Security Certification Workspace**: Dashboard `/validation/certification`, `CertificationValidationService`, `CertificationScoreCard`, `CertificationCategoryGrid`, `CertificationValidationRunButton`, `CertificationDetailsModal`, and sidebar navigation integration.
49. **Multi-Factor Authentication (MFA / TOTP) System Architecture (Phase 10.11)**: Enterprise TOTP two-factor authentication system (`MFAService`) supporting RFC 6238 time-based passcodes, Base64 QR code rendering, AES-256-GCM secret encryption, SHA-256 hashed single-use recovery codes, two-stage login challenge verification, and audit trail logging:
    - **RFC 6238 TOTP Engine**: `TOTPService` (`pyotp`) generating standard Base32 secrets, `otpauth://` provisioning URIs, and Base64 PNG QR code rendering (`qrcode`) compatible with Google Authenticator, Microsoft Authenticator, Authy, and 1Password.
    - **AES-256-GCM Encrypted Storage & SHA-256 Recovery Codes**: Stored TOTP secrets are encrypted using `CryptoService` AES-256-GCM envelope encryption before persistence in `users.mfa_secret`. Emergency recovery codes ('A1B2-C3D4-E5') are hashed using SHA-256 before storage in `users.mfa_backup_codes`.
    - **Two-Stage Authentication Flow**: Primary password authentication returns an ephemeral signed JWT `mfa_login_token` (5 min expiration) when MFA is enabled, requiring secondary OTP verification via `POST /api/v1/auth/mfa/challenge` before session tokens are issued.
    - **REST API Router (`/api/v1/auth/mfa`)**: `POST /setup`, `POST /verify-setup`, `POST /disable`, `POST /challenge`, `POST /recovery-codes/regenerate`, `GET /status`.
    - **Next.js MFA Workspace**: Workspace `/security/mfa`, `MFAService`, `QRCodeDisplay`, `OTPVerificationForm`, `RecoveryCodesModal`, `MFAStatusCard`, `MFASetupWizard`, and sidebar navigation integration under Settings.
50. **Database Performance Optimization & Index Tuning Architecture (Phase 11.1)**: Enterprise PostgreSQL query optimization layer (`QueryAnalyzerService`, `DatabaseBenchmarkService`, `DatabaseQueryMonitor`), composite index strategy (`0004_add_performance_indexes.py`), and SQLAlchemy connection pool tuning:
    - **Production Connection Pooling**: Configured `pool_size=20`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=1800`, `pool_pre_ping=True` preventing connection starvation under high concurrency.
    - **Composite Indexing**: Alembic migration `0004_add_performance_indexes.py` adding composite indexes on `users` (`organization_id`, `role`), `users` (`organization_id`, `is_active`), `audit_logs` (`organization_id`, `action`), `audit_logs` (`organization_id`, `created_at`), `refresh_tokens` (`user_id`, `is_revoked`), and `api_keys` (`organization_id`, `is_active`).
    - **Query Analyzer & Slow Query Monitoring**: `QueryAnalyzerService` analyzing execution patterns and generating index recommendations. `DatabaseQueryMonitor` attaching SQLAlchemy cursor event listeners to capture queries > 100ms.
    - **Controlled Query Benchmarking**: `DatabaseBenchmarkService` running batch query latency profiling (avg, p95, p99).
    - **REST API Router & Frontend Workspace**: REST endpoints `/api/v1/database/performance/*` (`/health`, `/benchmark`, `/slow-queries`) and Next.js Workspace `/database/performance` with `DatabasePerformanceCard`, `QueryBenchmarkTable`, and `DatabaseHealthBadge`.
51. **Redis Caching & Distributed Rate Limiting System Architecture (Phase 11.2)**: Enterprise Redis caching infrastructure (`RedisClientManager`, `CacheService`, `MultiLayerCacheManager`) and distributed token-bucket rate limiter (`DistributedRateLimiter`, `RateLimitMiddleware`):
    - **Graceful Degradation Connection Management**: `RedisClientManager` managing async connection pooling with fallback in-memory dictionary store if Redis becomes unreachable.
    - **Multi-Layer Cache Strategy**: Multi-tier caching for tenant metadata (`tenant:{org_id}`, 15 min TTL), user session data (`session:{user_id}`, 30 min TTL), and static policies (`config:{key}`, 1 hr TTL) with automated invalidation hooks.
    - **Distributed Token Bucket Rate Limiting**: `DistributedRateLimiter` implementing atomic Redis sliding window token buckets per IP, per User, and per Organization (100 req/min anonymous, 1000 req/min user, 5000 req/min admin).
    - **API Gateway Rate Limit Middleware**: `RateLimitMiddleware` rejecting rate-exceeded requests with HTTP 429 Too Many Requests and injecting `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.
    - **Locust Load Test Suite**: `testing/load/locustfile.py` load test scenario targeting 2000+ requests/sec system throughput verification.
52. **Centralized Observability, Telemetry & Distributed Monitoring Architecture (Phase 11.3)**: Enterprise observability stack (`StructuredLoggingService`, `MetricsCollector`, `TracingService`, `RequestTracingMiddleware`, `SystemHealthRouter`) integrated with Prometheus and Grafana:
    - **Structured JSON Logging & Sensitive Data Redaction**: `StructuredLoggingService` emitting JSON log events enriched with `X-Request-ID`, `X-Correlation-ID`, `user_id`, and `organization_id` while automatically redacting sensitive credentials via `mask_sensitive_data()`.
    - **Request Tracing Middleware**: `RequestTracingMiddleware` generating/propagating tracing context and setting response headers `X-Request-ID` and `X-Correlation-ID`.
    - **Prometheus Metrics Collector**: `MetricsCollector` tracking real-time HTTP throughput, query latency, database pool connections, Redis availability, and security event counters exposed at `GET /metrics`.
    - **OpenTelemetry Distributed Tracing**: `TracingService` providing OpenTelemetry span context wrappers (`trace_db_query`, `trace_redis_op`) compatible with OTLP / Jaeger collectors.
    - **Kubernetes Health Probes**: System router (`/api/v1/system/*`) exposing `/health` (summary), `/readiness` (503 if DB offline), and `/liveness` (200 OK process ping).
    - **Docker Monitoring Stack**: Integrated Prometheus (`prom/prometheus:v2.50.0`) and Grafana (`grafana/grafana:10.3.0`) services with pre-configured dashboards (`api_performance.json`, `database_performance.json`, `security_audit.json`).




















