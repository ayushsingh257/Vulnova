# Vulnova — Security Architecture & Policy Matrix (SECURITY.md)

Security is the core foundation of **Vulnova**. This document defines the security architecture, OWASP ASVS alignment, scanner sandbox isolation, target scan authorization & legal safety model, authentication framework, RBAC controls, data protection, and vulnerability disclosure policy.

---

## 🛡️ 1. Security Design Principles

1. **Defense-in-Depth**: Security controls are applied across every layer (DNS, Reverse Proxy, API Gateway, Application Logic, Database, Data at Rest, Isolated Scanner Sandboxes).
2. **Zero Trust Architecture**: Every request—internal or external—is authenticated, authorized, validated, and logged.
3. **Least Privilege Enforcement**: Users, services, and containers operate with the minimum required access rights.
4. **Fail Securely**: Systems fail into a closed, secure state without leaking sensitive trace details or unauthorized data.

---

## 🔒 2. Scanner Sandbox Isolation & Container Boundaries

Dynamic security scanning involves dispatching payloads against untrusted targets. Vulnova enforces strict sandbox boundaries around scanner worker nodes to protect the platform control plane:

- **Unprivileged Container Execution**: Scanner workers run as non-root users (`UID 10001`) with `read_only_rootfs: true` and all Linux capabilities dropped (`CAP_SYS_ADMIN`, `CAP_NET_RAW` removed).
- **Resource Constraints**: Strict limits enforced per worker container (`1.0 vCPU`, `512MB RAM`, `100MB tmpfs` wiped on completion).
- **Egress Firewall & Proxying**: Scanner egress passes through an outbound filtering proxy blocking access to internal private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`) and cloud metadata endpoints (`169.254.169.254`).
- **One-Way Result Reporting**: Sandbox workers communicate back to the orchestrator via sanitized JSON payload queues and possess no direct database access credentials or master secret keys.

---

## 📜 3. Scan Authorization & Legal Safety Model

Before any security assessment executes, Vulnova enforces legal authorization verification to prevent unauthorized scanning.

### A. Authorized Security Assessment Confirmation
Every target setup and scan creation request requires an explicit user confirmation check:

> *"I confirm that I own this asset or have explicit written permission from the asset owner to perform dynamic security testing. I agree to operate strictly within the defined scan scope."*

### B. Verification & Scope Enforcement
1. **Domain Ownership Verification**: Targets can require DNS TXT record or file upload verification prior to launching `FULL_SECURITY_ASSESSMENT` scans.
2. **Scope Boundary Restrictions**: Out-of-scope subdomains, paths, and URLs are strictly filtered by `ScanPolicyEngine.is_url_in_scope()` using fnmatch wildcard include/exclude pattern matching before executing active probes.
3. **Execution Rate & Concurrency Throttling**: `ScanPolicyEngine` validates and clamps request concurrency (max 20 workers) and rate limits (max 50 requests/sec) to prevent Denial of Service (DoS) against target infrastructure.
4. **Credential Injection Protection**: Auth headers (`Authorization: Bearer <token>`) and session cookies are injected safely via `enrich_request_headers` and `enrich_request_cookies`, ensuring secrets are masked before logging or evidence storage.
5. **Emergency Stop Controls**: Scans configured with `stop_on_critical: true` automatically terminate plugin execution immediately upon discovering a `CRITICAL` severity finding to prevent cascading impact.
6. **Immutable Audit Logging**: Every scan execution logs structured audit events capturing:
   - `user_id` & `organization_id`
   - Target URL, `profile_id`, and `enabled_plugins` list
   - Target URL & confirmed scope rules
   - User IP address, timestamp (UTC ISO 8601), and error logs.
7. **Asset Inventory Multi-Tenant Isolation**: `AssetInventoryService` and `AssetInventoryRepository` enforce mandatory `organization_id` boundary filters on all inventory endpoints (`GET /api/v1/assets/inventory`, `GET /api/v1/assets/{asset_id}`). Cross-organization asset lookups strictly fail with `ResourceNotFoundException` / 404 to prevent unauthorized posture visibility.

---

## 🔑 4. Authentication Framework & Session Management

### Dual Token Rotation Architecture
- **Access Tokens**: Short-lived JWT (15-minute expiration), signed using `RS256` or `EdDSA`. Carries user ID, org ID, and assigned roles.
- **Refresh Tokens**: Long-lived secure tokens (7-day expiration), stored in HTTP-Only, Secure, SameSite=Strict cookies. Hashed and stored in PostgreSQL with token family rotation to prevent reuse attacks.

### Multi-Factor Authentication (MFA)
- Time-based One-Time Password (TOTP) compliant with RFC 6238.
- Mandatory MFA requirement capability for Organization Admins.

---

## 👥 5. Multi-Tenant Role-Based Access Control (RBAC) Matrix

| Role | Access Permissions |
| :--- | :--- |
| **Owner** | Full organization control, billing management, deletion, role assignment |
| **Admin** | Manage users, scan profiles, integration Webhooks, API keys |
| **Security Analyst** | Launch scans, triage findings, trigger AI analysis, export security reports |
| **Viewer** | Read-only access to dashboards, scan status, and high-level reports |

---

## 🔐 6. Data Protection & Cryptography

### Encryption in Transit
- Mandatory TLS 1.3 (TLS 1.2 minimum) for all HTTP and WebSocket connections.
- HSTS preloading enabled with `max-age=63072000; includeSubDomains; preload`.

### Encryption at Rest
- Sensitive database fields (API Keys, Integration Secrets, Target Auth Tokens) encrypted using `AES-256-GCM` via envelope key management.
- PostgreSQL storage volumes encrypted at the infrastructure storage layer.

### Evidence Artifact Sanitization & Integrity
- **Sensitive Data Sanitization**: Prior to persisting HTTP exchanges, headers, or cookies in evidence storage, all sensitive credentials (`Authorization` headers, `Cookie`/`Set-Cookie` directives, session IDs, JWT tokens, API keys) are sanitized (`mask_sensitive_headers`, `mask_sensitive_cookies`).
- **Integrity Checksums**: Every captured evidence artifact calculates a SHA-256 hash over raw byte content to guarantee proof integrity and non-repudiation.
- **Tenant Isolation**: Evidence storage paths are strictly isolated per tenant (`uploads/evidence/<organization_id>/<finding_id>/`).

### Posture Snapshotting & Audit History Protection (Phase 4.9)
- **Tenant Boundary Isolation**: All posture snapshots (`asset_snapshots`) and change events (`asset_change_events`) enforce mandatory `organization_id` foreign keys and query filters.
- **Audit Trail Non-Repudiation**: Every posture snapshot is tied to `assessment_job_id` and timestamped (`created_at` TIMESTAMPTZ) to create an immutable compliance history.
- **RBAC Endpoint Protection**: Trend APIs (`GET /api/v1/assets/trends`, `GET /api/v1/security/posture/timeline`) enforce strict RBAC permissions (`assets:read`, `findings:read`).

### Finding Triage & Automated Suppression Security Controls (Phase 4.10)
- **Granular RBAC Authorization**: Finding triage actions (`PATCH /api/v1/findings/{id}/triage`) require `findings:triage` permission (`SECURITY_ANALYST` role level 20+), while creating or deleting automated suppression rules (`POST /api/v1/findings/suppression-rules`) requires `findings:suppress` permission (`ADMIN` role level 30+).
- **Immutable Triage History**: Every finding triage state transition is recorded in `finding_triage_history` with actor user attribution (`actor_user_id`), previous status, new status, and audit timestamps.
- **Audit Trail Traceability**: Reuses `AuditLogService.record_event` (`finding.triaged`, `suppression_rule.created`, `suppression_rule.deleted`) to provide complete audit trail traceability for regulatory compliance.
- **Multi-Tenant Boundary Security**: All `FindingTriageRepository` queries enforce strict `organization_id` filters to prevent cross-organization triage or suppression rule access.

### Multi-Provider LLM Gateway Security & Secret Encryption Controls (Phase 5.1)
- **AES-256-GCM Secret Encryption**: External LLM provider API keys and integration credentials are encrypted at rest using AES-256-GCM (`SecretEncryptionService` in `app/security/encryption.py`).
- **Prompt Context Secret Sanitization**: `PromptOrchestratorService` automatically strips/masks Authorization Bearer tokens, cookies, API keys, and passwords from security finding and evidence dumps before formatting prompt payloads (`mask_sensitive_prompt_context`).
- **Prompt Injection Defense Preparation**: System prompts enforce strict boundary demarcations (`<security_finding_data>`, `<evidence_dumps>`) instructing LLM providers to treat untrusted target input purely as data.
- **AI Audit Trail Non-Repudiation**: Every AI request records token consumption (input/output), latency (ms), provider used, model alias, cost estimate ($), and status in `llm_request_logs` with mandatory tenant isolation (`organization_id`).

### AI Finding Explainer & Impact Analysis Security Controls (Phase 5.2)
- **Granular RBAC Authorization**: Generating AI explanations or impact reports requires `findings:ai_explain` permission (`SECURITY_ANALYST` role level 20+), while reading previously generated analysis requires `findings:read` (`VIEWER` role level 10+).
- **Structured Output Recovery Defense**: Invalid or malformed LLM responses trigger a single repair attempt with strict JSON repair system prompts before recording a `FAILED` status, preventing malformed data injection into analysis tables.
- **Sensitive Data Masking**: All evidence dumps and finding descriptions pass through `mask_sensitive_prompt_context` before being rendered into prompt payloads.
- **Tenant Isolation & Audit Trail**: Explanations (`ai_finding_explanations`) and impact reports (`ai_impact_analyses`) enforce mandatory `organization_id` foreign keys and query filters, with generation events recorded via `AuditLogService.record_event` (`finding.ai_explained`, `finding.impact_analyzed`).

### AI Attack Path Synthesis Security Controls (Phase 5.3)
- **Granular RBAC Authorization**: Generating AI attack paths or recording analyst review feedback requires `findings:ai_attack_path` permission (`SECURITY_ANALYST` role level 20+), while reading attack paths requires `findings:read` (`VIEWER` role level 10+).
- **Evidence Grounding Safeguard**: Attack context built by `AIAttackPathService` strictly restricts LLM output to verified asset nodes, graph relationships, and evidence artifacts. LLM system prompts strictly forbid hallucinating non-existent assets or vulnerabilities.
- **MITRE ATT&CK Registry Validation**: Every step technique ID is validated against `KNOWN_MITRE_TECHNIQUES`. Unverified or non-standard technique IDs are flagged as `Unverified` to prevent malicious or hallucinated framework data.
- **Analyst Review Feedback Non-Repudiation**: Analyst status reviews (`ACCEPTED`, `REJECTED`, `REVIEWED`) record reviewer identity (`reviewed_by`), notes (`review_notes`), and timestamps (`reviewed_at`) in `ai_attack_paths` and log audit events (`ai_attack_path.reviewed`).

### AI Remediation Engine Security Controls (Phase 5.4)
- **Granular RBAC Authorization**: Generating remediation plans or updating review status requires `findings:ai_remediate` permission (`SECURITY_ANALYST` role level 20+), while reading plans requires `findings:read` (`VIEWER` role level 10+).
- **Strict Non-Executable Safety Policy**: Remediation recommendations and patch diff suggestions are stored as text strings. The service contains zero shell execution, git commit, or cloud API auto-mutation triggers, eliminating auto-remediation risks.
- **7-Layer Evidence Grounding**: Remediation context is constructed across 7 verified intelligence layers (finding, evidence proof, asset graph, triage state, Phase 5.2 explanations, Phase 5.2 impact analysis, Phase 5.3 attack paths). Prompts strictly prohibit inventing fake fixes or unrelated dependencies.
- **Analyst Review Non-Repudiation**: State transitions (`GENERATED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `IMPLEMENTED`, `VERIFIED`, `VALIDATION_FAILED`) require analyst authorization, recording `reviewed_by`, `review_notes`, and audit events (`ai_remediation.reviewed`).

