# Vulnova — Enterprise AI Application Security Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)
[![Security: OWASP ASVS](https://img.shields.io/badge/Security-OWASP_ASVS_v4.0-crimson.svg)](SECURITY.md)
[![Architecture: Clean Architecture](https://img.shields.io/badge/Architecture-Clean%20%2F%20DDD-black.svg)](ARCHITECTURE.md)
[![Status: Era 10 Complete](https://img.shields.io/badge/Status-Era%2010%20Validation%20Suite%20Complete-green.svg)](ROADMAP.md)

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
- **Role-Based Access Control (RBAC)**: Canonical permissions mapped to granular roles (`OWNER`, `ADMIN`, `SECURITY_ANALYST`, `VIEWER`) backed by `@require_permission` decorators.
- **Enterprise Administration Workspace (Phase 7.6)**:
  - **✓ Organization Governance**: Enterprise profile controls, security defaults, and system metadata visibility (`settings/organization/page.tsx`).
  - **✓ Team User Lifecycle**: User invitation modals, role elevation/demotion controls with active owner protection (`count_owners_in_org <= 1`), and self-deactivation guards (`settings/users/page.tsx`).
  - **✓ Role-Permission Matrix**: Interactive visual permissions table displaying granted privileges across all system roles (`settings/roles/page.tsx`).
  - **✓ API Key Governance**: Machine-to-machine integration API key generation with raw secret key show-once dialog, active key scope tags, and instant revocation (`settings/api-keys/page.tsx`, `APIKeyManagementPanel`).
  - **✓ Security Posture & MFA Overview**: Authentication security policy overview, session policy tracking, and MFA enrollment state visibility card (`settings/security/page.tsx`, `SecuritySettingsCard`).
- **PDF & HTML Executive Security Report Generator (Phase 8.1)**: CISO-level executive security report generation engine (`app/application/reporting/`) providing verified capabilities:
  - **✓ Executive Report Payload Aggregation**: Aggregates posture metrics, time-series risk trends, attack surface coverage, vulnerability severity breakdowns, top findings, and threat advisories via `ExecutiveSecurityReportService`.
  - **✓ Jinja2 HTML Live Preview**: `HTMLRendererService` rendering executive HTML reports with print-ready A4 CSS (`templates/style.css`, `templates/executive_report.html`) inside sandboxed iframe containers (`frontend/components/reports/ReportPreview.tsx`).
  - **✓ WeasyPrint PDF Generation & Fallback**: `PDFGeneratorService` compiling PDF binary streams with graceful fallback to compliant binary PDF/1.4 container wrapper if system libraries are missing.
  - **✓ Audit Event Non-Repudiation**: Dispatches audit log events (`report.generated`, `report.downloaded`) capturing report ID, user ID, organization ID, format, and payload size.
  - **✓ Next.js 14 CISO Reporting Workspace**: CISO reporting dashboard (`/reports`), report detail view (`/reports/[id]`), report generation modal (`ReportGenerationModal`), security metrics summary cards (`SecurityMetricsSummary`), and PDF export buttons (`ReportDownloadActions`).
- **Developer Technical Remediation Export System (Phase 8.2)**: Developer-focused technical export engine (`app/application/reporting/developer_export_service.py`) providing verified capabilities:
  - **✓ Memory-Efficient Streaming Bulk Exports**: Streams JSON arrays, CSV spreadsheets, and Markdown documents in 50-item batch chunks (`StreamingResponse`), preventing worker OOM memory crashes on large datasets.
  - **✓ Single Vulnerability Technical Export Package**: Formats finding details, proof evidence, attack chain graphs, and AI fix recommendations into ticket-ready Markdown, JSON, or CSV files (`export_single_finding`).
  - **✓ Sensitive Credential Masking**: `sanitize_sensitive_data` automatically scrubs Bearer tokens, authorization headers, and session cookies from exported proof snippets.
  - **✓ REST Export Router & RBAC**: `/api/v1/reports/export` router (`reports:export` permission) with `GET /json`, `GET /csv`, `GET /markdown`, `GET /{finding_id}` endpoints.
  - **✓ Next.js Technical Export UI Panel**: `TechnicalExportPanel` component with format selection tabs, scope controls, one-click file download, and copy-to-clipboard for Markdown ticket descriptions integrated into `/reports/[id]` and `/vulnerabilities/[id]`.
- **Compliance Framework Mapping Engine & Workspace (Phase 8.3)**: Enterprise compliance intelligence layer (`app/application/compliance/`) providing verified capabilities:
  - **✓ Multi-Standard Compliance Mapping**: `ComplianceMappingService` evaluating findings against OWASP Top 10 2021, OWASP ASVS 4.0.3, PCI DSS 4.0, and ISO 27001:2022 without database table changes.
  - **✓ Active Finding Filter & Posture Scoring**: Evaluates posture score `(passed_controls / total_controls) * 100.0` strictly filtering for active open findings (`OPEN`, `CONFIRMED`, `NEW`, `UNREAD`, `TRIAGED`, `IN_REMEDIATION`), excluding resolved and false-positive findings.
  - **✓ Full Control-to-Evidence Traceability**: Formats complete traceability chain (`Framework Control -> Vulnerability Finding -> Evidence Artifact Checksum -> Target Asset -> Remediation Guidance`).
  - **✓ REST Compliance Router & Audit Trail**: `/api/v1/compliance` endpoints backed by `compliance:read` and `compliance:export` permissions with audit logging (`compliance.viewed`, `compliance.exported`).
  - **✓ Next.js Compliance Workspace**: Dashboard `/compliance`, detail view `/compliance/[framework]`, framework selector tabs (`FrameworkSelector`), posture score card (`ComplianceScoreCard`), controls table (`ComplianceControlTable`), slide-in evidence drawer (`ComplianceEvidenceDrawer`), and JSON report downloader (`ComplianceExportButton`).
- **Jira & GitHub Issues Integration Plugin (Phase 9.1)**: Enterprise integration layer (`app/application/integrations/`) providing verified capabilities:
  - **✓ Bi-Directional Ticket Synchronization**: `IntegrationService` creating tickets in Atlassian Jira Cloud (Atlassian Document Format ADF) and GitHub Issues (GitHub-Flavored Markdown) directly from vulnerability findings.
  - **✓ AES-256 Secret Encryption**: `SecretEncryptionService` encrypting provider API tokens and Personal Access Tokens (PATs) at rest with zero plaintext leaks or database migrations.
  - **✓ Controlled State Transition Layer**: Controlled state mappers (`ControlledJiraStatusMapper`, `ControlledGitHubStatusMapper`) safely mapping external ticket state changes (`DONE`/`CLOSED` -> `RESOLVED`, `IN_PROGRESS` -> `IN_REMEDIATION`) into Vulnova finding lifecycle states.
  - **✓ REST Integrations Router & Granular RBAC**: `/api/v1/integrations` endpoints backed by `integrations:read` (VIEWER+), `integrations:create`/`integrations:update` (SECURITY_ANALYST+), and `integrations:manage` (ADMIN+) permissions.
  - **✓ Next.js Integration Control Plane**: Dashboard `/integrations`, provider settings `/integrations/settings`, `IntegrationsService`, `IntegrationSettingsCard`, `CreateIssueModal`, `IntegrationHistoryPanel`, and sidebar navigation integration.
- **Slack & Microsoft Teams Security Alert Webhooks (Phase 9.2)**: Enterprise security notification framework (`app/application/notifications/`) providing verified capabilities:
  - **✓ Slack Block Kit & Teams Adaptive Cards**: Format adapters (`SlackWebhookProvider` & `TeamsWebhookProvider`) dispatching richly formatted alert cards with severity color indicators (`#DC2626` for CRITICAL, `#F97316` for HIGH).
  - **✓ Resilient Asynchronous Alert Dispatch**: Non-blocking `NotificationService` dispatching alerts without disrupting scan execution, vulnerability processing, or compliance workflows.
  - **✓ Webhook Secret Protection & Tenant Isolation**: AES-256 encrypted webhook URLs (`SecretEncryptionService`), masked URL outputs, and `organization_id` boundary enforcement.
  - **✓ REST Notifications Router & Audit Logging**: `/api/v1/notifications` endpoints backed by `notifications:read`, `notifications:create`, `notifications:update`, and `notifications:manage` permissions with audit events (`notification.channel_created`, `notification.sent`, `notification.failed`).
  - **✓ Next.js Notification Center**: Dashboard `/notifications`, workspace `/notifications/settings`, `NotificationChannelCard`, `WebhookConfigurationModal`, `NotificationRuleEditor`, `NotificationHistoryPanel`, `TestNotificationButton`, and sidebar integration.
- **CI/CD Pipeline Scanning CLI Tool (Phase 9.3)**: Enterprise developer CLI and CI/CD automation suite (`cli/` & `app/application/cli_scanning/`) providing verified capabilities:
  - **✓ Independent Distributable CLI Package (`vulnova-cli`)**: Python CLI tool (`vulnova auth login`, `vulnova project register`, `vulnova scan start`, `vulnova scan status`, `vulnova findings summary`, `vulnova gate check`, `vulnova report export`) with zero DB/frontend dependencies, `--json` machine-readable output mode, and `--quiet` CI mode.
  - **✓ CI/CD Pipeline Integration Templates**: Ready-to-use templates for `.github/workflows/vulnova-security-scan.yml`, `.gitlab-ci.yml`, and `Jenkinsfile`.
  - **✓ Build Security Gate Evaluation**: Evaluates build gate thresholds (e.g. `CRITICAL >= 1`) returning standard CI exit codes (`0` = Pass, `1` = Gate Failure, `2` = Error).
  - **✓ REST CLI Router & Audit Logging**: `/api/v1/cli/*` endpoints backed by `cli:read`, `cli:trigger`, and `cli:manage` permissions with audit events (`cli.token_created`, `cli.token_revoked`, `cli.scan_started`, `cli.pipeline_failed`).
- **OWASP Top 10 (2021) Security Validation Suite (Phase 10.1)**: Automated security assertion framework (`app/application/owasp_validation/`) providing verified capabilities:
  - **✓ In-Memory Verification Engine**: `OWASPValidationRunnerService` evaluating active tenant findings and security controls against all 10 OWASP Top 10 (2021) categories (A01 - A10) with zero database table changes.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.owasp_suite_started`, `validation.owasp_suite_completed`) matching Era 8 zero-duplication compliance patterns.
  - **✓ Explainable Failure Diagnostics**: Every category result returns diagnostic `failure_reason`, target `affected_subsystem` (e.g. `SecretEncryptionService`, `SSRFValidator`, `RBACPolicy`), and actionable `remediation_guidance`.
  - **✓ Deep SSRF Firewall Validation**: Direct integration with `is_safe_target_url` verifying private IP range blocking (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`, AWS IMDS `169.254.169.254`) and DNS rebinding prevention.
  - **✓ REST Validation Router & RBAC**: `/api/v1/validation/owasp-top-10` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
  - **✓ Next.js OWASP Validation Workspace**: Dashboard `/validation/owasp`, `OWASPPassRateCard`, `OWASPCategoryGrid`, `OWASPValidationRunButton`, `OWASPTestDetailsModal`, and sidebar navigation integration.
- **OWASP API Security Top 10 (2023) Validation Suite (Phase 10.2)**: Automated API endpoint security assertion framework (`app/application/api_security_validation/`) providing verified capabilities:
  - **✓ In-Memory API Verification Engine**: `APISecurityValidationRunnerService` evaluating REST API routes and security controls against all 10 OWASP API Security Top 10 (2023) categories (API1 BOLA through API10 Unsafe API Consumption) with zero database table changes.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.api_security_suite_started`, `validation.api_security_suite_completed`).
  - **✓ Explainable API Failure Diagnostics**: Every API category result returns diagnostic `failure_reason`, target `affected_endpoint` (e.g. `/api/v1/vulnerabilities/{id}`), `affected_subsystem` (e.g. `OrganizationIsolation`, `RateLimiter`), and actionable `remediation_guidance`.
  - **✓ Deep BOLA & Auth Verification**: Verifies mandatory `organization_id` multi-tenant boundaries, IDOR protections, JWT expiration enforcement, and API key prefix rules (`vn_live_`, `vn_cli_`).
  - **✓ REST API Validation Router & RBAC**: `/api/v1/validation/api-security` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
  - **✓ Next.js API Security Workspace**: Dashboard `/validation/api-security`, `APIValidationPassRateCard`, `APIValidationCategoryGrid`, `APIValidationRunButton`, `APITestDetailsModal`, and sidebar navigation integration.
- **Security Configuration & Infrastructure Validation Suite (Phase 10.3)**: Automated infrastructure security assertion framework (`app/application/infrastructure_validation/`) providing verified capabilities:
  - **✓ In-Memory Infrastructure Verification Engine**: `InfrastructureSecurityValidationRunnerService` evaluating deployment posture, containers, supply chain lockfiles, CI/CD pipelines, database security, logging, RBAC access controls, network SSRF firewalls, cloud metadata, and operational security readiness across all 10 INFRA categories with zero database table changes.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.infrastructure_suite_started`, `validation.infrastructure_suite_completed`).
  - **✓ Explainable Infrastructure Failure Diagnostics**: Every category result returns diagnostic `failure_reason`, target `affected_component` (e.g. `Dockerfile & Docker Compose Runtime`, `Dependency Lockfiles`), and actionable `remediation_guidance`.
  - **✓ Deep Container, Supply Chain & Cloud Verification**: Verifies non-root container execution (`USER appuser`), supply chain lockfiles (`pyproject.toml`, `package-lock.json`), CI/CD pipeline gate enforcement, database connection encryption, `AuditLogService` & alert webhooks (Slack/Teams), and AWS IMDS cloud metadata blocking.
  - **✓ REST Validation Router & RBAC**: `/api/v1/validation/infrastructure` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
  - **✓ Next.js Infrastructure Workspace**: Dashboard `/validation/infrastructure`, `InfrastructurePassRateCard`, `InfrastructureCategoryGrid`, `InfrastructureValidationRunButton`, `InfrastructureTestDetailsModal`, and sidebar navigation integration.
- **Platform Penetration Testing & Exploit Verification Suite (Phase 10.4)**: Automated penetration test assertion framework (`app/application/pentest_validation/`) providing verified capabilities:
  - **✓ In-Memory Penetration Test Engine**: `PenTestValidationRunnerService` evaluating active exploit scenarios simulating real-world attack vectors against platform API Gateway, Auth, Multi-Tenant Boundaries, Injections, SSRF Egress, Mass Assignment, Rate Limits, CORS, Error Leakages, and Webhooks across all 10 PenTest categories (PEN1 - PEN10) with zero database table changes.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.pentest_suite_started`, `validation.pentest_suite_completed`).
  - **✓ Explainable Exploit Diagnostics**: Every PenTest category result returns diagnostic `failure_reason`, target `affected_target` (e.g. `/api/v1/auth/login`, `/api/v1/vulnerabilities/{id}`), and actionable `remediation_guidance`.
  - **✓ Deep Exploit Vector Verification**: Verifies JWT signature tampering rejection, multi-tenant IDOR boundaries (`organization_id`), SQL/Command injection protection, AWS IMDS metadata exfiltration blocking (`is_safe_target_url`), rate limit DoS protection (`RateLimiter`), CORS origin whitelisting, production stack trace suppression, and webhook HMAC signature verification.
  - **✓ REST Validation Router & RBAC**: `/api/v1/validation/pentest` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
  - **✓ Next.js PenTest Workspace**: Dashboard `/validation/pentest`, `PenTestPassRateCard`, `PenTestCategoryGrid`, `PenTestValidationRunButton`, `PenTestDetailsModal`, and sidebar navigation integration.
- **Dependency Security Audit & SCA Enforcement Suite (Phase 10.5)**: Automated Software Composition Analysis framework (`app/application/sca_validation/`) providing verified capabilities:
  - **✓ In-Memory SCA Verification Engine**: `SCAValidationRunnerService` evaluating third-party dependencies, lockfile integrity, outdated packages, CI/CD pipeline gates (`pip-audit`, `npm audit`), open-source license compliance, typosquatting, transitive tree depth, version pinning guards, DB drivers, and 30-day CVE remediation SLAs across all 10 SCA categories (SCA1 - SCA10) with zero database table changes.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.sca_suite_started`, `validation.sca_suite_completed`).
  - **✓ Explainable SCA Diagnostics**: Every SCA category result returns diagnostic `failure_reason`, target `affected_package` (e.g. `PyPI & NPM Dependencies`, `Dependency Lockfiles`), and actionable `remediation_guidance`.
  - **✓ Deep Supply Chain Verification**: Verifies lockfile cryptographic hash pins (`pyproject.toml`, `package-lock.json`), CI/CD `pip-audit`/`npm audit` gate rules, open-source license compliance (MIT, Apache, GPL), typosquatting detection, strict version pinning syntax (`==`), and database driver security (asyncpg, psycopg).
  - **✓ REST Validation Router & RBAC**: `/api/v1/validation/sca` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
  - **✓ Next.js SCA Workspace**: Dashboard `/validation/sca`, `SCAPassRateCard`, `SCACategoryGrid`, `SCAValidationRunButton`, `SCADetailsModal`, and sidebar navigation integration.
- **Container Image Security Audit & Runtime Hardening Suite (Phase 10.6)**: Automated container security verification framework (`app/application/container_validation/`) providing verified capabilities:
  - **✓ In-Memory Container Verification Engine**: `ContainerValidationRunnerService` evaluating base image CVEs, unprivileged execution (`USER appuser`), minimal distroless footprints, Linux capability drops (`cap_drop: [ALL]`), `HEALTHCHECK` directives, secret exposure in layers, cgroup resource throttling, custom bridge network isolation (`vulnova-network`), Seccomp profiles, and SHA-256 image digest pinning across all 10 Container categories (CONTAINER1 - CONTAINER10) with zero database table changes and controlled warning handling when scanner binaries are absent.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.container_suite_started`, `validation.container_suite_completed`).
  - **✓ Explainable Container Diagnostics**: Every Container category result returns diagnostic `failure_reason`, target `affected_container` (e.g. `Dockerfile & Docker Compose Runtime User`, `Seccomp & AppArmor Security Profiles`), and actionable `remediation_guidance`.
  - **✓ Deep Container Hardening Verification**: Verifies unprivileged execution (`USER appuser`), Linux capability dropping (`cap_drop: [ALL]`), `no-new-privileges` flag, cgroup CPU/memory limits (`memory: 1g`), `/health` probes, and SHA-256 image digest pinning.
  - **✓ REST Validation Router & RBAC**: `/api/v1/validation/container` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
- **Secrets & Cryptographic Management Audit Suite (Phase 10.7)**: Automated secrets scanning & cryptographic verification framework (`app/application/secrets_validation/`) providing verified capabilities:
  - **✓ In-Memory Secrets Verification Engine**: `SecretsValidationRunnerService` evaluating Gitleaks hardcoded secret scanning (with controlled warning status when Gitleaks binary is uninstalled), AES-256-GCM authenticated envelope encryption (`CryptoService`), JWT signing key entropy (min 256-bit entropy), machine-to-machine SHA-256 API key hashing & constant-time `hmac.compare_digest` verification, webhook HMAC-SHA256 signatures (`X-Vulnova-Signature`), TLS 1.2/1.3 in-transit encryption standards, secret key rotation policies & versioning metadata (without inventing fake rotation history), Argon2id/bcrypt password hashing work factors, CI/CD pipeline secret masking, and 90-day secrets governance SLAs across all 10 Secrets categories (SECRET1 - SECRET10) with zero database table changes.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.secrets_suite_started`, `validation.secrets_suite_completed`).
  - **✓ Explainable Secrets Diagnostics**: Every Secrets category result returns diagnostic `failure_reason`, target `affected_secret` (e.g. `Database Sensitive Field Encryption (CryptoService AES-256-GCM)`, `JWT Auth Signing Key & Algorithm Enforcement`), and actionable `remediation_guidance`.
  - **✓ Deep Cryptographic Verification**: Verifies AES-256-GCM envelope encryption, SHA-256 API key digests, HMAC-SHA256 webhook signatures, TLS 1.2/1.3 transport standards, and key rotation policy metadata.
  - **✓ REST Validation Router & RBAC**: `/api/v1/validation/secrets` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
- **Threat Model Review & STRIDE Verification Suite (Phase 10.8)**: Automated threat modeling framework (`app/application/threat_validation/`) providing verified capabilities:
  - **✓ In-Memory Threat Verification Engine**: `ThreatValidationRunnerService` evaluating all 6 Microsoft STRIDE threat categories: Spoofing (JWT identity validation, API key SHA-256 hashing & `vn_live_` prefixes), Tampering (Pydantic payload schema sanitization, SQL ORM parameterization, webhook HMAC-SHA256 signatures), Repudiation (mandatory `AuditLogService` event tracking), Information Disclosure (multi-tenant `organization_id` boundary isolation, AES-256-GCM field encryption, production stack trace masking, SSRF egress blocking), Denial of Service (Redis-backed `RateLimiter`, Celery worker concurrency limits), and Elevation of Privilege (RBAC role hierarchy `VIEWER` < `ANALYST` < `ADMIN`, IDOR prevention, container sandbox `cap_drop: [ALL]` & `USER appuser`) across all 10 STRIDE categories (STRIDE1 - STRIDE10) with zero database table changes.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.threat_suite_started`, `validation.threat_suite_completed`).
  - **✓ Explainable Threat Diagnostics**: Every STRIDE category result returns diagnostic `failure_reason`, target `affected_component` (e.g. `User JWT Bearer Authentication & Token Expiration`, `Multi-Tenant Database Queries (organization_id Scope)`), and actionable `remediation_guidance`.
  - **✓ Deep Architectural Verification**: Verifies identity authentication guards, API key hashing, input sanitization, webhook signatures, audit event tracking, multi-tenant boundaries, field encryption & SSRF egress blocking, Redis rate limiting, RBAC permission hierarchy, and container sandbox capability dropping.
  - **✓ REST Validation Router & RBAC**: `/api/v1/validation/threat` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
  - **✓ Next.js Threat Workspace**: Dashboard `/validation/threat`, `ThreatPassRateCard`, `ThreatCategoryGrid`, `ThreatValidationRunButton`, `ThreatDetailsModal`, and sidebar navigation integration.
- **Automated Security Regression Testing Framework (Phase 10.9)**: Continuous security regression testing engine (`app/application/regression_validation/`) providing verified capabilities:
  - **✓ In-Memory Security Regression Engine**: `RegressionValidationRunnerService` evaluating all 10 Security Regression categories: REGRESSION1 (OWASP Web Top 10), REGRESSION2 (OWASP API Security Top 10), REGRESSION3 (Security Config & Infrastructure), REGRESSION4 (Penetration Exploits), REGRESSION5 (SCA Supply Chain), REGRESSION6 (Container Hardening), REGRESSION7 (Secrets & Cryptography), REGRESSION8 (STRIDE Threat Model), REGRESSION9 (RBAC Hierarchy & Privilege Escalation), and REGRESSION10 (Audit Logging Non-Repudiation) with zero database table changes.
  - **✓ Ephemeral Audit Correlation**: Generates runtime `suite_id` UUIDs for audit log tracking (`validation.regression_suite_started`, `validation.regression_suite_completed`).
  - **✓ Explainable Regression Diagnostics**: Every category result returns diagnostic `failure_reason`, target `affected_component` (e.g. `FastAPI Web Routers & Middleware`, `AuditLogService Mandatory Event Dispatcher`), and actionable `remediation_guidance`.
  - **✓ Continuous Protection Matrix**: Verifies zero active SQLi/XSS/SSRF/RCE regressions, BOLA/BFLA guards, header hardening, pentest exploit re-execution blocking, supply chain lockfile hash integrity, container capability dropping, secret entropy, tenant isolation boundaries, RBAC decorators, and non-repudiation audit tracking.
  - **✓ REST Validation Router & RBAC**: `/api/v1/validation/regression` endpoints backed by `validation:read` (VIEWER+) and `validation:execute` (SECURITY_ANALYST+) permissions.
  - **✓ Next.js Security Regression Workspace**: Dashboard `/validation/regression`, `RegressionPassRateCard`, `RegressionCategoryGrid`, `RegressionValidationRunButton`, `RegressionDetailsModal`, and sidebar navigation integration.

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
- **PDF & HTML Executive Security Report Generator (Phase 8.1)**: CISO-level executive security report generation engine (`app/application/reporting/`) providing verified capabilities:
  - **✓ Executive Report Payload Aggregation**: Aggregates posture metrics, time-series risk trends, attack surface coverage, vulnerability severity breakdowns, top findings, and threat advisories via `ExecutiveSecurityReportService`.
  - **✓ Jinja2 HTML Live Preview**: `HTMLRendererService` rendering executive HTML reports with print-ready A4 CSS (`templates/style.css`, `templates/executive_report.html`) inside sandboxed iframe containers (`frontend/components/reports/ReportPreview.tsx`).
  - **✓ WeasyPrint PDF Generation & Fallback**: `PDFGeneratorService` compiling PDF binary streams with graceful fallback to compliant binary PDF/1.4 container wrapper if system libraries are missing.
  - **✓ Audit Event Non-Repudiation**: Dispatches audit log events (`report.generated`, `report.downloaded`) capturing report ID, user ID, organization ID, format, and payload size.
  - **✓ Next.js 14 CISO Reporting Workspace**: CISO reporting dashboard (`/reports`), report detail view (`/reports/[id]`), report generation modal (`ReportGenerationModal`), security metrics summary cards (`SecurityMetricsSummary`), and PDF export buttons (`ReportDownloadActions`).


### 🛡️ Enterprise Production Reliability & Operational Pillars
Vulnova is designed not only to provide security capabilities, but also to operate reliably as an enterprise SaaS platform. Its engineering roadmap integrates **Security Engineering**, **Scalability Engineering**, **Reliability Engineering**, **Observability**, and **Disaster Recovery readiness**.

#### ✅ Completed Operational Foundations:
- **Security Engineering**: Argon2id password hashing, short-lived HS256 JWT access tokens, token family rotation, multi-tenant isolation, OWASP ASVS v4.0 compliance, and zero auto-execution human safety policies.
- **Distributed Worker Sandbox Cluster**: Multi-queue Celery architecture (`celery_app.py`) with strict container resource limits (1 vCPU, 512MB RAM, `no_new_privs=True`, dropped capabilities, UID/GID 10001).
- **Audit Logging & Non-Repudiation**: Immutable audit log event tracking (`audit_logs`) across administrative mutations, finding triage, scan controls, and report exports.

#### 📋 Planned Enterprise Reliability Capabilities (Era 11 Roadmap):
- **Observability & Telemetry**: Prometheus metrics export (`/metrics`), Grafana dashboard visualization, Loki/ELK centralized logging, Sentry error tracking, automated alert rules, and `/health` liveness/readiness probes.
- **Backup Strategy & Point-in-Time Recovery**: Automated PostgreSQL WAL archiving, 30-day backup retention, AES-256 backup encryption at rest, and automated PITR restore verification testing.
- **Disaster Recovery & Failover**: Recovery Time Objective (RTO < 1h), Recovery Point Objective (RPO < 5m), automated multi-region failover, and deployment rollback strategies.
- **Incident Response Lifecycle**: 4-tier severity classification (`SEV-1` to `SEV-4`), automated PagerDuty/Slack alert escalation rules, forensic audit log investigation, and post-incident review (PIR) workflows.

---

## ⚡ 4. Why Vulnova is Different

1. **Enterprise Assessment Intelligence Pipeline**: Rather than operating as a raw plugin scanner, Vulnova transforms scan outputs into normalized, deduplicated, and fully evidenced security intelligence.
2. **AI-Native AppSec Workflows**: Built specifically to integrate Large Language Models (LLMs) for intelligent vulnerability scoring (CVSS 4.0), false-positive mitigation, attack path generation, and automated patch code fixes.
3. **Clean Architecture & Domain Isolation**: Strict separation of concerns (`api` → `application` → `domain` ← `infrastructure`) ensures core business logic remains independent of web frameworks and database drivers.
4. **Enterprise Multi-Tenancy**: Built from day one for multi-organization SaaS deployments with zero cross-tenant data leakage.
5. **Security-First & Reliability Engineering**: OWASP ASVS v4.0 aligned, strict Python type annotations (`mypy --strict`), automated supply chain vulnerability scanning (Trivy, Semgrep, Gitleaks), immutable audit trails, and planned observability/DR readiness.

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
- ✅ **Era 8**: Reporting, Executive Metrics & Export System *(COMPLETED)*
  - ✅ Phase 8.1 — PDF & HTML Executive Security Report Generator
  - ✅ Phase 8.2 — Developer Technical Remediation Export System
  - ✅ Phase 8.3 — Compliance Framework Mapping Engine & Workspace
- ✅ **Era 9**: Enterprise Integration & Developer Workflows *(COMPLETED)*
  - ✅ Phase 9.1 — Jira & GitHub Issues Integration Plugin
  - ✅ Phase 9.2 — Slack & Microsoft Teams Security Alert Webhooks
  - ✅ Phase 9.3 — CI/CD Pipeline Scanning CLI Tool (`vulnova-cli`)
- ✅ **Era 10**: Complete Security Validation Lifecycle & OWASP Verification *(COMPLETED)*
  - ✅ Phase 10.1 — OWASP Top 10 (2021) Security Validation Suite
  - ✅ Phase 10.2 — OWASP API Security Top 10 (2023) Validation Suite
  - ✅ Phase 10.3 — Security Configuration & Infrastructure Validation Suite
  - ✅ Phase 10.4 — Platform Penetration Testing & Exploit Verification Suite
  - ✅ Phase 10.5 — Dependency Security Audit & SCA Enforcement Suite
  - ✅ Phase 10.6 — Container Image Security Audit & Runtime Hardening Suite
  - ✅ Phase 10.7 — Secrets & Cryptographic Management Audit Suite
  - ✅ Phase 10.8 — Threat Model Review & STRIDE Verification Suite
  - ✅ Phase 10.9 — Automated Security Regression Testing Framework
- 🟡 **Era 11**: Enterprise Scale, Performance Tuning & Reliability *(PLANNED / NEXT)*
- ⏳ **Era 12**: Final Security Audit, Production Deployment & Release


---

## 📄 License

Vulnova is licensed under the [MIT License](LICENSE).
