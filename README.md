# Vulnova — Enterprise AI Application Security Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)
[![Security: OWASP ASVS](https://img.shields.io/badge/Security-OWASP_ASVS_v4.0-crimson.svg)](SECURITY.md)
[![Architecture: Clean Architecture](https://img.shields.io/badge/Architecture-Clean%20%2F%20DDD-black.svg)](ARCHITECTURE.md)
[![Status: Era 7 Complete](https://img.shields.io/badge/Status-Era%207%20Complete-green.svg)](ROADMAP.md)

[![Build Status](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-brightgreen.svg)](.github/workflows/ci.yml)

**Vulnova** is a next-generation, AI-native Application Security (AppSec) platform engineered for enterprise security teams, DevSecOps practitioners, and security analysts. It unifies automated attack surface discovery, dynamic security assessments (DAST), API security inspection, and an autonomous AI Security Analyst to continuously identify, prioritize, and remediate application vulnerabilities.

---

## 🎯 1. What is Vulnova?

### Product Identity
Vulnova is built to serve as an **Enterprise Security Operations & Application Risk Control Plane**. It replaces fragmented legacy security tools with a unified, multi-tenant platform designed for high-concurrency vulnerability scanning, deep API inspection, and AI-assisted risk triaging.

### The Problem It Solves
Traditional Dynamic Application Security Testing (DAST) scanners suffer from fundamental challenges:
- **High False-Positive Noise**: Legacy scanners flood security teams with thousands of low-context alerts without business impact prioritization.
- **Single-Page & API Blind Spots**: Standard crawlers fail to parse modern JavaScript Single-Page Applications (SPAs) and dynamic REST/GraphQL API surfaces.
- **Siloed Multi-Tenancy & Governance**: Enterprise organizations lack unified tenant boundaries, granular role-based access controls (RBAC), and immutable audit logs.
- **Lack of Actionable Remediation**: Scanner reports output raw vulnerability descriptions rather than verified, framework-specific code patches.

### Mission & Vision
- **Mission**: Automate complex application security assessments using isolated execution sandboxes and autonomous AI intelligence, enabling engineering teams to fix vulnerabilities before production deployment.
- **Vision**: Define the enterprise standard for AI-native AppSec platforms where security testing, asset surface mapping, and code remediation operate in a continuous, automated loop.

---

## 👥 2. Who Should Use Vulnova?

| User Persona | Key Use Cases |
|---|---|
| 🛡️ **Application Security (AppSec) Teams** | Centralized vulnerability management, false-positive reduction, policy enforcement, and CISO executive reporting. |
| 💻 **Security Engineers** | Custom DAST plugin creation, automated scope declaration enforcement, and target vulnerability verification. |
| 🚀 **DevSecOps & Engineering Teams** | Automated CI/CD security pipeline gates, language-specific code patch generation, and API security testing. |
| 👁️ **SOC & Incident Response Teams** | Forensic security audit log analysis, client metadata attribution, and attack surface tracking. |
| 🏢 **Enterprise Organizations** | Multi-tenant organization isolation, RBAC role management (`OWNER`, `ADMIN`, `SECURITY_ANALYST`, `VIEWER`), and machine-to-machine API key integration. |
| 🔬 **Security Researchers** | Modular plugin testing, custom attack payload evaluation, and target asset surface mapping. |

---

## 🚀 3. Core Capabilities

### 🔐 Enterprise Identity & Access Management
- **Argon2id Password Security**: Memory-hard password hashing aligned with OWASP ASVS standards.
- **OAuth2 & JWT Framework**: Short-lived (15-minute) HS256 JWT access tokens paired with cryptographically secure 64-byte refresh tokens.
- **Refresh Token Rotation**: Family-based refresh token rotation (`family_id`) with automatic reuse detection that immediately revokes compromised sessions.
- **HTTP-Only Cookies**: Secure `vulnova_refresh_token` delivery via HTTP-Only, Secure, SameSite=Lax cookies.

### 🔑 Machine-to-Machine API Key Management
- **Secure Key Hashing**: Cryptographically random API keys using `vn_live_` prefixes (8-character identification) + SHA-256 hex digest storage (raw key returned once and unrecoverable).
- **Constant-Time Verification**: `hmac.compare_digest` constant-time verification preventing timing side-channel attacks.
- **Dual-Mode Authentication**: Universal FastAPI dependency (`get_current_user_or_api_key`) prioritizing Bearer JWT tokens with X-API-Key fallback.

### 🛡️ Multi-Tenant RBAC & Tenant Isolation
- **Hierarchical Role Model**: Four-tier integer-ordered role structure (`OWNER = 40 > ADMIN = 30 > SECURITY_ANALYST = 20 > VIEWER = 10`).
- **Centralized Permission Map**: Resource-action permissions (`organization:update`, `users:invite`, `api_keys:create`, `audit_logs:read`) enforced via `require_permission()` dependencies.
- **Strict Tenant Isolation**: `verify_organization_access()` and `require_same_organization` prevent cross-organization resource tampering with HTTP 403 `ForbiddenException` guards.

### 👥 User & Organization Lifecycle Management
- **Organization Settings & Billing Tier Control**: Profile management, subscription plan tracking, and member counting.
- **Team Invitations & Role Updates**: Granular team member creation, role modification with sole-owner protection, and account status toggling.
- **Administrative Safeguards**: Built-in protection preventing self-deactivation, self-deletion, and orphaned organization states.

### 📜 Security Auditability & Compliance
- **Immutable Security Audit Log**: Append-only `audit_logs` database table capturing administrative actions, authentication attempts, user lifecycle mutations, and API key revocations.
- **Client Context Extraction**: Captures `client_ip` (supporting `X-Forwarded-For` proxy headers) and `user_agent` strings.
- **Fail-Safe Audit Logging**: Async audit recording designed to log high-priority warnings without disrupting primary business transactions.

### 🔍 Enterprise Assessment Intelligence & Policy Engine
- **10 Production Security Assessment Plugins**: High-concurrency security plugins covering Web (SQLi, XSS, Security Headers, Cookie Auth Security), API (Exposed Docs, JWT Signatures & Claims, CORS Policies), and Infrastructure/Cloud (Open Administrative Ports, TLS/SSL Certs & Protocols, S3/Azure/GCP & IMDS Exposure).
- **CVSS v3.1/v4 Risk Intelligence Engine**: CVSS vector parsing, EPSS (Exploit Prediction Scoring System) probability mapping, asset criticality multipliers (1.5x, 1.2x, 1.0x, 0.8x), normalized 0.0–100.0 risk scoring, and SLA assignment (24h Critical, 72h High, 14d Medium, 30d Low).
- **Finding Deduplication Engine**: SHA-256 signature hashing (`organization_id`, `plugin_id`, `cwe_id`, `target_endpoint`, `parameter_name`) merging duplicate finding instances into primary canonical findings.
- **Multi-Modal Evidence Collection Engine**: Captures reproducible proof including masked HTTP request/response dumps, header/cookie profiles, Playwright HTML DOM snapshots, and visual PNG screenshots.
- **Provider-Independent Evidence Storage**: Async `EvidenceArtifactStorage` with SHA-256 content checksum verification and tenant-isolated storage paths.
- **Enterprise Scan Profile Engine**: 10 pre-configured profiles (`Quick Scan`, `Web Scan`, `API Scan`, `Infrastructure Scan`, `OWASP Top 10`, `OWASP API Top 10`, `Full Assessment`, `Authenticated Scan`, `Passive Scan`, `Custom Scan`) resolving plugin execution subsets via `PluginRegistry`.
- **Policy-Controlled Assessment Execution**: Centralized `ScanPolicyEngine` enforcing concurrency limits, RPS rate limits, `robots.txt` compliance, wildcard scope include/exclude rules, custom auth header/cookie injection, and emergency `stop_on_critical` termination triggers.
- **Authenticated Scan Support & Custom Scan Policies**: Per-scan overrides for authentication headers, session cookies, rate limits, and custom scope boundaries.
- **Multi-Source Finding Correlation Engine**: `AssessmentCorrelationEngine` links security findings to Asset Graph nodes (`AssetNode`) and aggregates composite risk scores without duplicating findings as graph nodes or causing node graph explosion.
- **Unified Asset Inventory & Posture Model**: Tenant-isolated asset inventory (`GET /api/v1/assets/inventory`, `GET /api/v1/assets/{asset_id}`) combining discovery targets, technology stack fingerprints (`RUNS_TECH`), security findings, and evidence artifacts into consolidated posture views.
- **Attack Surface Trend & Continuous Monitoring Engine**: `ContinuousMonitoringService` & `ChangeDetectionEngine` capture point-in-time posture snapshots (`AssetSnapshotModel`), track vulnerability finding lifecycle transitions (`NEW`, `ACTIVE`, `RESOLVED`, `REOPENED`), calculate historical risk score trajectory analytics (`GET /api/v1/assets/trends`), and record security posture event timelines (`GET /api/v1/security/posture/timeline`).
- **Enterprise Finding Triage & Vulnerability Lifecycle Engine**: Analyst triage workflows (`UNREVIEWED`, `CONFIRMED`, `FALSE_POSITIVE`, `RISK_ACCEPTED`, `REMEDIATED`, `REOPENED`), automated false-positive suppression rules (`EXACT_CWE`, `TARGET_PATTERN`, `PLUGIN_ID`, `COMPOSITE`), immutable triage audit trail history (`finding_triage_history`), and RBAC permission guards (`findings:triage`, `findings:suppress`).
- **Multi-Provider LLM Gateway & Prompt Orchestration (Phase 5.1)**: Provider-agnostic LLM gateway supporting OpenAI, Anthropic, Google Gemini, and local Ollama models with zero mandatory third-party SDK dependencies (uses `httpx` REST APIs), priority-based fallback routing, health cooldown tracking, AES-256-GCM secret encryption (`SecretEncryptionService`), immutable prompt template versioning (`PromptTemplateModel`), sensitive credential masking in prompt context (`mask_sensitive_prompt_context`), and token budget cost tracking (`GET /api/v1/ai/usage`).
- **AI Finding Explainer & Impact Analysis Engine (Phase 5.2)**: Autonomous AI Security Analyst capability consuming Era 4 normalized findings, evidence dumps, asset topology, and triage state to generate 8-field structured vulnerability explanations (`AIFindingExplainerService`) and enterprise impact analysis reports (`ImpactAnalysisService`). Features structured output JSON repair recovery strategies, append-only persistence (`ai_finding_explanations`, `ai_impact_analyses`), sensitive credential masking, and RBAC authorization guards (`findings:ai_explain`).
- **AI Attack Path Synthesis Engine (Phase 5.3)**: Graph-aware AI attack chain reasoning engine (`AIAttackPathService`) that synthesizes evidence-grounded attack scenarios, MITRE ATT&CK technique progressions (`T1190`, `T1059`, `T1068`, `T1021`, etc. validated against `KNOWN_MITRE_TECHNIQUES` registry), path-level confidence scoring (`confidence_score`), and SOC analyst review feedback loops (`PATCH /api/v1/ai/attack-paths/{id}/review`). Persists Option A normalized relational tables (`ai_attack_paths`, `ai_attack_path_steps`) with RBAC authorization guards (`findings:ai_attack_path`).
- **AI Remediation Engine & Fix Recommendation System (Phase 5.4)**: Autonomous AI remediation planning capability (`AIRemediationService`) that transforms findings, evidence dumps, asset graph topology, triage state, Phase 5.2 explanations/impact analysis, and Phase 5.3 attack paths into multi-tier fix recommendations and non-executable code/config patch diff suggestions (`PYTHON`, `JAVASCRIPT`, `GO`, `JAVA`, `NGINX`, `DOCKER`, `TERRAFORM`, `YAML`). Features a strict **Human Approval Safety Policy** (zero execution capability), 3-table normalized relational schema (`ai_remediation_plans`, `ai_remediation_steps`, `ai_patch_suggestions`), CVE/CWE/version mapping, dual confidence metrics (`ai_confidence_score`, `effectiveness_confidence_score`), operational risk flags (`requires_backup`, `requires_downtime`, `rollback_available`), review state workflows (`VALIDATION_FAILED`, `APPROVED`, `REJECTED`, `IMPLEMENTED`, `VERIFIED`), and RBAC authorization guards (`findings:ai_remediate`).
- **AI False Positive Filter & Finding Confidence Intelligence Engine (Phase 5.5)**: Non-suppression analyst-assisted confidence intelligence capability (`AIConfidenceAnalysisService`) evaluating security findings across 8 intelligence layers (metadata, evidence proofs, asset topology, triage history, Phase 5.2 explanations/impact analysis, Phase 5.3 attack paths, and Phase 5.4 remediation plans) to determine classification (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `NEEDS_REVIEW`), confidence score (0.0 - 1.0), evidence quality score (0.0 - 1.0), supporting & contradicting evidence reasoning, missing information, validation requirements, and duplicate finding similarity correlation across 8 signals (`CVE`, `CWE`, `ENDPOINT`, `ASSET_NODE`, `PLUGIN_ID`, `VULNERABILITY_TITLE`, `AFFECTED_COMPONENT`, `ATTACK_TECHNIQUE`). Features a strict **Non-Suppression Safety Policy** (zero automated finding closure or suppression), 2-table normalized relational schema (`ai_finding_confidence_analyses`, `ai_finding_similarity_matches`), AI confidence score calibration metadata tracking (`predicted_confidence_score`, `analyst_final_decision`, `confidence_accuracy_delta`, `feedback_timestamp`), and RBAC authorization guards (`findings:ai_confidence`).
- **Security Knowledge Base & RAG Vector Engine (Phase 5.6)**: Retrieval-Augmented Generation (RAG) vector engine (`AIRAGKnowledgeService`) powered by PostgreSQL `pgvector` (`vector(1536)`). Ingests, chunks, embeds, and indexes security reference standards (OWASP Cheat Sheets, CWE definitions, CAPEC attack patterns, CVE/NVD databases, vendor advisories) and internal security policies with source-type configurable text chunking (`OWASP`/`CWE`/`CAPEC`: 512/64, `CVE_NVD`: 256/32, `INTERNAL_POLICY`: 768/128), embedding model metadata tracking (`embedding_model`, `embedding_dimension`), source citation tracking (`source_url`, `source_author`, `published_date`, `last_updated_date`), RAG evaluation metrics (`retrieval_quality_score`, `average_similarity_score`), human review governance approval workflows (`UNDER_REVIEW` -> `APPROVED` -> `INDEXED`), hybrid tenant boundary isolation (`organization_id IS NULL OR organization_id = tenant_id`), and RBAC authorization guards (`knowledge:read`, `knowledge:write`, `knowledge:delete`).
- **Enterprise AI Security Copilot & Interactive Assistant (Phase 5.7)**: Conversational SOC analyst assistant (`SecurityCopilotService`) synthesizing security intelligence from all Era 5 AI engines. Features a multi-agent intent routing architecture (`AgentOrchestrator`) with 6 specialized sub-agent personas (`SECURITY_ANALYST`, `EXPLAINER`, `ATTACK_PATH`, `REMEDIATION`, `FALSE_POSITIVE`, `KNOWLEDGE_RAG`), safe read-only security tool registry (`CopilotToolRegistry`) registering 7 internal tools (`get_finding_details`, `get_asset_topology`, `get_risk_summary`, `search_rag_knowledge`, `get_remediation_plan`, `get_confidence_analysis`, `get_attack_path`), multi-turn investigation memory (`CopilotContextMemory`), AI Response Grounding & Explainability metadata tracking (`response_confidence_score`, `sources_used`, `knowledge_chunks_used`, `tools_called`, `reasoning_summary`, `model_used`, `prompt_version`, `response_evaluation_metadata`), 5-table normalized schema (`ai_copilot_sessions`, `ai_copilot_messages`, `ai_copilot_context_memories`, `ai_copilot_tool_executions`, `ai_copilot_feedback`), strict **Human-in-the-Loop Only** non-autonomous safety policy, and RBAC authorization guards (`copilot:read`, `copilot:chat`, `copilot:manage`, `copilot:feedback`).
- **Celery & Distributed Isolated Worker Sandbox Cluster (Phase 6.1)**: Distributed Celery worker cluster infrastructure (`celery_app.py`) managing priority task queues (`scans.high`, `scans.default`, `scans.low`, `ai.priority`), container sandbox security limits (`WorkerSandboxManager` enforcing 1 vCPU, 512MB RAM, `no_new_privs=True`, unprivileged UID/GID 10001, read-only rootfs, dropped capabilities, egress network filtering), worker orchestrator service (`WorkerOrchestratorService`), worker node/task database tracking (`worker_nodes`, `worker_task_executions`), task execution audit logging (`worker_task.dispatched`, `worker_task.cancelled`), REST API cluster monitoring and job dispatching (`POST /api/v1/workers/jobs/dispatch`, `GET /api/v1/workers/nodes`, `GET /api/v1/workers/metrics`), and RBAC authorization guards (`workers:read`, `workers:manage`, `scans:dispatch`). Worker execution flow follows `Celery Worker -> Task Queue -> Sandbox Executor -> Job Dispatch` with zero direct OS command execution.
- **Scan Management Portal & Live Monitor Gateway (Phase 7.4)**: Operations portal (`/scans` & `/scans/[id]`), target URL masking utility (`mask_target_url()`), decoupled `ScanManagementService` (paginated jobs, telemetry aggregation, lifecycle state delegation), frontend service abstraction (`ScansService`), step execution activity timeline (`ScanActivityTimeline`), and real-time WebSocket event streaming console (`LiveEventConsole`).
- **Vulnerability Triage, Evidence Record Viewer & AI Remediation Drawer (Phase 7.5)**: Analyst investigation workspace (`/vulnerabilities/[id]`), read-only aggregator service `FindingIntelligenceService`, multi-modal proof evidence viewer (`EvidenceViewerDrawer` with HTTP request/responses, screenshots, DOM snapshots, plugin output, SHA-256 integrity badges), vertical attack chain graph (`AttackPathGraph`), and advisory copilot panel (`AIRemediationDrawer` displaying AI explanations, step-by-step fix guides, syntax-highlighted code patches, verification checklists, and on-demand AI remediation triggers). Zero table duplication with full tenant isolation.
- **Enterprise Administration Workspace & Control Plane (Phase 7.6)**: Administrative control plane (`/settings/*`) providing verified capabilities:
  - **✓ Organization Settings**: Workspace profile management, slug identification, and subscription plan tracking (`settings/organization/page.tsx`).
  - **✓ User Management**: Team member listing, status filters, user search, invitation workflows, role assignment, and account deactivation (`settings/users/page.tsx`, `UserManagementTable`, `InviteUserModal`).
  - **✓ RBAC Visualization**: Interactive role-permission boundary matrix comparing OWNER, ADMIN, SECURITY_ANALYST, and VIEWER roles against resource permissions (`settings/roles/page.tsx`, `RolePermissionMatrix`).
  - **✓ API Key Governance**: Machine-to-machine integration API key generation with raw secret key show-once dialog, active key scope tags, and instant revocation (`settings/api-keys/page.tsx`, `APIKeyManagementPanel`).
  - **✓ Security Posture & MFA Overview**: Authentication security policy overview, session policy tracking, and MFA enrollment state visibility card (`settings/security/page.tsx`, `SecuritySettingsCard`).


---


## ⚡ 4. Why Vulnova is Different

1. **Enterprise Assessment Intelligence Pipeline**: Rather than operating as a raw plugin scanner, Vulnova transforms scan outputs into normalized, deduplicated, and fully evidenced security intelligence.
2. **AI-Native AppSec Workflows**: Built specifically to integrate Large Language Models (LLMs) for intelligent vulnerability scoring (CVSS 4.0), false-positive mitigation, attack path generation, and automated patch code fixes.
3. **Clean Architecture & Domain Isolation**: Strict separation of concerns (`api` → `application` → `domain` ← `infrastructure`) ensures core business logic remains independent of web frameworks and database drivers.
4. **Enterprise Multi-Tenancy**: Built from day one for multi-organization SaaS deployments with zero cross-tenant data leakage.
5. **Security-First Engineering**: OWASP ASVS v4.0 aligned, strict Python type annotations (`mypy --strict`), automated supply chain vulnerability scanning (Trivy, Semgrep, Gitleaks), and immutable audit trails.

---

## 📐 5. System Architecture

```
                               ┌─────────────────────────────────────────┐
                               │   Next.js 14 Enterprise Web App         │
                               │   (React 18, TypeScript, TailwindCSS)   │
                               └────────────────────┬────────────────────┘
                                                    │ HTTPS / WSS
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │    FastAPI Gateway & Control Plane      │
                               │  (Async Python 3.12, OAuth2/JWT/RBAC)   │
                               └────────────────────┬────────────────────┘
                                                    │ Task Queue / Event Bus
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │   Assessment Intelligence Pipeline      │
                               │ ┌───────────────┬─────────────────────┐ │
                               │ │ Discovery     │ 10 Security Plugins │ │
                               │ ├───────────────┼─────────────────────┤ │
                               │ │ Risk Engine   │ Finding Deduplicator│ │
                               │ ├───────────────┼─────────────────────┤ │
                               │ │ Evidence      │ DOM/PNG Proof Store │ │
                               │ └───────────────┴─────────────────────┘ │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  PostgreSQL 16 (pgvector) & Redis 7     │
                               └─────────────────────────────────────────┘
```

---

## 🛠️ 6. Technology Stack Matrix

| Subsystem | Technologies & Specifications |
|---|---|
| **Core Language** | Python 3.12+ (Strict Type Annotations, AsyncIO) |
| **API Gateway & Web** | FastAPI 0.111+, Uvicorn, Pydantic v2, Pydantic Settings |
| **Authentication & Security** | Argon2id (`passlib[argon2]`), PyJWT (HS256), HMAC SHA-256 |
| **Database & ORM** | PostgreSQL 16+, SQLAlchemy 2.0 (Async), Alembic, `pgvector` |
| **Cache & Task Queue** | Redis 7+, Celery |
| **Browser Rendering** | Playwright Headless Chromium (DOM Snapshots & PNG Screenshots) |
| **Code Quality & CI/CD** | Pytest 8.2+, Black, Ruff, Mypy (`strict = true`), GitHub Actions |
| **DevSecOps Tools** | Trivy (SCA/Container), Semgrep (SAST), Gitleaks (Secret Detection) |

---

## 🔒 7. Security Architecture & Controls

### Authentication Flow
```
User Credentials ──► Argon2id Verify ──► Issue HS256 Access Token (15m)
                                      └──► Issue Refresh Token (7d HTTP-Only Cookie)
```

### Authorization & Tenant Isolation
- **Role Hierarchy**: `OWNER` (40) > `ADMIN` (30) > `SECURITY_ANALYST` (20) > `VIEWER` (10)
- **Dependency Guard**: `@router.get("", dependencies=[Depends(require_permission("users:read"))])`
- **Tenant Validation**: Enforces `UserModel.organization_id == target_organization_id` on all queries.

---

## ⚡ 8. Quick Start Guide

### Prerequisites
- Python 3.12+
- PostgreSQL 16+ (with `uuid-ossp` and `vector` extensions enabled)
- Redis 7+

### Backend Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ayushsingh257/Vulnova.git
   cd Vulnova/backend
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .[dev]
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in `backend/`:
   ```ini
   SECRET_KEY=your-super-secret-key-min-32-characters-long
   DATABASE_URL=postgresql+asyncpg://vulnova_admin:vulnova_secure_password@localhost:5432/vulnova_db
   REDIS_URL=redis://localhost:6379/0
   ENVIRONMENT=development
   ```

4. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Start FastAPI Control Plane**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Interactive OpenAPI docs available at `http://localhost:8000/docs`.

---

## 🧪 9. Testing & Quality Verification

Run the full local quality gates before committing code:

```bash
cd backend

# 1. Format Check (Black)
black --check app tests

# 2. Linting (Ruff)
ruff check app

# 3. Strict Type Checking (Mypy)
mypy app --config-file pyproject.toml

# 4. Automated Test Suite (Pytest)
python -m pytest -v
```

**Current Backend Quality Metrics**: **395+ Passed** (100% test pass rate, Mypy strict mode, Ruff clean, Black formatted).

---

## 🗺️ 10. Roadmap & Era Progression

- ✅ **Era 0**: Architecture & Enterprise Documentation Foundation
- ✅ **Era 0.5**: Enterprise Architecture Refinement & Security Model Polish
- ✅ **Era 1**: Infrastructure, Monorepo & DevSecOps Foundation
- ✅ **Era 2**: Core Platform & Tenant Management System
- ✅ **Era 3**: Discovery Engine & Asset Surface Mapping
- ✅ **Era 4**: Vulnerability Assessment Engine & Dynamic Testing
- ✅ **Era 5**: Enterprise AI Security Analyst & Copilot Engine
- ✅ **Era 6**: Distributed Scanning Orchestration & Worker Sandbox
  - ✅ Phase 6.1 — Celery & Distributed Worker Sandbox
  - ✅ Phase 6.2 — Target Scan Config & Authorized Contract Gate
  - ✅ Phase 6.3 — Scan Execution Lifecycle State Machine
  - ✅ Phase 6.4 — Real-Time Scan Progress & WebSocket Stream
  - ✅ Phase 6.5 — Distributed Scan Scheduler & Recurrence Engine
- ✅ **Era 7**: Enterprise SOC Dashboard, Scans & Management Platform *(COMPLETED)*
  - ✅ Phase 7.1 — Security Operations Dashboard & Analyst Experience
  - ✅ Phase 7.2 — Public Marketing Pages, Enterprise Trust Center & Security Disclosure Gateway
  - ✅ Phase 7.3 — Enterprise Executive Analytics, Risk Snapshot Engine & Threat Advisory System
  - ✅ Phase 7.4 — Scan Management Portal & Live Monitor Gateway
  - ✅ Phase 7.5 — Vulnerability Triage, Evidence Record Viewer & AI Remediation Drawer
  - ✅ Phase 7.6 — User, Organization & Role Management UI
- 🟡 **Era 8**: Reporting, Executive Metrics & Export System *(PLANNED / NEXT)*
  - ⏳ Phase 8.1 — PDF & HTML Executive Security Report Generator
- ⏳ **Era 9**: Enterprise Integration & Developer Workflows
- ⏳ **Era 10**: Complete Security Validation Lifecycle & OWASP Verification
- ⏳ **Era 11**: Enterprise Scale, Performance Tuning & Reliability
- ⏳ **Era 12**: Final Security Audit, Production Deployment & Release


---

## 📄 License

Vulnova is licensed under the [MIT License](LICENSE).