### AI False Positive Filter & Confidence Security Controls (Phase 5.5)
- **Granular RBAC Authorization**: Generating confidence assessments or updating review feedback requires `findings:ai_confidence` permission (`SECURITY_ANALYST` role level 20+), while reading assessments requires `findings:read` (`VIEWER` role level 10+).
- **Strict Non-Suppression Safety Policy**: AI confidence classifications (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `NEEDS_REVIEW`) and evidence quality scores serve as advisory analyst intelligence. Zero automated finding closure, deletion, or suppression execution code exists in the service.
- **8-Layer Intelligence Grounding**: Confidence context is constructed across 8 verified intelligence layers (finding, evidence, asset topology, triage history, Phase 5.2 explanation, Phase 5.2 impact, Phase 5.3 attack path, Phase 5.4 remediation plan) with prompt injection protection (`<untrusted_security_context>`) and secret context masking (`mask_sensitive_prompt_context`).
- **Analyst Review Calibration Non-Repudiation**: Analyst status reviews record reviewer identity (`reviewed_by`), notes (`review_notes`), timestamps, and calibration metadata (`predicted_confidence_score`, `analyst_final_decision`, `confidence_accuracy_delta`) in audit logs (`ai_confidence.reviewed`).

### Security Knowledge Base & RAG Vector Engine Security Controls (Phase 5.6)
- **Granular RBAC Authorization**: Ingesting documents or reviewing status requires `knowledge:write` permission (`SECURITY_ANALYST` role level 20+), deleting documents requires `knowledge:delete` (`ADMIN` role level 30+), and searching requires `knowledge:read` (`VIEWER` role level 10+).
- **Hybrid Tenant Boundary Protection**: Tenant isolation strictly enforces `organization_id IS NULL OR organization_id = tenant_id`. Private organizational policies uploaded by tenant A are invisible to tenant B.
- **Document Governance Approval Workflow**: Internal security policies uploaded to tenant knowledge bases start in `UNDER_REVIEW` and require explicit analyst approval (`PATCH /api/v1/ai/knowledge/documents/{id}/review`) before vector indexing into search stores.
- **Secret Prompt Masking & Prompt Injection Defense**: Ingested document content and RAG query strings pass through `mask_sensitive_prompt_context`. Retreived RAG context blocks are wrapped in `<rag_knowledge_context>` tags to isolate reference text from LLM system prompts.

### Enterprise AI Security Copilot Security Controls (Phase 5.7)
- **Granular RBAC Authorization**: Creating or updating sessions requires `copilot:manage` permission (`SECURITY_ANALYST` role level 20+), chatting requires `copilot:chat` (`SECURITY_ANALYST`), submitting feedback requires `copilot:feedback` (`SECURITY_ANALYST`), and viewing session history requires `copilot:read` (`VIEWER` role level 10+).
- **Strict Human-in-the-Loop Read-Only Safety Policy**: Copilot tool execution (`CopilotToolRegistry`) is strictly restricted to read-only security data retrieval. Zero auto-patching, system command execution, or finding suppression capability exists in the copilot service or tool registry.
- **Strict Multi-Tenant Isolation**: Copilot sessions, message history, context memory, and tool execution queries strictly enforce `organization_id = tenant_id`.
- **Response Grounding Explainability Auditability**: Every assistant response tracks and records explainability metadata columns (`response_confidence_score`, `sources_used`, `knowledge_chunks_used`, `tools_called`, `reasoning_summary`, `model_used`, `prompt_version`, `response_evaluation_metadata`) and emits structured audit logs (`copilot_message.sent`, `copilot_feedback.submitted`).

