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
| **Era 2** | Core Platform & Tenant Management System | 🟡 **IN PROGRESS** (Phase 2.1 ✅, Phase 2.2 ✅, Phase 2.3 ✅, Phase 2.4 ✅) | Sprint 2 |
| **Era 3** | Discovery Engine & Asset Surface Mapping | ⏳ Pending | Sprint 3 |
| **Era 4** | Vulnerability Assessment Engine & Dynamic Testing | ⏳ Pending | Sprint 4 |
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
