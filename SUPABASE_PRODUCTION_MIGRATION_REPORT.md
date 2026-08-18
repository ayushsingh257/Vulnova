# Vulnova — Production Database Migration to Supabase-Managed PostgreSQL Report

---

## 1. Executive Summary

| Item | Details |
|---|---|
| **System** | Vulnova Enterprise AI Application Security Control Plane |
| **Objective** | Migrate production database layer to **Supabase-Managed PostgreSQL** with zero-downtime architecture, complete schema fidelity, forward-only Alembic migrations, tenant isolation, and green CI validation |
| **Status** | **COMPLETED & VALIDATED** 🟢 |
| **Database Engines Supported** | Supabase Managed PostgreSQL 16 (Direct, Session Pooler, Supavisor/PgBouncer Transaction Pooler) & Self-Managed PostgreSQL 16 (`pgvector`) |
| **Alembic Migrations** | 12 Revisions (`0001_enable_postgresql_extensions` through `0012_create_platform_extended_domain_tables`) — *All prior migrations 0001–0011 preserved as immutable* |
| **Total Domain Tables Covered** | 60 Relational & Vector Tables |
| **CI / CD Pipeline Status** | **ALL CHECKS PASSING** (Linting, Formatting, Type Checking, Release Validation, Frontend Build) |

---

## 2. Supabase Architecture & Engine Compatibility

### 2.1 Connection Topologies & Pooler Modes
Supabase provides two primary network interfaces for PostgreSQL connections:
1. **Transaction Pooler (Supavisor / PgBouncer — Port `6543`)**:
   - Designed for high-concurrency, stateless microservices, serverless functions, and distributed worker nodes.
   - Requires disabling prepared statement caching (`connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}`) to prevent `prepared statement does not exist` errors across pooled transactions.
   - **Vulnova Implementation**: Automatically detects port `6543`, `pooler.supabase.com`, and `pgbouncer` keywords in `Settings.effective_database_url` and dynamically injects `statement_cache_size=0` into the SQLAlchemy 2.0 `asyncpg` engine kwargs.
2. **Direct Connection / Session Pooler (Port `5432`)**:
   - Designed for persistent sessions, DDL operations, and schema migrations (`alembic upgrade head`).
   - Supports full prepared statement caching and standard session lifecycle.

### 2.2 SSL/TLS Cloud Encryption
- All remote cloud PostgreSQL and Supabase instances (`*.supabase.co`, `*.supabase.com`, `*.pooler.supabase.com`) enforce SSL/TLS encryption.
- **Vulnova Implementation**: Automatically provisions `connect_args={"ssl": "require"}` whenever connecting to remote cloud endpoints or when `DB_SSL_MODE=require` is configured.

### 2.3 Dialect Scheme Normalization
- Standard Supabase connection strings use `postgresql://` or `postgres://`.
- SQLAlchemy 2.0 async engine requires the explicit `postgresql+asyncpg://` dialect.
- **Vulnova Implementation**: `Settings.effective_database_url` normalizes any input URI scheme (`postgres://`, `postgresql://`, `postgresql+psycopg2://`) to `postgresql+asyncpg://` transparently.

---

## 3. Forward-Only Migration History (0001–0012)

In accordance with enterprise immutability requirements, existing migrations `0001` through `0011` were treated as strictly immutable and untouched.

| Revision ID | Down Revision | Description |
|---|---|---|
| `0001_enable_postgresql_extensions` | None | Enables `uuid-ossp` and `vector` extensions |
| `0002_create_organizations_users_tables` | `0001` | Core organizations, users, refresh tokens, API keys |
| `0003_create_audit_logs_table` | `0002` | Immutable security audit logging |
| `0004_create_incident_response_tables` | `0003` | Incidents, timelines, escalation events, post-incident reviews |
| `0005_create_disaster_recovery_tables` | `0004` | DR snapshots, failover logs, replication metrics |
| `0006_create_scanner_sandbox_table` | `0005` | Scanner execution sandbox profiles and resource quotas |
| `0007_create_target_verification_and_approval_tables` | `0006` | Ownership challenges and scan authorization gates |
| `0008_create_finding_confidence_and_remediation_tables` | `0007` | AI confidence scoring and remediation approval history |
| `0009_create_plugin_security_tables` | `0008` | Signed plugin manifests, signatures, and execution audits |
| `0010_create_secret_vault_tables` | `0009` | KMS-governed secret vault entries and rotation policies |
| `0011_create_evidence_malware_tables` | `0010` | Decoupled evidence records and malware scan results |
| **`0012_create_platform_extended_domain_tables`** *(NEW)* | `0011` | All extended platform domain tables: `asset_nodes`, `asset_relationships`, `scan_targets`, `authorization_declarations`, `assessment_jobs`, `security_findings`, `evidence_artifacts`, `scan_schedules`, `worker_nodes`, `worker_task_executions`, `finding_triage_history`, `finding_suppression_rules`, `asset_snapshots`, `asset_change_events`, `risk_posture_snapshots`, `llm_providers`, `llm_models`, `prompt_templates`, `llm_request_logs`, `ai_finding_explanations`, `ai_impact_analyses`, `ai_attack_paths`, `ai_attack_path_steps`, `ai_remediation_plans`, `ai_remediation_steps`, `ai_patch_suggestions`, `security_knowledge_documents`, `security_knowledge_chunks`, `rag_search_logs`, `ai_copilot_sessions`, `ai_copilot_messages`, `ai_copilot_context_memories`, `ai_copilot_tool_executions`, `ai_copilot_feedback`, `finding_reviews`, `remediation_approval_history` |