---

## 🌐 7. Secure HTTP Headers & Browser Protections

Vulnova enforces strict security headers via API Gateway middleware:

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-R4nd0m...'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; frame-ancestors 'none'; object-src 'none'; base-uri 'self';
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

---

## 📢 8. Responsible Vulnerability Disclosure Policy

We welcome security researchers and developers to inspect Vulnova's codebase and report any identified vulnerabilities.

### Guidelines:
- Report security vulnerabilities directly to `security@vulnova.local` (or designated channel).
- Do not access, modify, or destroy customer or organizational data.
- Allow 30 days for remediation prior to public disclosure.

---

## ⚡ 9. Container Sandbox & Worker Cluster Security Controls (Phase 6.1)

1. **OCI Container Sandbox Security Constraints**:
   - **Resource Caps**: Enforces `cpu_limit_vcpu=1.0`, `memory_limit_mb=512`, and process thread limits (`PidsLimit=100`) to prevent denial-of-service or container resource starvation.
   - **Unprivileged Execution**: Runs under non-root UID/GID `10001:10001` with `no-new-privileges:true` security opt flag.
   - **FileSystem & Capabilities**: Root filesystem is read-only (`ReadonlyRootfs=True`); all Linux capabilities are dropped (`CapDrop=["ALL"]`).
   - **Egress Network Filtering**: Egress network connections are restricted to authorized target destinations.
2. **Execution Isolation Safeguard**:
   - Celery workers do NOT execute raw OS commands directly. All job executions pass through: `Celery Worker -> Task Queue -> Sandbox Executor -> Job Dispatch`.
3. **Multi-Tenant & RBAC Isolation**:
   - Database tables `worker_nodes` and `worker_task_executions` enforce `organization_id = tenant_id` isolation.
   - REST API endpoints enforce RBAC permissions (`workers:read`, `workers:manage`, `scans:dispatch`).

---

## 🎯 10. Authorized Security Assessment Contract & Pre-Scan Policy Gate (Phase 6.2)

1. **Mandatory Authorization Consent Contract**:
   - Every vulnerability assessment request requires explicit confirmation of `is_authorized_assessment=True`.
   - Requests lacking affirmative authorization consent are rejected immediately with HTTP 403 Forbidden.
# Vulnova — Security Architecture & Policy Matrix (SECURITY.md)

Security is the core foundation of **Vulnova**. This document defines the security architecture, OWASP ASVS alignment, scanner sandbox isolation, target scan authorization & legal safety model, authentication framework, RBAC controls, data protection, and vulnerability disclosure policy.

---

## 🛡️ 1. Security Design Principles

1. **Defense-in-Depth**: Security controls are applied across every layer (DNS, Reverse Proxy, API Gateway, Application Logic, Database, Data at Rest, Isolated Scanner Sandboxes).
2. **Zero Trust Architecture**: Every request—internal or external—is authenticated, authorized, validated, and logged.
3. **Least Privilege Enforcement**: Users, services, and containers operate with the minimum required access rights.
4. **Fail Securely**: Systems fail into a closed, secure state without leaking sensitive trace details or unauthorized data.

---

## 🔒 2. Scanner Sandbox Isolation & Container Boundaries

Dynamic security scanning involves dispatching payloads against untrusted targets. Vulnova enforces strict sandbox boundaries around scanner worker nodes to protect the platform control plane:

