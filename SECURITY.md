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
