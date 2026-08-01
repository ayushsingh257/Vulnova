# Vulnova — Era 2 Architecture Specification & Implementation Plan
## Core Platform & Tenant Management System (Phases 2.1 – 2.6)

**Document**: `ERA_2_ARCHITECTURE_PLAN.md`  
**Author**: Antigravity AI  
**Status**: 🟡 PROPOSED — AWAITING USER APPROVAL  
**Target Version**: Era 2 (Sprints 2.1 – 2.6)

---

## 1. Analysis of Existing Era 1 Foundation

Before introducing domain entities and business logic in Era 2, we analyze how Era 1 architectural components provide the foundation:

### 1.1 Clean Architecture Boundaries (`backend/app/`)
- **`domain/`**: Contains core domain entities, value objects, and repository interfaces. Must remain completely decoupled from FastAPI, SQLAlchemy, or external drivers.
- **`application/`**: Contains use cases, DTOs, and application orchestration services (e.g., `RegisterUserUseCase`, `AuthenticateUserUseCase`). Calls domain repositories via interfaces.
- **`infrastructure/`**: Implements persistence via SQLAlchemy 2.0 Async models, Alembic migrations, Redis client, and security adapters (Argon2id, PyJWT).
- **`api/v1/`**: FastAPI routers, request/response Pydantic schemas, dependency injectors (`get_current_user`, `require_permission`), and HTTP status mapping.

### 1.2 Database Foundation
- **SQLAlchemy 2.0 Async Engine**: `app/infrastructure/database/session.py` provides `AsyncEngine` and `async_sessionmaker[AsyncSession]`. All DB access MUST remain 100% async (`await session.execute(...)`).
- **Alembic Migration Engine**: Async `alembic/env.py` configured for auto-generating revisions from declarative base metadata. Initial migration `0001_enable_postgresql_extensions.py` (`uuid-ossp`, `pgvector`) is applied.

### 1.3 Security & Observability Foundation
- **Settings Management**: Pydantic `BaseSettings` (`app/core/config.py`) loading `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REDIS_URL`, `DATABASE_URL`.
- **Traceability & Correlation**: `RequestIDMiddleware` auto-generates `X-Request-ID` and binds it to `structlog.contextvars` and Python `contextvars` (`app/core/correlation.py`).
- **Exception Hierarchy**: Base `VulnovaException` with `ResourceNotFoundException`, `UnauthorizedException`, `ForbiddenException`, `ValidationException` mapped to standardized JSON responses with correlation IDs.

---

## 2. Era 2 Architectural Specification

Era 2 establishes multi-tenancy, user management, authentication, role-based access control (RBAC), API key management, and security audit logging.

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                 API Gateway / Router                              │
│         (/api/v1/auth, /api/v1/organizations, /api/v1/users, /api/v1/api-keys)  │
└─────────────────────────┬─────────────────────────────────┬───────────────────────┘
                          │                                 │
                          ▼                                 ▼
┌──────────────────────────────────────────┐  ┌───────────────────────────────────┐
│        Authentication Middleware         │  │     RBAC Permission Injector      │
│  (JWT Access Token / X-API-Key Validator)│  │   (Owner, Admin, Analyst, Viewer) │
└─────────────────────────┬────────────────┘  └─────────────────┬─────────────────┘
                          │                                     │
                          ▼                                     ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                Application Use Cases                              │
│    (RegisterOrg, AuthenticateUser, RotateTokens, ManageKeys, AuditSecurityEvent) │
└─────────────────────────┬─────────────────────────────────┬───────────────────────┘
                          │                                 │
                          ▼                                 ▼
┌──────────────────────────────────────────┐  ┌───────────────────────────────────┐
│        Domain Entities & Interfaces      │  │    Security Adapters & Crypto     │
│   (Organization, User, APIKey, AuditLog) │  │  (Argon2id Hashing, PyJWT Engine) │
└─────────────────────────┬────────────────┘  └───────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           Infrastructure Persistence Layer                        │
│             (SQLAlchemy 2.0 Async ORM Models & Alembic Migrations)                │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Models & Entity Relationship Design

### 3.1 Entity Relationship Diagram (ERD)