- **Unprivileged Container Execution**: Scanner workers run as non-root users (`UID 10001`) with `read_only_rootfs: true` and all Linux capabilities dropped (`CAP_SYS_ADMIN`, `CAP_NET_RAW` removed).
- **Resource Constraints**: Strict limits enforced per worker container (`1.0 vCPU`, `512MB RAM`, `100MB tmpfs` wiped on completion).
- **Egress Firewall & Proxying**: Scanner egress passes through an outbound filtering proxy blocking access to internal private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`) and cloud metadata endpoints (`169.254.169.254`).
- **One-Way Result Reporting**: Sandbox workers communicate back to the orchestrator via sanitized JSON payload queues and possess no direct database access credentials or master secret keys.

---

## 📜 3. Scan Authorization & Legal Safety Model

Before any security assessment executes, Vulnova enforces legal authorization verification to prevent unauthorized scanning.

### A. Authorized Security Assessment Confirmation
Every target setup and scan creation request requires an explicit user confirmation check:

> *"I confirm that I own this asset or have explicit written permission from the asset owner to perform dynamic security testing. I agree to operate strictly within the defined scan scope."*

### B. Verification & Scope Enforcement
1. **Domain Ownership Verification**: Targets can require DNS TXT record or file upload verification prior to launching `FULL_SECURITY_ASSESSMENT` scans.
2. **Scope Boundary Restrictions**: Out-of-scope subdomains, paths, and URLs are strictly filtered by `ScanPolicyEngine.is_url_in_scope()` using fnmatch wildcard include/exclude pattern matching before executing active probes.
3. **Execution Rate & Concurrency Throttling**: `ScanPolicyEngine` validates and clamps request concurrency (max 20 workers) and rate limits (max 50 requests/sec) to prevent Denial of Service (DoS) against target infrastructure.
4. **Credential Injection Protection**: Auth headers (`Authorization: Bearer <token>`) and session cookies are injected safely via `enrich_request_headers` and `enrich_request_cookies`, ensuring secrets are masked before logging or evidence storage.
5. **Emergency Stop Controls**: Scans configured with `stop_on_critical: true` automatically terminate plugin execution immediately upon discovering a `CRITICAL` severity finding to prevent cascading impact.
6. **Immutable Audit Logging**: Every scan execution logs structured audit events capturing:
   - `user_id` & `organization_id`
   - Target URL, `profile_id`, and `enabled_plugins` list
   - Target URL & confirmed scope rules
   - User IP address, timestamp (UTC ISO 8601), and error logs.
7. **Asset Inventory Multi-Tenant Isolation**: `AssetInventoryService` and `AssetInventoryRepository` enforce mandatory `organization_id` boundary filters on all inventory endpoints (`GET /api/v1/assets/inventory`, `GET /api/v1/assets/{asset_id}`). Cross-organization asset lookups strictly fail with `ResourceNotFoundException` / 404 to prevent unauthorized posture visibility.

---

## 🔑 4. Authentication Framework & Session Management

### Dual Token Rotation Architecture
- **Access Tokens**: Short-lived JWT (15-minute expiration), signed using `RS256` or `EdDSA`. Carries user ID, org ID, and assigned roles.
- **Refresh Tokens**: Long-lived secure tokens (7-day expiration), stored in HTTP-Only, Secure, SameSite=Strict cookies. Hashed and stored in PostgreSQL with token family rotation to prevent reuse attacks.

### Multi-Factor Authentication (MFA)
- Time-based One-Time Password (TOTP) compliant with RFC 6238.
- Mandatory MFA requirement capability for Organization Admins.

---

## 👥 5. Multi-Tenant Role-Based Access Control (RBAC) Matrix

| Role | Access Permissions |
| :--- | :--- |
| **Owner** | Full organization control, billing management, deletion, role assignment |
| **Admin** | Manage users, scan profiles, integration Webhooks, API keys |
| **Security Analyst** | Launch scans, triage findings, trigger AI analysis, export security reports |
| **Viewer** | Read-only access to dashboards, scan status, and high-level reports |

---

## 🔐 6. Data Protection & Cryptography

### Encryption in Transit
- Mandatory TLS 1.3 (TLS 1.2 minimum) for all HTTP and WebSocket connections.
- HSTS preloading enabled with `max-age=63072000; includeSubDomains; preload`.

### Encryption at Rest
- Sensitive database fields (API Keys, Integration Secrets, Target Auth Tokens) encrypted using `AES-256-GCM` via envelope key management.
- PostgreSQL storage volumes encrypted at the infrastructure storage layer.

### Evidence Artifact Sanitization & Integrity
- **Sensitive Data Sanitization**: Prior to persisting HTTP exchanges, headers, or cookies in evidence storage, all sensitive credentials (`Authorization` headers, `Cookie`/`Set-Cookie` directives, session IDs, JWT tokens, API keys) are sanitized (`mask_sensitive_headers`, `mask_sensitive_cookies`).
- **Integrity Checksums**: Every captured evidence artifact calculates a SHA-256 hash over raw byte content to guarantee proof integrity and non-repudiation.
- **Tenant Isolation**: Evidence storage paths are strictly isolated per tenant (`uploads/evidence/<organization_id>/<finding_id>/`).

### Posture Snapshotting & Audit History Protection (Phase 4.9)
- **Tenant Boundary Isolation**: All posture snapshots (`asset_snapshots`) and change events (`asset_change_events`) enforce mandatory `organization_id` foreign keys and query filters.
- **Audit Trail Non-Repudiation**: Every posture snapshot is tied to `assessment_job_id` and timestamped (`created_at` TIMESTAMPTZ) to create an immutable compliance history.
- **RBAC Endpoint Protection**: Trend APIs (`GET /api/v1/assets/trends`, `GET /api/v1/security/posture/timeline`) enforce strict RBAC permissions (`assets:read`, `findings:read`).

### Finding Triage & Automated Suppression Security Controls (Phase 4.10)
- **Granular RBAC Authorization**: Finding triage actions (`PATCH /api/v1/findings/{id}/triage`) require `findings:triage` permission (`SECURITY_ANALYST` role level 20+), while creating or deleting automated suppression rules (`POST /api/v1/findings/suppression-rules`) requires `findings:suppress` permission (`ADMIN` role level 30+).
- **Immutable Triage History**: Every finding triage state transition is recorded in `finding_triage_history` with actor user attribution (`actor_user_id`), previous status, new status, and audit timestamps.
- **Audit Trail Traceability**: Reuses `AuditLogService.record_event` (`finding.triaged`, `suppression_rule.created`, `suppression_rule.deleted`) to provide complete audit trail traceability for regulatory compliance.
- **Multi-Tenant Boundary Security**: All `FindingTriageRepository` queries enforce strict `organization_id` filters to prevent cross-organization triage or suppression rule access.

### Multi-Provider LLM Gateway Security & Secret Encryption Controls (Phase 5.1)
- **AES-256-GCM Secret Encryption**: External LLM provider API keys and integration credentials are encrypted at rest using AES-256-GCM (`SecretEncryptionService` in `app/security/encryption.py`).
- **Prompt Context Secret Sanitization**: `PromptOrchestratorService` automatically strips/masks Authorization Bearer tokens, cookies, API keys, and passwords from security finding and evidence dumps before formatting prompt payloads (`mask_sensitive_prompt_context`).
- **Prompt Injection Defense Preparation**: System prompts enforce strict boundary demarcations (`<security_finding_data>`, `<evidence_dumps>`) instructing LLM providers to treat untrusted target input purely as data.
- **AI Audit Trail Non-Repudiation**: Every AI request records token consumption (input/output), latency (ms), provider used, model alias, cost estimate ($), and status in `llm_request_logs` with mandatory tenant isolation (`organization_id`).

### AI Finding Explainer & Impact Analysis Security Controls (Phase 5.2)
- **Granular RBAC Authorization**: Generating AI explanations or impact reports requires `findings:ai_explain` permission (`SECURITY_ANALYST` role level 20+), while reading previously generated analysis requires `findings:read` (`VIEWER` role level 10+).
- **Structured Output Recovery Defense**: Invalid or malformed LLM responses trigger a single repair attempt with strict JSON repair system prompts before recording a `FAILED` status, preventing malformed data injection into analysis tables.
- **Sensitive Data Masking**: All evidence dumps and finding descriptions pass through `mask_sensitive_prompt_context` before being rendered into prompt payloads.
- **Tenant Isolation & Audit Trail**: Explanations (`ai_finding_explanations`) and impact reports (`ai_impact_analyses`) enforce mandatory `organization_id` foreign keys and query filters, with generation events recorded via `AuditLogService.record_event` (`finding.ai_explained`, `finding.impact_analyzed`).

### AI Attack Path Synthesis Security Controls (Phase 5.3)
- **Granular RBAC Authorization**: Generating AI attack paths or recording analyst review feedback requires `findings:ai_attack_path` permission (`SECURITY_ANALYST` role level 20+), while reading attack paths requires `findings:read` (`VIEWER` role level 10+).
- **Evidence Grounding Safeguard**: Attack context built by `AIAttackPathService` strictly restricts LLM output to verified asset nodes, graph relationships, and evidence artifacts. LLM system prompts strictly forbid hallucinating non-existent assets or vulnerabilities.
- **MITRE ATT&CK Registry Validation**: Every step technique ID is validated against `KNOWN_MITRE_TECHNIQUES`. Unverified or non-standard technique IDs are flagged as `Unverified` to prevent malicious or hallucinated framework data.
- **Analyst Review Feedback Non-Repudiation**: Analyst status reviews (`ACCEPTED`, `REJECTED`, `REVIEWED`) record reviewer identity (`reviewed_by`), notes (`review_notes`), and timestamps (`reviewed_at`) in `ai_attack_paths` and log audit events (`ai_attack_path.reviewed`).

### AI Remediation Engine Security Controls (Phase 5.4)
- **Granular RBAC Authorization**: Generating remediation plans or updating review status requires `findings:ai_remediate` permission (`SECURITY_ANALYST` role level 20+), while reading plans requires `findings:read` (`VIEWER` role level 10+).
- **Strict Non-Executable Safety Policy**: Remediation recommendations and patch diff suggestions are stored as text strings. The service contains zero shell execution, git commit, or cloud API auto-mutation triggers, eliminating auto-remediation risks.
- **7-Layer Evidence Grounding**: Remediation context is constructed across 7 verified intelligence layers (finding, evidence proof, asset graph, triage state, Phase 5.2 explanations, Phase 5.2 impact analysis, Phase 5.3 attack paths). Prompts strictly prohibit inventing fake fixes or unrelated dependencies.
- **Analyst Review Non-Repudiation**: State transitions (`GENERATED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `IMPLEMENTED`, `VERIFIED`, `VALIDATION_FAILED`) require analyst authorization, recording `reviewed_by`, `review_notes`, and audit events (`ai_remediation.reviewed`).

### AI False Positive Filter & Confidence Security Controls (Phase 5.5)
- **Granular RBAC Authorization**: Generating confidence assessments or updating review feedback requires `findings:ai_confidence` permission (`SECURITY_ANALYST` role level 20+), while reading assessments requires `findings:read` (`VIEWER` role level 10+).
- **Strict Non-Suppression Safety Policy**: AI confidence classifications (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `NEEDS_REVIEW`) and evidence quality scores serve as advisory analyst intelligence. Zero automated finding closure, deletion, or suppression execution code exists in the service.
- **8-Layer Intelligence Grounding**: Confidence context is constructed across 8 verified intelligence layers (finding, evidence, asset topology, triage history, Phase 5.2 explanation, Phase 5.2 impact, Phase 5.3 attack path, Phase 5.4 remediation plan) with prompt injection protection (`<untrusted_security_context>`) and secret context masking (`mask_sensitive_prompt_context`).
- **Analyst Review Calibration Non-Repudiation**: Analyst status reviews record reviewer identity (`reviewed_by`), notes (`review_notes`), timestamps, and calibration metadata (`predicted_confidence_score`, `analyst_final_decision`, `confidence_accuracy_delta`) in audit logs (`ai_confidence.reviewed`).

