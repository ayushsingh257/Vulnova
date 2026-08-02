# Vulnova — Enterprise AI Application Security Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)
[![Security: OWASP ASVS](https://img.shields.io/badge/Security-OWASP_ASVS_v4.0-crimson.svg)](SECURITY.md)
[![Architecture: Clean Architecture](https://img.shields.io/badge/Architecture-Clean%20%2F%20DDD-black.svg)](ARCHITECTURE.md)
[![Status: Era 2 Complete](https://img.shields.io/badge/Status-Era%202%20Complete-green.svg)](ROADMAP.md)
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

### 🔍 Security Assessment & Evidence Intelligence Engine
- **10 Production Assessment Plugins**: High-concurrency security plugins covering Web (SQLi, XSS, Security Headers, Cookie Auth Security), API (Exposed Docs, JWT Signatures & Claims, CORS Policies), and Infrastructure/Cloud (Open Administrative Ports, TLS/SSL Certs & Protocols, S3/Azure/GCP & IMDS Exposure).
- **Risk Intelligence Engine**: CVSS v3.1/v4 vector parsing, EPSS (Exploit Prediction Scoring System) probability mapping, asset criticality multipliers (1.5x, 1.2x, 1.0x, 0.8x), normalized 0.0–100.0 risk scoring, and SLA assignment (24h Critical, 72h High, 14d Medium, 30d Low).
- **Finding Deduplication**: SHA-256 signature hashing (`organization_id`, `plugin_id`, `cwe_id`, `target_endpoint`, `parameter_name`) merging duplicate finding instances into primary canonical findings.
- **Multi-Modal Evidence Collection Engine**: Captures reproducible proof including masked HTTP request/response dumps, header/cookie profiles, Playwright HTML DOM snapshots, and visual PNG screenshots.
- **Provider-Independent Evidence Storage**: Async `EvidenceArtifactStorage` with SHA-256 content checksum verification and tenant-isolated storage paths.

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

**Current Backend Quality Metrics**: **148/148 Passed** (100% test pass rate).

---

## 🗺️ 10. Roadmap & Era Progression

- ✅ **Era 0**: Architecture & Enterprise Documentation Foundation
- ✅ **Era 0.5**: Enterprise Architecture Refinement & Security Model Polish
- ✅ **Era 1**: Infrastructure, Monorepo & DevSecOps Foundation
- ✅ **Era 2**: Core Platform & Tenant Management System
- ✅ **Era 3**: Discovery Engine & Asset Surface Mapping
  - ✅ Phase 3.1 — Async HTTP Web Crawler Core
  - ✅ Phase 3.2 — SPA & Dynamic DOM Crawling System
  - ✅ Phase 3.3 — Target Asset Taxonomy & Fingerprinting
  - ✅ Phase 3.4 — API Schema Inference & Endpoint Discovery
  - ✅ Phase 3.5 — Attack Surface Mapping & Visual Graph Engine
- 🟡 **Era 4**: Vulnerability Assessment Engine & Dynamic Testing *(IN PROGRESS)*
  - ✅ Phase 4.1 — Security Assessment Plugin Framework Core
  - ✅ Phase 4.2 — Web Vulnerability Assessment Plugin Suite
  - ✅ Phase 4.3 — API Security Assessment Plugin Suite
  - ✅ Phase 4.4 — Infrastructure & Cloud Security Assessment Plugin Suite
  - ✅ Phase 4.5 — Finding Normalization & Risk Intelligence Engine
  - ✅ Phase 4.6 — Multi-Modal Evidence Collection & Capture Engine
  - ⏳ Phase 4.7 — Enterprise Scan Profile & Execution Policy Engine
  - ⏳ Phase 4.8 — Multi-Source Finding Correlation & Asset Inventory Engine
  - ⏳ Phase 4.9 — Attack Surface Trend & Continuous Monitoring Engine
- ⏳ **Era 5**: Enterprise AI Security Analyst & Copilot Engine
- ⏳ **Era 6**: Distributed Scanning Orchestration & Worker Sandbox
- ⏳ **Era 7**: Enterprise Web Application, Dashboard & Trust Center
- ⏳ **Era 8**: Reporting, Executive Metrics & Export System
- ⏳ **Era 9**: Enterprise Integration & Developer Workflows
- ⏳ **Era 10**: Complete Security Validation Lifecycle & OWASP Verification
- ⏳ **Era 11**: Enterprise Scale, Performance Tuning & Reliability
- ⏳ **Era 12**: Final Security Audit, Production Deployment & Release

---

## 📄 License

Vulnova is licensed under the [MIT License](LICENSE).