```
  ┌──────────────────────────┐         1:N         ┌──────────────────────────┐
  │      organizations       │────────────────────►│          users           │
  │──────────────────────────│                     │──────────────────────────│
  │ id: UUID (PK)            │                     │ id: UUID (PK)            │
  │ name: VARCHAR(255)       │                     │ organization_id: UUID(FK)│
  │ slug: VARCHAR(255) (UQ)  │                     │ email: VARCHAR(255) (UQ) │
  │ plan_tier: VARCHAR(50)   │                     │ password_hash: VARCHAR   │
  │ is_active: BOOLEAN       │                     │ full_name: VARCHAR(255)  │
  │ created_at: TIMESTAMPTZ  │                     │ role: VARCHAR(50)        │
  │ updated_at: TIMESTAMPTZ  │                     │ is_active: BOOLEAN       │
  └─────────────┬────────────┘                     │ is_mfa_enabled: BOOLEAN  │
                │                                  │ mfa_secret: VARCHAR      │
                │ 1:N                              │ last_login_at: TIMESTAMPTZ│
                │                                  └────────────┬─────────────┘
                ├────────────────────────┐                      │
                │                        │                      │
                ▼                        ▼                      ▼
  ┌──────────────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐
  │         api_keys         │ │  refresh_tokens  │ │        audit_logs        │
  │──────────────────────────│ │──────────────────│ │──────────────────────────│
  │ id: UUID (PK)            │ │ id: UUID (PK)    │ │ id: UUID (PK)            │
  │ organization_id: UUID(FK)│ │ user_id: UUID(FK)│ │ organization_id: UUID(FK)│
  │ user_id: UUID (FK)       │ │ token_hash: VAR  │ │ actor_user_id: UUID (FK) │
  │ name: VARCHAR(255)       │ │ family_id: UUID  │ │ action: VARCHAR(100)     │
  │ key_prefix: VARCHAR(8)   │ │ is_revoked: BOOL │ │ resource_type: VAR(100)  │
  │ key_hash: VARCHAR(255)   │ │ expires_at: TZ   │ │ resource_id: VARCHAR(255)│
  │ scopes: JSONB            │ │ created_at: TZ   │ │ client_ip: VARCHAR(45)   │
  │ expires_at: TIMESTAMPTZ  │ └──────────────────┘ │ user_agent: TEXT         │
  │ last_used_at: TIMESTAMPTZ│                      │ details: JSONB           │
  └──────────────────────────┘                      │ created_at: TIMESTAMPTZ  │
                                                    └──────────────────────────┘
```

### 3.2 Detailed DDL & Table Schemas

#### 1. `organizations`
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'ENTERPRISE_TRIAL',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_organizations_slug ON organizations(slug);
```

#### 2. `users`
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'SECURITY_ANALYST',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_org_id ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
```

#### 3. `refresh_tokens` (Family Rotation Engine)
```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(family_id);
```