### Security Knowledge Base & RAG Vector Engine Security Controls (Phase 5.6)
- **Granular RBAC Authorization**: Ingesting documents or reviewing status requires `knowledge:write` permission (`SECURITY_ANALYST` role level 20+), deleting documents requires `knowledge:delete` (`ADMIN` role level 30+), and searching requires `knowledge:read` (`VIEWER` role level 10+).
- **Hybrid Tenant Boundary Protection**: Tenant isolation strictly enforces `organization_id IS NULL OR organization_id = tenant_id`. Private organizational policies uploaded by tenant A are invisible to tenant B.
- **Document Governance Approval Workflow**: Internal security policies uploaded to tenant knowledge bases start in `UNDER_REVIEW` and require explicit analyst approval (`PATCH /api/v1/ai/knowledge/documents/{id}/review`) before vector indexing into search stores.
- **Secret Prompt Masking & Prompt Injection Defense**: Ingested document content and RAG query strings pass through `mask_sensitive_prompt_context`. Retreived RAG context blocks are wrapped in `<rag_knowledge_context>` tags to isolate reference text from LLM system prompts.

### Enterprise AI Security Copilot Security Controls (Phase 5.7)
- **Granular RBAC Authorization**: Creating or updating sessions requires `copilot:manage` permission (`SECURITY_ANALYST` role level 20+), chatting requires `copilot:chat` (`SECURITY_ANALYST`), submitting feedback requires `copilot:feedback` (`SECURITY_ANALYST`), and viewing session history requires `copilot:read` (`VIEWER` role level 10+).
- **Strict Human-in-the-Loop Read-Only Safety Policy**: Copilot tool execution (`CopilotToolRegistry`) is strictly restricted to read-only security data retrieval. Zero auto-patching, system command execution, or finding suppression capability exists in the copilot service or tool registry.
- **Strict Multi-Tenant Isolation**: Copilot sessions, message history, context memory, and tool execution queries strictly enforce `organization_id = tenant_id`.
- **Response Grounding Explainability Auditability**: Every assistant response tracks and records explainability metadata columns (`response_confidence_score`, `sources_used`, `knowledge_chunks_used`, `tools_called`, `reasoning_summary`, `model_used`, `prompt_version`, `response_evaluation_metadata`) and emits structured audit logs (`copilot_message.sent`, `copilot_feedback.submitted`).

---

## 🌐 7. Secure HTTP Headers & Browser Protections

Vulnova enforces strict security headers via API Gateway middleware:

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-R4nd0m...'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; frame-ancestors 'none'; object-src 'none'; base-uri 'self';
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

---

## 📢 8. Responsible Vulnerability Disclosure Policy

We welcome security researchers and developers to inspect Vulnova's codebase and report any identified vulnerabilities.

### Guidelines:
- Report security vulnerabilities directly to `security@vulnova.local` (or designated channel).
- Do not access, modify, or destroy customer or organizational data.
- Allow 30 days for remediation prior to public disclosure.

---

## ⚡ 9. Container Sandbox & Worker Cluster Security Controls (Phase 6.1)

1. **OCI Container Sandbox Security Constraints**:
   - **Resource Caps**: Enforces `cpu_limit_vcpu=1.0`, `memory_limit_mb=512`, and process thread limits (`PidsLimit=100`) to prevent denial-of-service or container resource starvation.
   - **Unprivileged Execution**: Runs under non-root UID/GID `10001:10001` with `no-new-privileges:true` security opt flag.
   - **FileSystem & Capabilities**: Root filesystem is read-only (`ReadonlyRootfs=True`); all Linux capabilities are dropped (`CapDrop=["ALL"]`).
   - **Egress Network Filtering**: Egress network connections are restricted to authorized target destinations.
2. **Execution Isolation Safeguard**:
   - Celery workers do NOT execute raw OS commands directly. All job executions pass through: `Celery Worker -> Task Queue -> Sandbox Executor -> Job Dispatch`.
3. **Multi-Tenant & RBAC Isolation**:
   - Database tables `worker_nodes` and `worker_task_executions` enforce `organization_id = tenant_id` isolation.
   - REST API endpoints enforce RBAC permissions (`workers:read`, `workers:manage`, `scans:dispatch`).

---

## 🎯 10. Authorized Security Assessment Contract & Pre-Scan Policy Gate (Phase 6.2)

1. **Mandatory Authorization Consent Contract**:
   - Every vulnerability assessment request requires explicit confirmation of `is_authorized_assessment=True`.
   - Requests lacking affirmative authorization consent are rejected immediately with HTTP 403 Forbidden.
2. **Scan Target Registration Gate**:
   - Target URLs must be pre-registered in `scan_targets` under the requesting organization before scanning.
   - Only targets with `status = 'ACTIVE'` can be scanned. Targets marked `ARCHIVED` or `SUSPENDED` are rejected.
3. **Immutable Consent Audit Trail**:
   - Every authorization event generates a timestamped, immutable record in `authorization_declarations` (`organization_id`, `scan_target_id`, `declared_by`, `authorization_scope`, `ip_address`).
   - Ensures legal traceability and compliance with CFAA / Computer Misuse Act guidelines.
4. **Worker Task Authorization Validation**:
   - `WorkerOrchestratorService.dispatch_scan_job()` verifies `is_authorized_assessment=True` before queuing background jobs.

---

## 📡 12. Real-Time WebSocket Event Stream Security Controls (Phase 6.4)

1. **JWT Handshake Authentication**:
   - WebSocket connection upgrades require valid JWT access tokens via query parameter (`?token=<jwt_access_token>`).
   - Unauthenticated or expired tokens cause immediate socket termination (Close Code `4001 Unauthorized`).
2. **Strict Multi-Tenant Boundary Enforcement**:
   - WebSocket connection requests validate that `user.organization_id` strictly matches target scan `organization_id`.
   - Cross-tenant connection attempts are terminated with Close Code `4003 Forbidden`.
3. **Connection Rate Limiting & Resource Protection**:
   - `MAX_CONNECTIONS_PER_ORG = 50`: Clamps total concurrent active WebSocket connections per organization. Connection attempts exceeding this limit are rejected with Close Code `4008 Limit Exceeded`.
   - `HEARTBEAT_INTERVAL_SECONDS = 30`: Sends periodic ping/pong heartbeats.
   - `CONNECTION_TIMEOUT_SECONDS = 90`: Background pruning drops stale connections inactive for >90s.
   - `MAX_EVENT_PAYLOAD_SIZE = 64KB`: Validates and caps event payload size. Oversized event payloads raise `ValueError` and trigger security warnings.
4. **Credential & Sensitive Payload Masking**:
   - Authorization headers and session cookies are sanitized (`mask_sensitive_headers`) before being emitted over real-time WebSocket event streams.

---

## ⏰ 13. Distributed Scan Scheduler & Recurrence Security Controls (Phase 6.5)

1. **Active Schedule Quota & Rate Safeguards**:
   - `MAX_ACTIVE_SCHEDULES_PER_ORG = 20`: Enforces active schedule quotas per tenant organization to prevent scheduling resource exhaustion or runaway scan proliferation.
   - Creating a new active schedule when at capacity raises `QuotaExceededException` (422 Unprocessable Entity).
2. **Target Scope & Target Existence Controls**:
   - Creating or updating a schedule verifies target existence and status in `ScanTargetRepository`.
   - Scheduled execution against archived or suspended targets is automatically skipped with `scan_schedule.skipped_target_inactive` audit logs.
3. **Concurrency & Lock Guard Integration**:
   - Scheduler execution tick (`ScanSchedulerService.execute_due_schedules()`) acquires target concurrency locks via Phase 6.3 `DistributedScanLockManager` before triggering scan execution.
   - Concurrency lock collisions cleanly skip duplicate execution without crashing or creating race conditions.