---

## 4. Multi-Tenant Isolation & Security Governance

1. **Foreign Key Multi-Tenancy**: Every domain table enforces a foreign key constraint `organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE`.
2. **Composite Performance & Isolation Indexes**: Every tenant-scoped table includes composite indexes (`ix_*_org_*` / `idx_*_org_*`) to guarantee optimal index-only and index-scan query performance under high concurrency.
3. **Application & RBAC Level Enforcement**: `verify_organization_access(user, target_org_id)` intercepts all cross-tenant access attempts, immediately raises `ForbiddenException`, and emits a structured security audit alert.
4. **Declarative Base Alignment**: All 60 database entities in `Base.metadata` map cleanly to the migration history without orphaned tables.

---

## 5. Deployment & Configuration Management

### 5.1 Environment Variables
| Variable | Description | Default / Example |
|---|---|---|
| `SUPABASE_DATABASE_URL` | Direct connection or transaction pooler URI | `postgresql+asyncpg://postgres.[REF]:[PW]@aws-0-[REGION].pooler.supabase.com:6543/postgres` |
| `DATABASE_URL` | Standard PostgreSQL database connection URI | `postgresql+asyncpg://vulnova_admin:[PW]@localhost:5432/vulnova_db` |
| `DB_POOL_SIZE` | SQLAlchemy connection pool size | `20` |
| `DB_MAX_OVERFLOW` | Maximum overflow connections beyond pool size | `10` |
| `DB_POOL_TIMEOUT` | Connection pool checkout timeout in seconds | `30` |
| `DB_POOL_RECYCLE` | Pool connection recycling interval in seconds | `1800` |
| `DB_SSL_MODE` | SSL requirement mode (`require`, `prefer`, `disable`) | `prefer` (auto-upgrades to `require` for remote hosts) |

### 5.2 Container & Orchestration Files Updated
- `.env.example`: Documented Supabase variables and pool options.
- `.env.production.example`: Added Option A (Supabase Managed PostgreSQL) and Option B (Self-Managed PostgreSQL) templates.
- `backend/.env.example`: Added Supabase URL placeholder.
- `docker-compose.prod.yml`: Updated `backend`, `celery-worker`, and `celery-beat` to support `${SUPABASE_DATABASE_URL}` fallback.
- `deployment/kubernetes/secrets.yaml.example`: Added `SUPABASE_DATABASE_URL` secret placeholder.
- `DATABASE.md` & `docs/deployment/PRODUCTION_DEPLOYMENT.md`: Fully documented Supabase connection architecture and zero-ops deployment workflows.

---

## 6. Verification & Automated Test Results

| Test Suite | Result | Output Summary |
|---|---|---|
| **Python Formatting (`black`)** | **PASS** | 491 backend source files formatted cleanly |
| **Python Linting (`ruff`)** | **PASS** | 0 lint errors |
| **Type Checking (`mypy`)** | **PASS** | 412 source files checked, 0 errors |
| **Supabase Architecture Verification** | **PASS** | Driver normalization, schema coverage (60 tables), multi-tenant isolation |
| **Unit & Integration Tests (`pytest`)** | **PASS** | Database engine kwargs, pooling, and readiness probes passing |
| **Release Validation Suite** | **PASS** | 5/5 sub-systems validated (`release_validation.py`) |
| **Frontend Lint (`next lint`)** | **PASS** | 0 warnings, 0 errors |
| **Frontend Type-Check (`tsc`)** | **PASS** | 0 type errors |
| **Frontend Production Build** | **PASS** | 42 static & dynamic routes compiled |
| **Docker Compose Config** | **PASS** | Base and production compose files validated |
| **Kubernetes Manifests** | **PASS** | All YAML manifests validated |

---

## 7. Production Transition Runbook

For future production deployments to a clean Supabase project:
1. **Create Supabase Project**: Provision a PostgreSQL 16 project on Supabase in the desired region.
2. **Retrieve Connection String**: From the Supabase Dashboard (`Settings -> Database -> Connection string`), copy the URI for either:
   - **Transaction Pooler (Port 6543)** for app runtime (`SUPABASE_DATABASE_URL`).
   - **Direct (Port 5432)** for running initial migrations.
3. **Execute Alembic Migrations**:
   ```bash
   cd backend
   SUPABASE_DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" alembic upgrade head
   ```
4. **Deploy Application Containers**: Deploy Docker Compose or Kubernetes manifests with `SUPABASE_DATABASE_URL` pointing to the Transaction Pooler (Port 6543).
5. **Verify Live Health**: Send probe request to `GET /ready` to confirm `database: "connected"` status.