#### 4. `api_keys`
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    scopes JSONB NOT NULL DEFAULT '["read", "write"]',
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_api_keys_org ON api_keys(organization_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
```

#### 5. `audit_logs`
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    client_ip VARCHAR(45),
    user_agent TEXT,
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_logs_org_action ON audit_logs(organization_id, action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
```

---

## 4. Security & Authentication Architecture

### 4.1 Password Hashing Strategy
- **Algorithm**: Argon2id (`argon2_type=argon2id`, `memory_cost=65536` [64MB], `time_cost=3`, `parallelism=4`) via `passlib[argon2]`.
- Mitigates GPU-accelerated brute-force attacks and side-channel timing analysis.

### 4.2 Token Dual-Rotation Architecture
- **Access Tokens**: Short-lived JWT (15-minute expiration).
  - Claims payload: `{ "sub": user_id, "org_id": org_id, "role": role, "type": "access", "exp": ts }`.
  - Signature: HMAC-SHA256 (`HS256`) using `JWT_SECRET`.
- **Refresh Tokens**: Long-lived secure UUID (7-day expiration).
  - Sent via HTTP-Only, Secure, `SameSite=Strict` cookie (`vulnova_refresh_token`).
  - Stored in `refresh_tokens` database table hashed using SHA-256.
  - **Token Family Reuse Detection**: If a previously revoked refresh token is presented, the entire token family (`family_id`) is instantly invalidated to mitigate token theft.

### 4.3 Multi-Tenant RBAC Authorization Matrix

| Permission Code | Owner | Admin | Security Analyst | Viewer |
|---|:---:|:---:|:---:|:---:|
| `org:update` | ✅ | ❌ | ❌ | ❌ |
| `org:delete` | ✅ | ❌ | ❌ | ❌ |
| `members:manage` | ✅ | ✅ | ❌ | ❌ |
| `api_keys:manage` | ✅ | ✅ | ❌ | ❌ |
| `scans:launch` | ✅ | ✅ | ✅ | ❌ |
| `scans:triage` | ✅ | ✅ | ✅ | ❌ |
| `reports:view` | ✅ | ✅ | ✅ | ✅ |

FastAPI Dependency Injectors:
```python
# Usage in API routers:
@router.post("/scans", dependencies=[Depends(require_permission("scans:launch"))])
async def launch_scan(...): ...
```

---

## 5. API Boundaries & Endpoint Design

All endpoints prefixed with `/api/v1`:

### 5.1 Auth Router (`/api/v1/auth`)
- `POST /auth/register` — Register owner & tenant organization.
- `POST /auth/login` — Authenticate credentials, issue access token & set refresh cookie.
- `POST /auth/refresh` — Rotate access/refresh token pair using active token family.
- `POST /auth/logout` — Revoke refresh token and clear auth cookies.
- `GET  /auth/me` — Retrieve current authenticated user & organization profile.

### 5.2 Organization & Member Management (`/api/v1/organizations`)
- `GET  /organizations/me` — Retrieve current organization settings & usage.
- `PATCH /organizations/me` — Update organization name/settings (Owner only).
- `GET  /organizations/me/members` — List tenant members.
- `POST /organizations/me/members` — Invite/add member (Owner/Admin).
- `DELETE /organizations/me/members/{user_id}` — Remove member (Owner/Admin).

### 5.3 API Key Router (`/api/v1/api-keys`)
- `GET  /api-keys` — List active API keys for organization.
- `POST /api-keys` — Provision new machine-to-machine API key.
- `DELETE /api-keys/{key_id}` — Revoke API key.

### 5.4 Audit Log Router (`/api/v1/audit-logs`)
- `GET  /audit-logs` — Query paginated organization security audit trail.

---

## 6. Implementation Phases (Era 2 Roadmap Breakdown)

| Sub-Phase | Focus Area | Key Deliverables |
|---|---|---|
| **Phase 2.1** | Database Entity Models & Alembic Migration | `models/user.py`, `organization.py`, `refresh_token.py`, `api_key.py`, `audit_log.py`, Alembic migration `0002_create_core_platform_tables.py` |
| **Phase 2.2** | JWT & OAuth2 Auth Framework | Password hasher (`Argon2id`), JWT provider, `/api/v1/auth` router (`register`, `login`, `refresh`, `logout`, `me`) |
| **Phase 2.3** | Multi-Tenant RBAC Security Layer | `app/security/rbac.py`, `require_permission` dependency injectors, tenant isolation unit test suite |
| **Phase 2.4** | API Key Management System | Key generator, SHA-256 prefix hashing, `X-API-Key` authentication middleware, `/api/v1/api-keys` router |
| **Phase 2.5** | User & Organization Management Endpoints | `/api/v1/organizations` router, member invitation flow, profile management |
| **Phase 2.6** | Security Audit Logging System | `AuditLoggerService`, async background audit logging, `/api/v1/audit-logs` query router |

---

## 7. Compliance Verification Checklist

Before starting implementation of any Phase in Era 2, the following rules will be strictly enforced:

- [ ] **No Synchronous DB Code**: 100% of SQLAlchemy operations use `AsyncSession` and `asyncpg`.
- [ ] **Clean Architecture Boundaries**: Domain models in `app/domain/` contain no FastAPI/SQLAlchemy imports.
- [ ] **Structured Logging**: All log statements use `structlog.get_logger(__name__)` with key-value arguments.
- [ ] **Traceability**: All log lines within HTTP requests automatically include `request_id`.
- [ ] **Deterministic Testing**: Every phase adds comprehensive unit/API tests (`pytest`).
- [ ] **GitHub Actions Gate**: No phase is marked complete until both `ci.yml` and `security.yml` pass green on GitHub.

---

## 🛑 Status

**Awaiting user review and approval before starting Phase 2.1 implementation.**