4. **Audit Trail Traceability**:
   - Every schedule lifecycle action generates structured audit logs capturing `organization_id`, `schedule_id`, `actor_user_id`, and event type (`scan_schedule.created`, `scan_schedule.updated`, `scan_schedule.paused`, `scan_schedule.resumed`, `scan_schedule.disabled`, `scan_schedule.triggered`).
5. **Governance-Only Autoscale Metrics**:
   - `WorkerAutoscalerService` provides capacity monitoring and scaling recommendations without direct infrastructure provisioning or cloud API execution, preventing unauthorized compute creation.

---

## 🖥️ 14. Security Operations Dashboard & Analyst Controls (Phase 7.1)

1. **Mandatory Tenant Boundary Isolation**:
   - All SQL queries within `DashboardAnalyticsService` enforce strict `WHERE organization_id = current_user.organization_id` clauses.
   - Redis cache key topologies incorporate tenant organization IDs (`dashboard:metrics:{org_id}`), preventing cross-tenant posture data leakage.
2. **Granular RBAC Authorization**:
   - `dashboard:read` permission required for viewing high-level SOC dashboard overview metrics (`Role.VIEWER` level 10+).
   - `analytics:read` permission required for accessing detailed composite risk trajectories and security posture analytics (`Role.SECURITY_ANALYST` level 20+).
3. **Sensitive Credential Sanitization**:
   - Scan targets, active scan step descriptions, and finding previews rendered on the dashboard pass through `mask_sensitive_headers` and `mask_sensitive_cookies` to sanitize tokens or secrets.
4. **Denial-of-Service Defense**:
   - 30s Redis cache TTL buffers the PostgreSQL database against high-frequency browser tab refreshes or concurrent analyst dashboard views.

---

## 🔒 15. Public Enterprise Trust Center & Security Disclosure Controls (Phase 7.2)

1. **Strict Public Data Boundary Isolation**:
   - Public endpoints (`/api/v1/public/trust`, `/api/v1/public/status`, `/.well-known/security.txt`) strictly return static platform compliance control mappings, encryption specifications, and high-level health indicators.
   - ZERO tenant organization IDs, target URLs, vulnerability findings, user PII, or internal credentials are exposed.
2. **RFC 9116 Vulnerability Disclosure Standardization**:
   - Implements standard `/.well-known/security.txt` and `/security` route providing security researchers with PGP public keys, security contact emails (`security@vulnova.com`), and response SLAs (24-hour triage, 72-hour remediation plan, 14-day resolution).
3. **Public Scraping & DoS Defense**:
   - 300s Redis cache TTL (`trust_center:public_summary`) buffers backend services against automated public crawler traffic.
   - IP-based rate limiting token bucket (`rate_limit:public:{ip}`) caps public requests at 60 req/min per client IP.

---

## 📊 16. Executive Analytics, Risk Snapshot & Export Controls (Phase 7.3)

1. **Persistent Risk Snapshot Isolation**:
   - Every `RiskPostureSnapshotModel` record strictly belongs to a specific `organization_id`. Celery Beat daily snapshot generation (`capture_daily_risk_snapshots`) enforces tenant boundaries during periodic background execution.
2. **Export Rate Limiting & DoS Defense**:
   - `/api/v1/dashboard/export` endpoints are protected by rate-limiting counter (`rate_limit:export:{org_id}`, max 10 req/min) to prevent bulk data extraction or server memory exhaustion.
3. **Structured Export Audit Logging**:
   - Every report download triggers an audit event (`dashboard.executive_report.exported`) capturing `organization_id`, `actor_user_id`, requested format (`json` or `csv`), and timestamp.
4. **Granular Report RBAC Permissions**:
   - `reports:read` required for retrieving executive posture summaries (`Role.VIEWER` level 10+).
   - `reports:export` required for executing report downloads (`Role.SECURITY_ANALYST` level 20+).

---

## 🔍 17. Vulnerability Investigation Workspace & Evidence Protection Controls (Phase 7.5)

1. **Strict Multi-Tenant Isolation**:
   - All `/api/v1/vulnerabilities/*` endpoints enforce `organization_id = current_user.organization_id` database query filters. Cross-tenant finding lookups return 404 Not Found to prevent attack surface enumeration.
2. **Evidence Artifact Integrity & Protection**:
   - Proof evidence artifacts (HTTP request/response dumps, screenshots, DOM snapshots) are read-only. Every artifact stores a SHA-256 checksum computed at creation time for non-repudiation and proof integrity verification.
3. **AI Remediation Non-Executable Advisory Safety**:
   - AI remediation guidance, code diffs, and verification steps are purely advisory text recommendations. The system contains ZERO auto-patch execution, shell invocation, or automated deployment triggers. All code changes require human analyst review.
4. **RBAC Guarding**:
   - `findings:read` required for finding details and evidence (`Role.VIEWER` level 10+).
   - `findings:ai_attack_path` required for attack path graph data (`Role.SECURITY_ANALYST` level 20+).
   - `findings:ai_remediate` required for AI remediation plan generation (`Role.SECURITY_ANALYST` level 20+).

---

## ⚙️ 18. Administrative RBAC Controls & API Key Governance (Phase 7.6)

1. **Administrative Tenant Isolation**:
   - All administrative endpoints (`/api/v1/admin/*`) enforce strict `organization_id = current_user.organization_id` database queries. Cross-tenant user, role, or organization access returns 403 Forbidden or 404 Not Found.
2. **Canonical Permission Enforcement**:
   - Organization settings require `organization:read` / `organization:update` (`Role.ADMIN` level 30+).
   - User management requires `users:read`, `users:invite`, `users:update_role`, `users:remove` (`Role.ADMIN` level 30+ / `Role.OWNER` level 40).
   - Integration API key governance requires `api_keys:read`, `api_keys:create`, `api_keys:revoke` (`Role.ADMIN` level 30+).
3. **Account Safeguards & Sole Owner Demotion Protection**:
   - `update_user_role` and `deactivate_user` check active owner counts (`count_owners_in_org <= 1`). Demoting or deactivating the sole active `OWNER` raises `400 Bad Request` validation error to prevent organization lockout.
   - `deactivate_user` explicitly blocks self-deactivation (`target_user_id == current_user.id`) with `403 Forbidden`.
4. **Raw API Key Show-Once Governance & Hash Storage**:
   - Raw integration API keys (`vn_live_...`) are generated cryptographically and returned ONCE in creation response DTO. Only `key_prefix` and SHA-256 `key_hash` are persisted in database storage.
5. **Comprehensive Administrative Audit Events**:
   - All administrative mutations dispatches audit events (`organization.updated`, `user.invited`, `user.role_updated`, `user.deactivated`, `api_key.created`, `api_key.revoked`) recording `actor_user_id`, `organization_id`, `resource_id`, `timestamp`, and detailed metadata.

---

## 📊 19. Executive Security Reporting RBAC & PDF Export Controls (Phase 8.1)

1. **Strict Multi-Tenant Query Boundaries**:
   - All `/api/v1/reports/*` endpoints enforce `organization_id = current_user.organization_id` database query filters. Cross-tenant report generation or PDF export requests return 403 Forbidden / 404 Not Found.
2. **Canonical Permission Enforcement**:
   - `reports:create` required for `POST /api/v1/reports/executive` (`Role.ADMIN` level 30+).
   - `reports:read` required for `GET /api/v1/reports/{id}` and `GET /api/v1/reports/{id}/html` (`Role.VIEWER` level 10+).
   - `reports:export` required for `GET /api/v1/reports/{id}/pdf` (`Role.SECURITY_ANALYST` level 20+).
3. **Graceful PDF Fallback & Sandbox Defense**:
   - PDF compilation via `PDFGeneratorService` isolates HTML rendering inside WeasyPrint with graceful fallback to a compliant binary PDF/1.4 wrapper if system C-libraries are unavailable.
   - Live HTML previews in Next.js UI render inside sandboxed `<iframe>` elements (`sandbox="allow-same-origin"`) to prevent script execution risks.
4. **Audit Trail Non-Repudiation**:
   - Report generation and PDF downloads dispatch immutable audit events (`report.generated`, `report.downloaded`) capturing `actor_user_id`, `organization_id`, `resource_id` (report ID), `timestamp`, `format`, and byte size.

5. **Developer Technical Remediation Export Security Controls (Phase 8.2)**:
   - **Sensitive Data & Credential Masking**: `sanitize_sensitive_data` automatically scrubs Authorization Bearer tokens, basic auth credentials, and session cookie headers from exported proof evidence snippets prior to document serialization.
   - **Streaming Memory Exhaustion Defense**: Bulk export endpoints (`/api/v1/reports/export/json`, `/csv`, `/markdown`) use batch cursors (`_stream_findings`, batch size 50) and stream output as chunked `StreamingResponse` objects, mitigating Denial-of-Service OOM worker crashes on large tenant datasets.
   - **Export RBAC & Tenant Boundaries**: Requires `reports:export` permission (`Role.SECURITY_ANALYST` level 20+) and restricts exported findings strictly to `organization_id = current_user.organization_id`.
   - **Export Audit Event Generation**: Dispatches `report.exported` and `vulnerability.exported` audit events recording `actor_user_id`, `organization_id`, export format, finding counts, and timestamps.

---

## 🛡️ 21. Compliance Governance & Security Controls (Phase 8.3)

Phase 8.3 establishes Vulnova's compliance intelligence layer and governance controls:

1. **Granular RBAC Authorization**:
   - `compliance:read`: Granted to `Role.VIEWER` (level 10+) and above. Authorizes access to framework overview posture scores and control status lists (`GET /api/v1/compliance/{framework}/overview`, `GET /api/v1/compliance/{framework}/controls`).
   - `compliance:export`: Restricted to `Role.SECURITY_ANALYST` (level 20+) and above. Authorizes export of downloadable JSON compliance report packages (`GET /api/v1/compliance/{framework}/export`).

2. **Strict Multi-Tenant Query Boundaries**:
   - Every compliance evaluation query strictly filters by `organization_id = current_user.organization_id`. Cross-tenant compliance posture inspection or report export requests return 403 Forbidden / 404 Not Found.

3. **Active Finding Compliance Filtering**:
   - Compliance posture score calculation strictly filters for active open findings (`OPEN`, `CONFIRMED`, `NEW`, `UNREAD`, `TRIAGED`, `IN_REMEDIATION`).
   - Findings marked as `RESOLVED`, `VERIFIED_FIXED`, or `FALSE_POSITIVE` do not cause compliance control failures, incentivizing remediation workflows.

4. **Non-Repudiable Audit Event Logging**:
   - Viewing compliance overviews and exporting compliance reports dispatch immutable audit events:
     - `compliance.viewed`: Captures `actor_user_id`, `organization_id`, `resource_id` (`framework_id`), `framework_version`, `compliance_percentage`, `failed_controls_count`, and UTC `timestamp`.
     - `compliance.exported`: Captures `actor_user_id`, `organization_id`, `resource_id` (`framework_id`), `framework_version`, `compliance_percentage`, and UTC `timestamp`.

---

## 🚨 20. Security Operations Maturity, Incident Response & Breach Readiness (Planned Era 11)

Era 11 establishes Vulnova's operational security maturity, security monitoring, and incident response governance:

1. **Security Monitoring & Threat Detection**:
   - Continuous log analysis (Loki/ELK) scanning application logs for authentication brute-force patterns, invalid token usage, rate limit violations (`rate_limit:exceeded`), and unauthorized permission attempts (`403 Forbidden`).
   - Automated SIEM integration streaming structured JSON audit logs (`AuditLogService`) to external SIEM platforms.

2. **Forensic Audit Log Analysis**:
   - Every operational and security event includes immutable actor attribution: `actor_user_id`, `organization_id`, `client_ip`, `user_agent`, `action`, `resource_id`, and UTC `timestamp`.
   - Audit trail tamper-resistance via append-only database constraints and WAL archiving.

3. **Security Incident Response Lifecycle (SEV-1 to SEV-4)**:
   - **SEV-1 (Critical)**: Active breach or privilege escalation; automated PagerDuty alert; 15-minute response SLA; immediate isolation of compromised tenant context.
   - **SEV-2 (High)**: Discovered unpatched vulnerability or worker queue compromise; 1-hour SLA.
   - **SEV-3 (Medium)**: Non-exploitable policy violation or rate-limit anomaly; 24-hour SLA.
   - **SEV-4 (Low)**: Informational security query or non-critical log error; 72-hour SLA.

4. **Recovery Procedures & Post-Incident Review (PIR)**:
   - Emergency API key & JWT secret rotation runbooks.
   - Blameless Post-Incident Review (PIR) mandatory within 48 hours of any SEV-1/SEV-2 incident, documenting root cause analysis, timeline, remediation items, and prevention controls.

5. **Breach Response & Regulatory Compliance**:
   - Customer notification protocol within 72 hours of verified security breach.
   - Evidence preservation runbooks ensuring database snapshots, WAL archives, and container logs are frozen for forensic analysis.

---

## 🔒 22. Integration Security Controls & External API Governance (Phase 9.1)

Phase 9.1 enforces strict security controls for external integrations with Atlassian Jira Cloud and GitHub Issues:

1. **AES-256 Secret Encryption at Rest**:
   - All external provider credentials (Jira API tokens, GitHub Personal Access Tokens) are encrypted at rest using AES-256-GCM / Fernet via `SecretEncryptionService`.
   - Plaintext credentials are **NEVER** logged, written to disk, or exposed in REST API payloads (secrets are masked in API responses e.g. `vn_token_********1234`).
2. **Controlled State Transition Layer**:
   - External ticket status changes pass through controlled state transition mappers (`ControlledJiraStatusMapper`, `ControlledGitHubStatusMapper`) before updating internal Vulnova finding lifecycle states (`DONE`/`CLOSED` -> `RESOLVED`, `IN_PROGRESS` -> `IN_REMEDIATION`).
   - Prevents external systems from directly mutating security posture without validation.
3. **Multi-Tenant Isolation**:
   - All integration configuration, ticket creation, and status synchronization calls enforce tenant boundaries (`organization_id = current_user.organization_id`). Cross-tenant access is rejected with HTTP 403 Forbidden / 404 Not Found.
4. **RBAC Permission Enforcement**:
   - `integrations:read`: `Role.VIEWER` (level 10+) — view integration status (secrets masked).
   - `integrations:create`: `Role.SECURITY_ANALYST` (level 20+) — create Jira/GitHub tickets.
   - `integrations:update`: `Role.SECURITY_ANALYST` (level 20+) — sync issue status.
   - `integrations:manage`: `Role.ADMIN` (level 30+) — save/update provider credentials.
5. **Immutable Security Audit Trail**:
   - Every integration operation records non-repudiable audit events (`integration.configuration_updated`, `integration.issue_created`, `integration.issue_synced`) capturing actor user ID, tenant ID, provider, issue ID, and timestamp.

---

## 🔔 23. Webhook Security Controls & Notification Governance (Phase 9.2)

Phase 9.2 enforces strict security controls for real-time Slack and Microsoft Teams security alert webhooks:

1. **Webhook Secret Token Protection**:
   - All Incoming Webhook URLs (which contain sensitive token secrets) are encrypted at rest using AES-256-GCM / Fernet via `SecretEncryptionService`.
   - Webhook URLs in REST API responses are strictly masked (`https://hooks.slack.com/services/T00/B00/*****XXXX`), eliminating token exposure in frontend client state.
2. **Resilient & Non-Blocking Alert Dispatching**:
   - Webhook notification delivery operates asynchronously without blocking core vulnerability processing, scan execution, or compliance evaluation.
   - HTTP errors, timeouts, or 500 responses from external webhooks are logged cleanly without causing application failure or unhandled exceptions.
3. **Multi-Tenant Boundary Enforcement**:
   - Channel configuration management and alert routing strictly enforce tenant isolation (`organization_id = current_user.organization_id`).
4. **RBAC Permission Enforcement**:
   - `notifications:read`: `Role.VIEWER` (level 10+) — list configured channels.
   - `notifications:create`: `Role.SECURITY_ANALYST` (level 20+) — send test notifications.
   - `notifications:update`: `Role.SECURITY_ANALYST` (level 20+) — update channel settings.
   - `notifications:manage`: `Role.ADMIN` (level 30+) — create, edit, or delete webhook channels.
5. **Audit Logging & Delivery Monitoring**:
   - Dispatches immutable security audit log events (`notification.channel_created`, `notification.channel_updated`, `notification.channel_deleted`, `notification.sent`, `notification.failed`) capturing delivery status, HTTP status codes, provider, and timestamp.

---

## 🛠️ 24. Pipeline Security Gates & CLI Token Security (Phase 9.3)

Phase 9.3 introduces security controls for CI/CD pipeline automation and CLI execution:

1. **CLI Token Protection & Hashing**:
   - CLI API tokens use `vn_cli_` prefix and SHA-256 digests (`APIKeyModel`). Raw tokens are returned once upon creation and unrecoverable from database queries.
2. **Zero Plaintext Secret Exposure in Logs**:
   - CLI tool logs never output API tokens, credentials, or sensitive vulnerability evidence snippets.
3. **Automated Pipeline Security Gates**:
   - Build security gates enforce policy thresholds (e.g. `CRITICAL >= 1`). Violations cause build failure (`exit code 1`) preventing vulnerable code promotion.
4. **Tenant Isolation & RBAC Protection**:
   - CLI endpoints enforce tenant boundaries (`organization_id = current_user.organization_id`).
   - Permissions: `cli:read` (`Role.VIEWER` level 10+), `cli:trigger` (`Role.SECURITY_ANALYST` level 20+), `cli:manage` (`Role.ADMIN` level 30+).
5. **Immutable Audit Trail**:
   - Records audit log events (`cli.token_created`, `cli.token_revoked`, `cli.scan_started`, `cli.scan_completed`, `cli.pipeline_failed`).

---

## 🛡️ 25. Security Control Verification & OWASP Validation Controls (Phase 10.1)

Phase 10.1 introduces automated security controls verifying platform and tenant posture against the **OWASP Top 10 (2021)** standard:

1. **Zero Database Table Duplication**:
   - In-memory validation engine operating without document archival tables or schema migrations (`Run -> Evaluate Category Assertions -> Record Audit Log -> Return DTO`).
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` token string (`suite_id`) recorded in security audit events (`validation.owasp_suite_started`, `validation.owasp_suite_completed`) for cross-system SIEM event correlation.
3. **Explainable Failure Diagnostics & Subsystem Mapping**:
   - Every category result returns diagnostic `failure_reason`, target `affected_subsystem` (e.g. `SecretEncryptionService`, `SSRFValidator`, `RBACPolicy`), and actionable `remediation_guidance`.
4. **Deep SSRF Egress Firewall Verification**:
   - Direct integration with `is_safe_target_url` verifying private IP range blocking (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`, AWS IMDS `169.254.169.254`) and DNS rebinding protections.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 🛡️ 26. API Security Controls Validation (Phase 10.2)

Phase 10.2 introduces automated API security controls verifying REST endpoints against the **OWASP API Security Top 10 (2023)** standard:

1. **Zero Database Table Duplication**:
   - In-memory API assertion engine operating without document archival tables or schema migrations (`Run -> Execute API Assertions -> Record Audit Event -> Return DTO`).
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Runtime `uuid4()` token string (`suite_id`) recorded in audit log events (`validation.api_security_suite_started`, `validation.api_security_suite_completed`).
3. **Explainable Failure Diagnostics & Endpoint Mapping**:
   - Every API category result returns diagnostic `failure_reason`, target `affected_endpoint` (e.g. `/api/v1/vulnerabilities/{id}`), `affected_subsystem` (e.g. `OrganizationIsolation`, `RateLimiter`), and actionable `remediation_guidance`.
4. **Deep BOLA & Security Boundary Verification**:
   - Asserts mandatory `organization_id` multi-tenant boundaries, IDOR protections, JWT signature validation, token expiry rules, and API key prefix rules (`vn_live_`, `vn_cli_`).
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 🛡️ 27. Infrastructure Security Control Validation (Phase 10.3)

Phase 10.3 introduces automated infrastructure security controls verifying deployment posture, containers, supply chain lockfiles, CI/CD pipelines, database security, logging, RBAC access controls, network SSRF firewalls, cloud metadata, and operational security readiness across all 10 Infrastructure Security categories:

1. **Zero Database Table Duplication**:
   - In-memory infrastructure assertion engine operating without document archival tables or schema migrations (`Run -> Execute Infrastructure Assertions -> Record Audit Event -> Return DTO`).
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Runtime `uuid4()` token string (`suite_id`) recorded in audit log events (`validation.infrastructure_suite_started`, `validation.infrastructure_suite_completed`).
3. **Explainable Failure Diagnostics & Component Mapping**:
   - Every infrastructure category result returns diagnostic `failure_reason`, target `affected_component` (e.g. `Dockerfile & Docker Compose Runtime`, `Dependency Lockfiles`), and actionable `remediation_guidance`.
4. **Deep Container, Supply Chain & Cloud Control Verification**:
   - Verifies non-root container execution (`USER appuser`), supply chain lockfiles (`pyproject.toml`, `package-lock.json`), CI/CD pipeline gate enforcement, database connection encryption, `AuditLogService` & alert webhooks (Slack/Teams), and AWS IMDS cloud metadata blocking.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 🛡️ 28. Platform Penetration Testing & Exploit Verification Controls (Phase 10.4)

Phase 10.4 introduces automated penetration test assertion controls executing active exploit verification scenarios simulating real-world attack vectors against platform API Gateway, Auth, Multi-Tenant Boundaries, Injections, SSRF Egress, Mass Assignment, Rate Limits, CORS, Error Leakages, and Webhooks across all 10 PenTest categories:

1. **Zero Database Table Duplication**:
   - In-memory penetration test assertion engine operating without document archival tables or schema migrations (`Run Penetration Suite -> Execute Exploit Assertions -> Record Audit Event -> Return DTO`).
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Runtime `uuid4()` token string (`suite_id`) recorded in audit log events (`validation.pentest_suite_started`, `validation.pentest_suite_completed`).
3. **Explainable Failure Diagnostics & Target Mapping**:
   - Every PenTest category result returns diagnostic `failure_reason`, target `affected_target` (e.g. `/api/v1/auth/login`, `/api/v1/vulnerabilities/{id}`), and actionable `remediation_guidance`.
4. **Deep Exploit Vector Verification**:
   - Verifies JWT signature tampering rejection, multi-tenant IDOR boundaries (`organization_id`), SQL/Command injection protection, AWS IMDS metadata exfiltration blocking (`is_safe_target_url`), rate limit DoS protection (`RateLimiter`), CORS origin whitelisting, production stack trace suppression, and webhook HMAC signature verification.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).







