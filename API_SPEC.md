# Vulnova — REST API & WebSocket Specification (API_SPEC.md)

This document provides the REST API endpoints, plugin manifest schemas, target scan authorization payloads, query parameters, request/response payload schemas, error formats, and WebSocket contracts for **Vulnova**.

---

## 🌐 1. API Protocol & Base URLs

- **API Gateway Base URL**: `https://api.vulnova.local/api/v1`
- **WebSocket Streaming URL**: `wss://api.vulnova.local/api/v1/ws`
- **Content Type**: `application/json`
- **Authentication Header**: `Authorization: Bearer <access_token>` or `X-API-Key: <api_key_hash>`

---

## 🚨 2. Standardized Error Response Envelope

All API errors return a standardized JSON error format:

```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "User does not have required Security Analyst permissions.",
    "details": [
      {
        "field": "role",
        "issue": "Required role: SECURITY_ANALYST or higher"
      }
    ],
    "timestamp": "2026-08-01T12:00:00Z",
    "correlation_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
}
```

---

## 📡 3. REST Endpoint Reference Matrix

### A. Authentication & Session Management (`/auth`)

#### `POST /auth/register`
- **Summary**: Register new user and organization.
- **Request Body**:
  ```json
  {
    "email": "analyst@enterprise.com",
    "password": "SecurePassword123!",
    "full_name": "Jane Doe",
    "organization_name": "Acme Corp"
  }
  ```
- **Response (201 Created)**: Returns user and org tokens.

---

### B. Discovery & Target Management (`/targets`)

#### `POST /targets`
- **Summary**: Create new scan target asset with legal scope parameters.
- **Request Body**:
  ```json
  {
    "name": "Production E-Commerce API",
    "target_url": "https://api.shop.enterprise.com",
    "environment": "PRODUCTION"
  }
  ```

---

### C. Assessment Execution & Profile Management (`/assessments`)

#### `GET /api/v1/assessments/profiles`
- **Summary**: List all available enterprise scan profiles and default execution policies.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `scans:read` permission.
- **Response (200 OK)**:
  ```json
  [
    {
      "id": "web_scan",
      "name": "Web Vulnerability Scan",
      "description": "Web application assessment (SQLi, XSS, Headers, Auth Cookies).",
      "plugin_ids": ["sql_injection_plugin", "xss_plugin", "security_headers_plugin", "auth_security_plugin"],
      "default_policy": {
        "concurrency_limit": 5,
        "rate_limit_rps": 10,
        "respect_robots_txt": true,
        "scope_include_patterns": [],
        "scope_exclude_patterns": [],
        "max_crawl_depth": 3,
        "max_requests": 500,
        "timeout_seconds": 30.0,
        "stop_on_critical": false
      }
    }
  ]
  ```

#### `POST /api/v1/assessments`
- **Summary**: Dispatch dynamic vulnerability assessment scan with scan profile selection and execution policy overrides.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `scans:trigger` permission.
- **Request Body**:
  ```json
  {
    "target_url": "https://api.shop.enterprise.com",
    "profile_id": "web_scan",
    "plugins": ["sql_injection_plugin", "xss_plugin"],
    "policy_override": {
      "concurrency_limit": 10,
      "rate_limit_rps": 20,
      "stop_on_critical": true
    }
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "id": "c73bcd8f-0e42-4f32-8419-756c66d214a1",
    "target_url": "https://api.shop.enterprise.com",
    "status": "COMPLETED",
    "profile_id": "web_scan",
    "enabled_plugins": ["sql_injection_plugin", "xss_plugin"],
    "policy": {
      "concurrency_limit": 10,
      "rate_limit_rps": 20,
      "respect_robots_txt": true,
      "scope_include_patterns": [],
      "scope_exclude_patterns": [],
      "max_crawl_depth": 3,
      "max_requests": 500,
      "timeout_seconds": 30.0,
      "stop_on_critical": true
    },
    "total_findings": 2,
    "findings": [],
    "duration_seconds": 4.12,
    "error_message": null,
    "created_at": "2026-08-03T00:00:00Z"
---

### D. Enterprise Asset Inventory & Posture Intelligence (`/assets`)

#### `GET /api/v1/assets/inventory`
- **Summary**: List tenant asset inventory nodes enriched with risk posture scores, findings count, and running technologies.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `assets:read` permission.
- **Query Parameters**: `node_type` (optional), `min_risk_score` (optional float), `search` (optional string), `page`, `limit`.
- **Response (200 OK)**:
  ```json
  {
    "total": 1,
    "items": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "node_type": "TARGET_DOMAIN",
        "name": "shop.enterprise.com",
        "value": "shop.example.com",
        "risk_score": 85.5,
        "risk_level": "CRITICAL",
        "total_findings": 3,
        "findings_by_severity": { "CRITICAL": 1, "HIGH": 2 },
        "technologies": ["FastAPI", "PostgreSQL"],
        "created_at": "2026-08-03T00:00:00Z",
        "updated_at": "2026-08-03T00:00:00Z"
      }
    ]
  }
  ```

#### `GET /api/v1/assets/{asset_id}`
- **Summary**: Query detailed inventory summary for a single asset node.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `assets:read` permission.
- **Response (200 OK)**:
  ```json
  {
    "asset": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "node_type": "TARGET_DOMAIN",
      "name": "shop.enterprise.com",
      "value": "shop.example.com",
      "risk_score": 85.5,
      "risk_level": "CRITICAL",
      "total_findings": 3,
      "findings_by_severity": { "CRITICAL": 1, "HIGH": 2 },
      "technologies": ["FastAPI", "PostgreSQL"],
      "created_at": "2026-08-03T00:00:00Z",
      "updated_at": "2026-08-03T00:00:00Z"
    },
    "technologies": [
      {
        "id": "9a12b34c-5678-90ef-a1b2-c3d4e5f67890",
        "name": "FastAPI",
        "category": "BACKEND_FRAMEWORK",
        "version": "0.110.0"
      }
    ],
    "findings": [],
    "relationships": []
  }
  ```

#### `GET /api/v1/assets/{asset_id}/findings`
- **Summary**: List security findings affecting a specific asset.
- **RBAC Guard**: Requires authentication and `findings:read` permission.

#### `GET /api/v1/assets/{asset_id}/technologies`
- **Summary**: List technologies running on a specific asset.
- **RBAC Guard**: Requires authentication and `assets:read` permission.

#### `GET /api/v1/assets/trends`
- **Summary**: Query organizational risk score trajectory and historical posture snapshots over time.
- **RBAC Guard**: Requires authentication and `assets:read` permission.
- **Response (200 OK)**:
  ```json
  {
    "current_avg_risk_score": 45.2,
    "previous_avg_risk_score": 52.0,
    "net_risk_delta": -6.8,
    "risk_trend_direction": "DECREASING",
    "total_snapshots": 5,
    "snapshots": []
  }
  ```

#### `GET /api/v1/assets/{asset_id}/history`
- **Summary**: Query historical posture timeline and change events for a specific asset node.
- **RBAC Guard**: Requires authentication and `assets:read` permission.

#### `GET /api/v1/findings/history`
- **Summary**: Query vulnerability finding lifecycle status transitions (`NEW`, `RESOLVED`, `REOPENED`).
- **RBAC Guard**: Requires authentication and `findings:read` permission.

#### `GET /api/v1/security/posture/timeline`
- **Summary**: Query aggregated security posture delta change events (`ASSET_ADDED`, `ASSET_REMOVED`, `TECH_UPDATED`, `FINDING_NEW`, `FINDING_RESOLVED`, `FINDING_REOPENED`).
- **RBAC Guard**: Requires authentication and `assets:read` permission.

#### `PATCH /api/v1/findings/{finding_id}/triage`
- **Summary**: Triage a security finding status (`UNREVIEWED`, `CONFIRMED`, `FALSE_POSITIVE`, `RISK_ACCEPTED`, `REMEDIATED`, `REOPENED`).
- **RBAC Guard**: Requires authentication and `findings:triage` permission (`SECURITY_ANALYST`+).

---

### E. Vulnerability Intelligence & Triage (`/vulnerabilities`)

#### `GET /api/v1/vulnerabilities/{finding_id}`
- **Summary**: Query comprehensive vulnerability intelligence record, CVSS/EPSS scores, risk context, scan origin, and triage history.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `findings:read` permission.
- **Response (200 OK)**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "SQL Injection in Authentication API",
    "description": "Unsanitized login parameter vulnerable to blind SQL injection.",
    "severity": "CRITICAL",
    "category": "INJECTION",
    "cve_id": "CVE-2024-9999",
    "cwe_id": "CWE-89",
    "cvss": { "version": "3.1", "base_score": 9.8, "exploitability_score": 3.9, "impact_score": 5.9 },
    "epss": { "epss_score": 0.95, "percentile": 0.99 },
    "risk_context": { "composite_risk_score": 95.0, "remediation_sla_hours": 24, "risk_level": "CRITICAL", "affected_asset_count": 1 },
    "scan_origin": { "job_id": "uuid", "target_name": "https://api.staging.enterprise.com", "target_environment": "PRODUCTION", "scan_profile": "full_assessment" },
    "triage_status": "UNREVIEWED",
    "triage_history": [],
    "created_at": "2026-08-01T10:00:00Z"
  }
  ```

#### `GET /api/v1/vulnerabilities/{finding_id}/evidence`
- **Summary**: Query multi-modal proof evidence artifacts (HTTP exchanges, screenshots, DOM snapshots, plugin output) for a finding.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `findings:read` permission.

#### `GET /api/v1/vulnerabilities/{finding_id}/attack-path`
- **Summary**: Query graph visualization nodes describing vulnerability exploitation progression.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `findings:ai_attack_path` permission.

#### `GET /api/v1/vulnerabilities/{finding_id}/remediation`
- **Summary**: Query AI remediation plan, fix steps, code patch suggestions, and verification checklist.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `findings:ai_remediate` permission.

#### `POST /api/v1/vulnerabilities/{finding_id}/remediation-ai`
- **Summary**: Trigger on-demand AI remediation engine synthesis for advisory code fixes.
- **RBAC Guard**: Requires authentication (`get_current_user_or_api_key`) and `findings:ai_remediate` permission (`SECURITY_ANALYST`+).

- **Request Body**:
  ```json
  {
    "status": "CONFIRMED",
    "comment": "Verified valid SQL injection vulnerability.",
    "risk_accepted_until": "2026-12-31T23:59:59Z"
  }
  ```

#### `POST /api/v1/findings/triage/bulk`
- **Summary**: Bulk triage multiple security findings in a single request.
- **RBAC Guard**: Requires authentication and `findings:triage` permission (`SECURITY_ANALYST`+).

#### `GET /api/v1/findings/{finding_id}/triage-history`
- **Summary**: Query historical triage audit timeline for a finding.
- **RBAC Guard**: Requires authentication and `findings:read` permission.

#### `POST /api/v1/findings/suppression-rules`
- **Summary**: Create an automated false-positive finding suppression rule.
- **RBAC Guard**: Requires authentication and `findings:suppress` permission (`ADMIN`+).

#### `GET /api/v1/findings/suppression-rules`
- **Summary**: List active automated finding suppression rules for tenant organization.
- **RBAC Guard**: Requires authentication and `findings:read` permission.

#### `DELETE /api/v1/findings/suppression-rules/{rule_id}`
- **Summary**: Deactivate or delete an automated finding suppression rule.
- **RBAC Guard**: Requires authentication and `findings:suppress` permission (`ADMIN`+).

#### `POST /api/v1/ai/chat/completions`
- **Summary**: Execute AI chat completion request across configured gateway providers with automatic fallback & health tracking.
- **RBAC Guard**: Requires authentication and `findings:ai_analyze` permission (`SECURITY_ANALYST`+).
- **Request Body**:
  ```json
  {
    "messages": [
      { "role": "system", "content": "You are Vulnova, an expert AI Security Analyst." },
      { "role": "user", "content": "Analyze the following security finding context:\n..." }
    ],
    "model_alias": "gpt-4o",
    "max_tokens": 4096,
    "temperature": 0.2
  }
  ```

#### `POST /api/v1/ai/providers`
- **Summary**: Configure a tenant-isolated LLM provider with encrypted API key (AES-256-GCM).
- **RBAC Guard**: Requires authentication and `organization:update` permission (`ADMIN`+).

#### `GET /api/v1/ai/providers`
- **Summary**: List active configured LLM providers for tenant organization.
- **RBAC Guard**: Requires authentication and `findings:ai_analyze` permission.

#### `POST /api/v1/ai/models`
- **Summary**: Register supported LLM model metadata, context token limits, and pricing.
- **RBAC Guard**: Requires authentication and `organization:update` permission (`ADMIN`+).

#### `GET /api/v1/ai/models`
- **Summary**: List registered LLM models for organization.
- **RBAC Guard**: Requires authentication and `findings:ai_analyze` permission.

#### `POST /api/v1/ai/prompts`
- **Summary**: Create a new immutable version of a security prompt template (`version = max_version + 1`).
- **RBAC Guard**: Requires authentication and `organization:update` permission (`ADMIN`+).

#### `GET /api/v1/ai/prompts`
- **Summary**: List active security prompt templates for organization.
- **RBAC Guard**: Requires authentication and `findings:ai_analyze` permission.

#### `GET /api/v1/ai/usage`
- **Summary**: Query organizational token consumption, latency, and estimated USD cost analytics.
- **RBAC Guard**: Requires authentication and `findings:ai_analyze` permission.

---

### D. Security Plugin Management (`/plugins`)

#### `GET /plugins`
- **Summary**: List installed security assessment plugins and active `plugin.yaml` manifests.
- **Response (200 OK)**:
  ```json
  {
    "plugins": [
      {
        "id": "vuln-dast-sqli-v1",
        "name": "Advanced SQL Injection Detector",
        "version": "1.2.0",
        "category": "INJECTION",
        "severity": "CRITICAL",
        "cwe_mapping": ["CWE-89"],
        "owasp_mapping": ["A03:2021-Injection"]
      }
    ]
  }
  ```

#### `POST /plugins/register`
- **Summary**: Register or update custom enterprise plugin manifest (`plugin.yaml`).

---

### E. Finding Triage & AI Intelligence (`/findings`)

#### `GET /findings`
- **Summary**: List all discovered security findings for an organization enriched with normalized risk metrics and multi-modal evidence metadata.
- **Response (200 OK)**:
  ```json
  [
    {
      "id": "f83b2a19-4c3d-4e5f-8a1b-2c3d4e5f6a7b",
      "assessment_job_id": "c73bcd8f-0e42-4f32-8419-756c66d214a1",
      "plugin_id": "xss_plugin",
      "title": "Reflected Cross-Site Scripting (XSS)",
      "description": "Reflected XSS vulnerability detected in query parameter.",
      "severity": "HIGH",
      "category": "INJECTION",
      "cve_id": null,
      "cwe_id": "CWE-79",
      "remediation": "Sanitize and HTML-encode user input prior to rendering.",
      "evidence": { "probe_url": "https://example.com/search?q=\"><vlnv_xss_probe>" },
      "cvss": { "version": "3.1", "base_score": 7.5, "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N" },
      "epss": { "epss_score": 0.85, "percentile": 0.92 },
      "risk_score": 82.5,
      "confidence": "HIGH",
      "is_duplicate": false,
      "canonical_finding_id": null,
      "fix_sla_hours": 72,
      "evidence_count": 5,
      "evidence_available": true,
      "artifacts": [
        {
          "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
          "finding_id": "f83b2a19-4c3d-4e5f-8a1b-2c3d4e5f6a7b",
          "artifact_type": "SCREENSHOT",
          "storage_path": "uploads/evidence/org_123/finding_456/screenshot.png",
          "metadata": { "url": "https://example.com/search" },
          "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "created_at": "2026-08-02T22:00:00Z"
        }
      ],
      "created_at": "2026-08-02T22:00:00Z"
    }
  ]
  ```

#### `GET /findings/{finding_id}/evidence`
- **Summary**: Retrieve detailed evidence records (screenshots, HTTP request/response dumps, proof hashes) associated with finding.

#### `POST /ai/findings/{finding_id}/explain`
- **Summary**: Generate AI finding explanation (`findings:ai_explain` permission required).
- **Response (201 Created)**:
  ```json
  {
    "id": "explanation_uuid",
    "finding_id": "finding_uuid",
    "vulnerability_summary": "SQL Injection allowing database extraction.",
    "technical_root_cause": "Direct string concatenation in SQL query builder.",
    "affected_asset_context": "Login authentication API endpoint.",
    "exploitability_analysis": "High exploitability; public tool availability.",
    "business_impact": "Potential data breach and unauthorized database access.",
    "attack_prerequisites": "Network access to login form.",
    "severity_reasoning": "High CVSS base score of 8.5.",
    "remediation_priority": "P1 - Fix immediately within 72 hours.",
    "model_used": "gpt-4o",
    "provider_used": "OPENAI",
    "prompt_version": 1,
    "status": "COMPLETED",
    "created_at": "2026-08-03T12:00:00Z"
  }
  ```

#### `GET /ai/findings/{finding_id}/explanation`
- **Summary**: Retrieve latest AI explanation for a finding (`findings:read` permission required).

#### `POST /ai/findings/{finding_id}/impact`
- **Summary**: Generate AI impact analysis report (`findings:ai_explain` permission required).
- **Response (201 Created)**:
  ```json
  {
    "id": "impact_uuid",
    "finding_id": "finding_uuid",
    "technical_impact_summary": "Full compromise of web application server host.",
    "executive_impact_summary": "Critical threat to customer data confidentiality.",
    "risk_justification": "Maximum risk rating driven by high EPSS exploit probability (92%).",
    "affected_business_components": "Core Payment Processing Service.",
    "cvss_interpretation": "CVSS 9.8 Critical rating.",
    "epss_context": "92nd percentile exploit probability.",
    "exposure_assessment": "Publicly exposed Internet facing API endpoint.",
    "evidence_correlation": "Proof-of-exploit HTTP request dump confirms remote shell execution.",
    "model_used": "claude-3-5-sonnet",
    "provider_used": "ANTHROPIC",
    "prompt_version": 1,
    "status": "COMPLETED",
    "created_at": "2026-08-03T12:00:00Z"
  }
  ```

#### `GET /ai/findings/{finding_id}/impact`
- **Summary**: Retrieve latest AI impact analysis report (`findings:read` permission required).

#### `POST /ai/findings/{finding_id}/attack-paths`
- **Summary**: Synthesize AI attack path graph (`findings:ai_attack_path` permission required).
- **Response (201 Created)**:
  ```json
  {
    "id": "path_uuid",
    "root_finding_id": "finding_uuid",
    "source_asset_id": "asset_uuid",
    "target_asset_id": "asset_uuid",
    "title": "SQL Injection to Database Takeover",
    "attack_summary": "Attacker leverages unescaped SQL parameter to extract admin hashes and escalate privileges.",
    "composite_risk_score": 88.5,
    "confidence_score": 0.92,
    "model_used": "gpt-4o",
    "provider_used": "OPENAI",
    "prompt_version": 1,
    "status": "GENERATED",
    "steps": [
      {
        "id": "step_uuid",
        "sequence_number": 1,
        "step_type": "INITIAL_ACCESS",
        "title": "Exploit SQL Injection",
        "description": "Send crafted SQL payload to admin search form.",
        "mitre_tactic": "Initial Access",
        "mitre_technique_id": "T1190",
        "mitre_technique_name": "Exploit Public-Facing Application",
        "attacker_action": "POST /search with payload",
        "required_privilege": "Unauthenticated",
        "confidence_score": 0.95
      }
    ],
    "created_at": "2026-08-03T12:00:00Z"
  }
  ```

#### `GET /ai/findings/{finding_id}/attack-paths`
- **Summary**: Retrieve all synthesized attack paths for a specific finding (`findings:read` permission required).

#### `GET /ai/attack-paths/{id}`
- **Summary**: Retrieve single attack path by ID with all steps (`findings:read` permission required).

#### `GET /ai/attack-paths`
- **Summary**: List organizational attack path history (`findings:read` permission required).

#### `PATCH /ai/attack-paths/{id}/review`
- **Summary**: Record SOC analyst review status (`ACCEPTED`, `REJECTED`, `REVIEWED`) and notes (`findings:ai_attack_path` permission required).

#### `POST /ai/findings/{finding_id}/remediation`
- **Summary**: Synthesize AI remediation plan with non-executable patch suggestions (`findings:ai_remediate` permission required).
- **Response (201 Created)**:
  ```json
  {
    "id": "remed_uuid",
    "root_finding_id": "finding_uuid",
    "attack_path_id": "path_uuid",
    "cve_id": "CVE-2024-8888",
    "cwe_id": "CWE-89",
    "affected_version": "1.2.0",
    "fixed_version": "1.2.1",
    "title": "Remediation Plan: Parametrize SQL Queries",
    "summary": "Replace concatenated SQL strings with parameterized queries using ORM.",
    "technical_solution": "Use bound parameters in SQL query execution.",
    "business_solution": "Prevents unauthorized database access.",
    "risk_reduction_explanation": "Eliminates SQL injection vulnerability completely.",
    "validation_strategy": "Re-run assessment plugin.",
    "composite_risk_score": 85.0,
    "ai_confidence_score": 0.96,
    "effectiveness_confidence_score": 0.98,
    "requires_backup": true,
    "requires_downtime": false,
    "rollback_available": true,
    "model_used": "gpt-4o",
    "provider_used": "OPENAI",
    "prompt_version": 1,
    "status": "GENERATED",
    "steps": [
      {
        "id": "step_uuid",
        "sequence_number": 1,
        "step_type": "CODE_PATCH",
        "title": "Parametrize SQL query in auth.py",
        "description": "Refactor raw execute to use ORM query binding.",
        "affected_component": "backend/app/api/v1/auth.py",
        "recommended_action": "Update query to use bound parameters",
        "validation_command": "pytest tests/test_auth.py",
        "rollback_strategy": "Git revert commit",
        "confidence_score": 0.95
      }
    ],
    "patch_suggestions": [
      {
        "id": "patch_uuid",
        "language": "PYTHON",
        "file_type": "SOURCE_CODE",
        "target_file_path": "backend/app/api/v1/auth.py",
        "original_code_snippet": "cursor.execute(f'SELECT * FROM users WHERE name={name}')",
        "proposed_patch_diff": "--- auth.py\n+++ auth.py\n-cursor.execute(f'SELECT * FROM users WHERE name={name}')\n+cursor.execute('SELECT * FROM users WHERE name=:name', {'name': name})",
        "explanation": "Replaces string interpolation with parameter binding.",
        "security_impact_notes": "Completely mitigates SQL injection.",
        "confidence_score": 0.97
      }
    ],
    "created_at": "2026-08-03T14:00:00Z"
  }
  ```

#### `GET /ai/findings/{finding_id}/remediation`
- **Summary**: Retrieve all synthesized remediation plans for a finding (`findings:read` permission required).

#### `GET /ai/remediation/{id}`
- **Summary**: Retrieve single remediation plan by ID with steps and patch suggestions (`findings:read` permission required).

#### `GET /ai/remediation`
- **Summary**: List organizational remediation history (`findings:read` permission required).

#### `PATCH /ai/remediation/{id}/review`
- **Summary**: Record SOC analyst review status (`APPROVED`, `REJECTED`, `UNDER_REVIEW`, `IMPLEMENTED`, `VERIFIED`, `VALIDATION_FAILED`) and notes (`findings:ai_remediate` permission required).

#### `POST /ai/findings/{finding_id}/confidence-analysis`
- **Summary**: Synthesize AI false-positive and confidence assessment (`findings:ai_confidence` permission required).
- **Response (201 Created)**:
  ```json
  {
    "id": "conf_uuid",
    "finding_id": "finding_uuid",
    "classification": "TRUE_POSITIVE",
    "confidence_score": 0.95,
    "evidence_quality_score": 0.92,
    "reasoning": "High confidence SQL injection confirmed by error payload response.",
    "supporting_evidence": "HTTP 500 error containing PostgreSQL syntax exception.",
    "contradicting_evidence": "None noted.",
    "missing_information": "None.",
    "validation_requirements": "Re-run sqli_plugin with sleep payload.",
    "recommendation": "Prioritize immediate patch deployment.",
    "composite_risk_score": 85.0,
    "model_used": "gpt-4o",
    "provider_used": "OPENAI",
    "prompt_version": 1,
    "status": "GENERATED",
    "similarity_matches": [
      {
        "id": "sim_uuid",
        "source_finding_id": "finding_uuid",
        "matched_finding_id": "cand_uuid",
        "similarity_score": 0.85,
        "similarity_reason": "Identical CVE identifier (CVE-2024-1111); Identical CWE category (CWE-89)",
        "matched_signals": ["CVE", "CWE", "PLUGIN_ID"],
        "status": "GENERATED",
        "created_at": "2026-08-03T14:00:00Z"
      }
    ],
    "predicted_confidence_score": null,
    "analyst_final_decision": null,
    "confidence_accuracy_delta": null,
    "feedback_timestamp": null,
    "created_at": "2026-08-03T14:00:00Z"
  }
  ```

#### `GET /ai/findings/{finding_id}/confidence-analysis`
- **Summary**: Retrieve latest confidence analysis assessment for a finding (`findings:read` permission required).

#### `GET /ai/confidence-analysis`
- **Summary**: List organizational confidence analysis history (`findings:read` permission required).

#### `POST /ai/findings/{finding_id}/similarity-check`
- **Summary**: Correlate finding against organizational history across 8 matching signals (`findings:ai_confidence` permission required).

#### `GET /ai/finding-similarity/{finding_id}`
- **Summary**: Retrieve existing similarity matches for a finding (`findings:read` permission required).

#### `PATCH /ai/confidence-analysis/{id}/review`
- **Summary**: Record SOC analyst review feedback and track AI confidence score calibration metadata (`findings:ai_confidence` permission required).

#### `POST /ai/knowledge/documents`
- **Summary**: Ingest security reference document or company policy into vector store (`knowledge:write` permission required).
- **Response (201 Created)**:
  ```json
  {
    "id": "doc_uuid",
    "organization_id": null,
    "source_type": "OWASP",
    "ingestion_source": "MANUAL_UPLOAD",
    "title": "OWASP SQL Injection Prevention Cheat Sheet",
    "external_ref_id": "OWASP-A03:2021",
    "description": "Official OWASP guidelines.",
    "version": "2.0",
    "status": "INDEXED",
    "chunk_size_tokens": 512,
    "chunk_overlap_tokens": 64,
    "chunk_count": 5,
    "token_count": 2200,
    "embedding_model": "text-embedding-3-small",
    "embedding_dimension": 1536,
    "source_url": "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    "source_author": "OWASP Foundation",
    "published_date": "2026-01-01",
    "last_updated_date": "2026-06-01",
    "metadata_json": {},
    "error_message": null,
    "created_by": "user_uuid",
    "reviewed_by": null,
    "reviewed_at": null,
    "created_at": "2026-08-03T14:00:00Z",
    "updated_at": "2026-08-03T14:00:00Z"
  }
  ```

#### `GET /ai/knowledge/documents`
- **Summary**: List security knowledge documents accessible to tenant with pagination (`knowledge:read` permission required).

#### `GET /ai/knowledge/documents/{document_id}`
- **Summary**: Retrieve single knowledge document details by ID (`knowledge:read` permission required).

#### `PATCH /ai/knowledge/documents/{document_id}/review`
- **Summary**: Record analyst governance approval status (`APPROVED`, `REJECTED`, `INDEXED`, `ARCHIVED`) (`knowledge:write` permission required).

#### `DELETE /ai/knowledge/documents/{document_id}`
- **Summary**: Delete knowledge document and associated vector chunks (`knowledge:delete` permission required).

#### `POST /ai/rag/search`
- **Summary**: Execute semantic vector similarity search across active security knowledge base chunks (`knowledge:read` permission required).
- **Response (200 OK)**:
  ```json
  {
    "query": "SQL injection prevention",
    "results_count": 1,
    "results": [
      {
        "chunk_id": "chunk_uuid",
        "document_id": "doc_uuid",
        "document_title": "OWASP SQL Injection Prevention Cheat Sheet",
        "source_type": "OWASP",
        "content_text": "Use parameterized queries and prepared statements to prevent SQL injection vulnerabilities.",
        "similarity_score": 0.9254,
        "external_ref_id": "OWASP-A03:2021",
        "source_url": "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
        "source_author": "OWASP Foundation",
        "chunk_metadata": {"source_type": "OWASP"}
      }
    ],
    "search_latency_ms": 4
  }
  ```

#### `POST /ai/findings/{finding_id}/rag-context`
- **Summary**: Generate tailored RAG knowledge context block for a security finding (`findings:read` permission required).

#### `POST /ai/copilot/sessions`
- **Summary**: Initialize a new multi-turn AI Security Copilot investigation session (`copilot:manage` permission required).
- **Response (201 Created)**:
  ```json
  {
    "id": "session_uuid",
    "organization_id": "org_uuid",
    "user_id": "user_uuid",
    "title": "Investigating Critical SQLi",
    "status": "ACTIVE",
    "focused_finding_id": "finding_uuid",
    "model_alias": "default",
    "temperature": 0.2,
    "total_tokens": 0,
    "message_count": 0,
    "created_at": "2026-08-03T18:00:00Z",
    "updated_at": "2026-08-03T18:00:00Z"
  }
  ```

#### `GET /ai/copilot/sessions`
- **Summary**: List Copilot investigation sessions for organization with pagination (`copilot:read` permission required).

#### `GET /ai/copilot/sessions/{session_id}`
- **Summary**: Retrieve single Copilot investigation session details by ID (`copilot:read` permission required).

#### `PATCH /ai/copilot/sessions/{session_id}`
- **Summary**: Update session title, status, or focused finding ID (`copilot:manage` permission required).

#### `DELETE /ai/copilot/sessions/{session_id}`
- **Summary**: Delete Copilot investigation session and message history (`copilot:manage` permission required).

#### `POST /ai/copilot/sessions/{session_id}/messages`
- **Summary**: Send analyst query to Copilot assistant and receive grounded AI response with explainability metadata (`copilot:chat` permission required).
- **Response (200 OK)**:
  ```json
  {
    "session_id": "session_uuid",
    "user_message": {
      "id": "user_msg_uuid",
      "session_id": "session_uuid",
      "organization_id": "org_uuid",
      "role": "USER",
      "content": "How do I fix this SQL injection?",
      "agent_type": "SECURITY_ANALYST",
      "token_count": 8,
      "created_at": "2026-08-03T18:01:00Z"
    },
    "assistant_message": {
      "id": "assistant_msg_uuid",
      "session_id": "session_uuid",
      "organization_id": "org_uuid",
      "role": "ASSISTANT",
      "content": "### AI Security Copilot Analysis (REMEDIATION)\nUse parameterized queries.",
      "agent_type": "REMEDIATION",
      "token_count": 45,
      "response_confidence_score": 0.92,
      "sources_used": [{"title": "OWASP SQLi Prevention", "source_url": "https://owasp.org"}],
      "knowledge_chunks_used": [{"chunk_id": "chunk_uuid", "similarity_score": 0.88}],
      "tools_called": [{"tool_name": "get_remediation_plan", "execution_status": "SUCCESS"}],
      "reasoning_summary": "Synthesized using OWASP standards and remediation tool output.",
      "model_used": "default",
      "prompt_version": "1.0",
      "response_evaluation_metadata": {"agent_type": "REMEDIATION"},
      "created_at": "2026-08-03T18:01:02Z"
    },
    "agent_type": "REMEDIATION",
    "sources_used": [
      {
        "source_type": "OWASP",
        "title": "OWASP SQLi Prevention",
        "external_ref_id": "OWASP-A03:2021",
        "source_url": "https://owasp.org",
        "similarity_score": 0.88
      }
    ],
    "tools_executed": [
      {
        "tool_name": "get_remediation_plan",
        "input_params": {"finding_id": "finding_uuid"},
        "execution_status": "SUCCESS",
        "summary": "Executed get_remediation_plan in 12ms"
      }
    ],
    "response_confidence_score": 0.92,
    "total_session_tokens": 53
  }
  ```

#### `GET /ai/copilot/sessions/{session_id}/messages`
- **Summary**: Retrieve full message history for a Copilot investigation session (`copilot:read` permission required).

#### `POST /ai/copilot/feedback`
- **Summary**: Record SOC analyst rating (1-5 stars) and evaluation feedback (`copilot:feedback` permission required).

#### `POST /workers/heartbeat`
- **Summary**: Register worker node or update heartbeat in cluster inventory (`workers:manage` permission required).

#### `GET /workers/nodes`
- **Summary**: List worker nodes in cluster for organization with optional status filtering (`workers:read` permission required).

#### `GET /workers/metrics`
- **Summary**: Compute overall worker cluster metrics and active capacity (`workers:read` permission required).
- **Response (200 OK)**:
  ```json
  {
    "organization_id": "org_uuid",
    "total_nodes": 3,
    "active_nodes": 3,
    "total_capacity": 12,
    "current_active_tasks": 2,
    "avg_cpu_percent": 18.5,
    "avg_memory_usage_mb": 256.0
  }
  ```

#### `POST /workers/jobs/dispatch`
- **Summary**: Dispatch scan job to Celery priority queues with container sandbox security validation (`scans:dispatch` permission required).
- **Response (202 Accepted)**:
  ```json
  {
    "id": "task_exec_uuid",
    "task_id": "task-uuid-1234",
    "scan_id": "scan_uuid",
    "organization_id": "org_uuid",
    "requested_by": "user_uuid",
    "priority": "scans.default",
    "task_name": "execute_scan_job_task",
    "state": "PENDING",
    "retry_count": 0,
    "runtime_ms": 0,
    "created_at": "2026-08-03T19:00:00Z"
  }
  ```

#### `POST /workers/tasks/{task_id}/cancel`
- **Summary**: Cancel running worker task execution and signal sandbox termination (`scans:dispatch` permission required).

#### `GET /workers/tasks/{task_id}`
- **Summary**: Retrieve task execution record by task_id with tenant boundary checks (`workers:read` permission required).

---

### M. Scan Target Management & Authorization (`/scan-targets`) (Phase 6.2)

#### `POST /scan-targets`
- **Summary**: Register a new scan target for the authenticated organization (`targets:create` permission required).
- **Request Body**:
  ```json
  {
    "name": "Production E-Commerce API",
    "target_url": "https://api.example.com",
    "environment": "PRODUCTION"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "id": "target_uuid",
    "organization_id": "org_uuid",
    "name": "Production E-Commerce API",
    "target_url": "https://api.example.com",
    "environment": "PRODUCTION",
    "status": "ACTIVE",
    "is_ownership_verified": false,
    "ownership_verification_token": "vulnova-verify-a1b2c3d4e5f67890",
    "created_at": "2026-08-03T20:00:00Z"
  }
  ```

#### `GET /scan-targets`
- **Summary**: List all registered scan targets for the organization (`targets:read` permission required). Supports optional `?status=ACTIVE` query parameter filter.

#### `GET /scan-targets/{target_id}`
- **Summary**: Get details of a specific scan target by UUID (`targets:read` permission required).

#### `PUT /scan-targets/{target_id}`
- **Summary**: Update name, environment, or status of a scan target (`targets:update` permission required).

#### `DELETE /scan-targets/{target_id}`
- **Summary**: Archive (soft-delete) a scan target (`targets:delete` permission required). Sets status to `ARCHIVED`. Archived targets cannot be scanned.

---

### N. Scan Lifecycle State Machine & Retry Engine (`/assessments`) (Phase 6.3)

#### `GET /assessments/{assessment_id}/state`
- **Summary**: Retrieve detailed state machine status, step, and retry metrics for a scan job (`scans:read` permission required).
- **Response (200 OK)**:
  ```json
  {
    "job_id": "job_uuid",
    "organization_id": "org_uuid",
    "target_url": "https://api.example.com",
    "execution_state": "ASSESSING",
    "status": "ASSESSING",
    "current_step": "Plugin Vulnerability Scanning",
    "retry_count": 0,
    "max_retries": 3,
    "last_error": null,
    "started_at": "2026-08-03T20:30:00Z",
    "completed_at": null,
    "is_terminal": false
  }
  ```

#### `POST /assessments/{assessment_id}/retry`
- **Summary**: Manually trigger retry for a failed or cancelled assessment job (`scans:retry` permission required). Transitions state to `QUEUED`.

#### `POST /assessments/{assessment_id}/cancel`
- **Summary**: Signal abort and transition active assessment job to `CANCELLED` (`scans:cancel` permission required). Releases target lock.

---

### O. Real-Time Scan Progress & WebSocket Event Stream (`/ws/scans` & `/assessments/{id}/events`) (Phase 6.4)

#### `WebSocket /ws/scans/{scan_id}?token={jwt}`
- **Protocol**: `ws://` or `wss://`
- **Query Parameter**: `token` (string, required) - Valid JWT Access Token
- **Close Codes**:
  - `4001`: Missing or invalid JWT access token (Unauthorized)
  - `4003`: Cross-tenant mismatch or missing `scans:read` permission (Forbidden)
  - `4004`: Assessment job not found (Not Found)
  - `4008`: Maximum organization connection limit (50) exceeded
- **Sample Event Payload (`STATE_CHANGE`)**:
  ```json
  {
    "event_id": "evt_123456789abc",
    "job_id": "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18",
    "organization_id": "6bcb30b5-148f-4a15-baf2-3e5598512bd8",
    "event_type": "STATE_CHANGE",
    "payload": {
      "previous_state": "CRAWLING",
      "new_state": "ASSESSING",
      "current_step": "Plugin Vulnerability Scanning"
    },
    "timestamp": "2026-08-04T01:10:00Z"
  }
  ```

#### `GET /assessments/{scan_id}/events`
- **Summary**: Retrieve recent execution event history for a scan job (`scans:read` permission required).
- **Response (200 OK)**:
  ```json
  {
    "job_id": "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18",
    "total_events": 1,
    "events": [
      {
        "event_id": "evt_init_8d48aca2",
        "job_id": "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18",
        "organization_id": "6bcb30b5-148f-4a15-baf2-3e5598512bd8",
        "event_type": "STATE_CHANGE",
        "payload": {
          "previous_state": "QUEUED",
          "new_state": "CRAWLING",
          "current_step": "Crawling Target Endpoints"
        },
        "timestamp": "2026-08-04T01:10:00Z"
      }
    ]
  }
  ```

### 3.8 Distributed Scan Schedules & Autoscale Metrics (Phase 6.5)

#### `POST /scan-schedules`
- **Summary**: Create a new recurring scan schedule (`scans:schedule` permission required).
- **Request Body**:
  ```json
  {
    "scan_target_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Daily Staging Security Scan",
    "cron_expression": "0 2 * * *",
    "frequency": "DAILY",
    "profile_id": "full_assessment"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "id": "e7b92c41-8d2a-431e-b811-9f201b543201",
    "organization_id": "6bcb30b5-148f-4a15-baf2-3e5598512bd8",
    "scan_target_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Daily Staging Security Scan",
    "cron_expression": "0 2 * * *",
    "frequency": "DAILY",
    "status": "ACTIVE",
    "profile_id": "full_assessment",
    "enabled_plugins": null,
    "total_runs_count": 0,
    "next_run_at": "2026-08-05T02:00:00Z",
    "last_run_at": null,
    "created_by": "11111111-1111-1111-1111-111111111111",
    "created_at": "2026-08-04T02:00:00Z",
    "updated_at": "2026-08-04T02:00:00Z"
  }
  ```

#### `GET /scan-schedules`
- **Summary**: List recurring scan schedules with optional status filter (`scans:schedule` permission required).
- **Query Parameters**: `status` (`ACTIVE`, `PAUSED`, `DISABLED`), `limit`, `offset`.

#### `POST /scan-schedules/{schedule_id}/pause`
- **Summary**: Pause an active scan schedule (`scans:schedule` permission required).

#### `POST /scan-schedules/{schedule_id}/resume`
- **Summary**: Resume a paused scan schedule (`scans:schedule` permission required).

#### `POST /scan-schedules/tick`
- **Summary**: Manually trigger a Celery Beat scheduler tick executing all due active schedules (`scans:schedule` permission required).

#### `GET /scan-schedules/workers/autoscale-metrics`
- **Summary**: Retrieve worker capacity metrics and non-invasive autoscaling signals (`workers:read` permission required).
- **Response (200 OK)**:
  ```json
  {
    "active_workers_count": 4,
    "idle_workers_count": 2,
    "pending_queue_depth": 0,
    "recommended_workers_count": 4,
    "scaling_action_suggested": "STABLE",
    "timestamp": "2026-08-04T02:00:00Z"
  }
  ```

### 3.9 Security Operations Dashboard & Analyst Experience (Phase 7.1)

#### `GET /dashboard/overview`
- **Summary**: Retrieve consolidated SOC dashboard metrics including composite risk score, posture status, vulnerability distribution, active scan telemetry, top high-risk assets, and schedule summaries (`dashboard:read` permission required).
- **Response (200 OK)**:
  ```json
  {
    "organization_id": "6bcb30b5-148f-4a15-baf2-3e5598512bd8",
    "posture_summary": {
      "composite_risk_score": 78.5,
      "posture_status": "ELEVATED_RISK",
      "total_targets_count": 12,
      "total_open_findings": 47,
      "critical_findings_count": 3,
      "high_findings_count": 14
    },
    "vulnerability_breakdown": {
      "critical_count": 3,
      "high_count": 14,
      "medium_count": 20,
      "low_count": 8,
      "info_count": 2
    },
    "active_scans": [
      {
        "job_id": "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18",
        "target_name": "Production API Gateway",
        "target_url": "https://api.staging.example.com",
        "execution_state": "ASSESSING",
        "current_step": "Executing Active Security Plugins",
        "started_at": "2026-08-04T08:30:00Z"
      }
    ],
    "top_vulnerable_assets": [
      {
        "target_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "target_url": "https://auth.staging.example.com",
        "environment": "STAGING",
        "risk_score": 92.0,
        "critical_count": 2,
        "high_count": 5
      }
    ],
    "schedules_summary": {
      "total_active_schedules": 4,
      "next_scheduled_run_at": "2026-08-05T02:00:00Z"
    },
    "cached_at": "2026-08-04T09:15:00Z"
  }
  ```

#### `GET /dashboard/posture`
- **Summary**: Retrieve detailed organization posture risk score and status summary (`analytics:read` permission required).

#### `GET /dashboard/scans/active`
- **Summary**: Retrieve real-time active scan job details for live dashboard display (`scans:read` permission required).

### 3.10 Public Enterprise Trust Center & Security Disclosure Gateway (Phase 7.2)

#### `GET /public/trust`
- **Summary**: Retrieve public Enterprise Trust Center summary, OWASP ASVS control mappings, encryption specifications, and operational status (Unauthenticated public endpoint).
- **Response (200 OK)**:
  ```json
  {
    "platform_name": "Vulnova Enterprise AI Application Security Platform",
    "version": "1.0.0",
    "system_status": "OPERATIONAL",
    "asvs_alignment": "Security Controls Mapped Against OWASP ASVS v4.0",
    "encryption_standards": {
      "data_at_rest": "AES-256-GCM Envelope Encryption",
      "data_in_transit": "TLS 1.3 / HSTS Preloaded",
      "token_signing": "RS256 / EdDSA"
    },
    "sandbox_isolation": {
      "execution_user": "UID 10001 (Unprivileged)",
      "filesystem": "read_only_rootfs: true",
      "egress_filtering": "Strict Private Subnet Egress Proxy"
    },
    "security_practices_grid": [
      {
        "category": "V17_WORKER_SANDBOX",
        "title": "Container Sandbox Worker Isolation",
        "description": "Scanner workers execute in unprivileged containers with dropped Linux capabilities.",
        "status": "ENFORCED",
        "asvs_ref": "V14.2.1"
      }
    ],
    "cached_at": "2026-08-04T09:40:00Z"
  }
  ```

#### `GET /public/status`
- **Summary**: Retrieve high-level operational system status (Unauthenticated public endpoint).

#### `GET /public/security-disclosure`
- **Summary**: Retrieve vulnerability disclosure policy details, PGP key link, and security contact email (Unauthenticated public endpoint).

#### `GET /.well-known/security.txt`
- **Summary**: RFC 9116 standard plain text security disclosure directives for security researchers (Unauthenticated public endpoint).

### 3.11 Enterprise Executive Analytics & Report Export Gateway (Phase 7.3)

#### `GET /dashboard/trends`
- **Summary**: Retrieve historical risk score trajectory points, baseline score, and risk velocity (`analytics:read` permission required).
- **Query Parameters**: `timeframe_days` (default `30`, values: `7`, `30`, `90`).
- **Response (200 OK)**:
  ```json
  {
    "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "timeframe_days": 30,
    "current_risk_score": 65.0,
    "baseline_risk_score": 78.0,
    "risk_velocity": "IMPROVING",
    "mean_time_to_remediate_hours": 32.5,
    "trend_points": [
      {
        "date_str": "2026-07-05",
        "composite_risk_score": 78.0,
        "open_findings_count": 55,
        "critical_findings_count": 5
      }
    ],
    "cached_at": "2026-08-04T10:00:00Z"
  }
  ```

#### `GET /dashboard/coverage`
- **Summary**: Retrieve attack surface coverage percentage and environment asset breakdown (`dashboard:read` permission required).

#### `GET /dashboard/threat-advisories`
- **Summary**: Retrieve active executive security threat advisories, CVSS 9.0+ findings, and SLA breach warnings (`dashboard:read` permission required).

#### `GET /dashboard/executive-summary`
- **Summary**: Retrieve consolidated executive security posture report payload (`reports:read` permission required).

#### `GET /dashboard/export`
- **Summary**: Export executive security posture report in JSON or CSV format (`reports:export` permission required).
- **Query Parameters**: `format` (`json` or `csv`).

---

### Section F: Enterprise Administration REST Endpoints (Phase 7.6)

#### `GET /api/v1/admin/organization`
- **Summary**: Retrieve organization administration settings, plan metadata, and active member metrics.
- **RBAC Guard**: `organization:read` (`Role.VIEWER`+).

#### `PATCH /api/v1/admin/organization`
- **Summary**: Update organization display name or plan tier metadata with audit event recording (`organization.updated`).
- **RBAC Guard**: `organization:update` (`Role.ADMIN`+).

#### `GET /api/v1/admin/users`
- **Summary**: List organization team members, assigned RBAC roles, and account statuses.
- **RBAC Guard**: `users:read` (`Role.ADMIN`+).

#### `POST /api/v1/admin/users/invite`
- **Summary**: Invite a new team member with assigned RBAC role and dispatch audit event (`user.invited`).
- **RBAC Guard**: `users:invite` (`Role.ADMIN`+).

#### `PATCH /api/v1/admin/users/{user_id}/role`
- **Summary**: Update team member RBAC role. Enforces sole owner demotion protection (`count_owners_in_org <= 1`).
- **RBAC Guard**: `users:update_role` (`Role.OWNER` level 40).

#### `DELETE /api/v1/admin/users/{user_id}`
- **Summary**: Deactivate team member account. Enforces self-deactivation and sole owner protection.
- **RBAC Guard**: `users:remove` (`Role.ADMIN`+).

#### `GET /api/v1/admin/roles`
- **Summary**: Retrieve RBAC role-permission boundary matrix comparing OWNER, ADMIN, SECURITY_ANALYST, and VIEWER.
- **RBAC Guard**: `users:read` (`Role.ADMIN`+).

#### `GET /api/v1/admin/api-keys`
- **Summary**: List active integration API keys, prefixes, scopes, and last used timestamps.
- **RBAC Guard**: `api_keys:read` (`Role.ADMIN`+).

#### `POST /api/v1/admin/api-keys`
- **Summary**: Generate machine-to-machine API key. Raw secret returned ONCE in creation response DTO. Records audit event (`api_key.created`).
- **RBAC Guard**: `api_keys:create` (`Role.ADMIN`+).

#### `DELETE /api/v1/admin/api-keys/{key_id}`
- **Summary**: Revoke integration API key with audit event recording (`api_key.revoked`).
- **RBAC Guard**: `api_keys:revoke` (`Role.ADMIN`+).

#### `GET /api/v1/admin/security/status`
- **Summary**: Retrieve security configuration overview and MFA enrollment tracking visibility.
- **RBAC Guard**: `organization:read` (`Role.ADMIN`+).

---

### Section G: Executive Security Reports & Export REST Endpoints (Phase 8.1)

#### `POST /api/v1/reports/executive`
- **Summary**: Assembles complete CISO executive security posture report payload including risk scores, historical risk velocity, attack surface coverage, vulnerability severity breakdown, top findings, and threat advisories. Records audit event (`report.generated`).
- **RBAC Guard**: `reports:create` (`Role.ADMIN`+).
- **Request Body**:
  ```json
  {
    "title": "Q3 Enterprise Security Posture Report",
    "timeframe_days": 30,
    "include_sections": ["summary", "posture", "vulnerabilities", "attack_surface", "advisories"]
  }
  ```

#### `GET /api/v1/reports/{id}`
- **Summary**: Retrieve metadata description, posture score, total finding counts, and supported export formats for a generated report instance.
- **RBAC Guard**: `reports:read` (`Role.VIEWER`+).

#### `GET /api/v1/reports/{id}/html`
- **Summary**: Render styled HTML document string using Jinja2 templates and print-ready CSS for interactive browser preview.
- **RBAC Guard**: `reports:read` (`Role.VIEWER`+).

#### `GET /api/v1/reports/{id}/pdf`
- **Summary**: Generates and streams binary PDF document file (`application/pdf`) generated via WeasyPrint with graceful fallback. Records audit event (`report.downloaded`).
- **RBAC Guard**: `reports:export` (`Role.SECURITY_ANALYST`+).

#### `GET /api/v1/reports/export/json` (Phase 8.2)
- **Summary**: Stream bulk organizational security findings formatted as a machine-readable JSON array using memory-efficient batch chunking. Records audit event (`report.exported`).
- **RBAC Guard**: `reports:export` (`Role.SECURITY_ANALYST`+).
- **Response**: `application/json` streamed response (`Content-Disposition: attachment; filename="Vulnova_Export_Findings_...json"`).

#### `GET /api/v1/reports/export/csv` (Phase 8.2)
- **Summary**: Stream bulk organizational security findings formatted as a spreadsheet-ready CSV file using memory-efficient batch chunking. Records audit event (`report.exported`).
- **RBAC Guard**: `reports:export` (`Role.SECURITY_ANALYST`+).
- **Response**: `text/csv` streamed response (`Content-Disposition: attachment; filename="Vulnova_Export_Findings_...csv"`).

#### `GET /api/v1/reports/export/markdown` (Phase 8.2)
- **Summary**: Stream bulk organizational security findings formatted as a ticket-ready Markdown document using memory-efficient batch chunking. Records audit event (`report.exported`).
- **RBAC Guard**: `reports:export` (`Role.SECURITY_ANALYST`+).
- **Response**: `text/markdown` streamed response (`Content-Disposition: attachment; filename="Vulnova_Export_Findings_...md"`).

#### `GET /api/v1/reports/export/{finding_id}` (Phase 8.2)
- **Summary**: Export single vulnerability technical remediation package compiling intelligence, multi-modal evidence dumps, attack chain graphs, and AI fix recommendations into JSON, CSV, or Markdown. Automatically redacts sensitive tokens and Bearer credentials (`sanitize_sensitive_data`). Records audit event (`vulnerability.exported`).
- **RBAC Guard**: `reports:export` (`Role.SECURITY_ANALYST`+).
- **Query Parameters**: `format` (`json` | `csv` | `markdown`, default: `markdown`).
- **Response**: Downloadable file with matching media type and filename (`Vulnova_Finding_{finding_id[:8]}.{ext}`).

#### `GET /api/v1/compliance/{framework}/overview` (Phase 8.3)
- **Summary**: Returns compliance posture overview payload for the specified framework (`owasp_top10`, `asvs_v4`, `pci_dss`, `iso27001`). Evaluates score dynamically from active open findings, formats framework version metadata, and dispatches audit event (`compliance.viewed`).
- **RBAC Guard**: `compliance:read` (`Role.VIEWER`+).
- **Path Parameters**: `framework` (`owasp_top10` | `asvs_v4` | `pci_dss` | `iso27001`).
- **Response**: `200 OK` returning `ComplianceOverviewResponse` (framework metadata, score, controls list, top failed controls, top remediation priorities).

#### `GET /api/v1/compliance/{framework}/controls` (Phase 8.3)
- **Summary**: Returns all framework controls mapped to active vulnerability findings and evidence artifact checksums with full traceability (`Framework Control -> Vulnerability Finding -> Evidence Artifact -> Target Asset -> Remediation Guidance`).
- **RBAC Guard**: `compliance:read` (`Role.VIEWER`+).
- **Path Parameters**: `framework` (`owasp_top10` | `asvs_v4` | `pci_dss` | `iso27001`).
- **Response**: `200 OK` returning `List[ComplianceControlDTO]`.

#### `GET /api/v1/compliance/{framework}/export` (Phase 8.3)
- **Summary**: Generates and downloads dynamic JSON compliance report payload. Dispatches audit event (`compliance.exported`).
- **RBAC Guard**: `compliance:export` (`Role.SECURITY_ANALYST`+).
- **Path Parameters**: `framework` (`owasp_top10` | `asvs_v4` | `pci_dss` | `iso27001`).
- **Response**: `200 OK` `application/json` (`Content-Disposition: attachment; filename="Vulnova_Compliance_{framework}_...json"`).

---

### Section I: Enterprise Integrations Router Endpoints (`/api/v1/integrations`) (Phase 9.1 ✅)

#### `GET /api/v1/integrations` (Phase 9.1)
- **Summary**: Retrieve configuration status for Jira Cloud and GitHub Issues integrations (secrets masked).
- **RBAC Guard**: `integrations:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `IntegrationConfigResponse` (`jira`: `JiraConfigDTO`, `github`: `GitHubConfigDTO`).

#### `POST /api/v1/integrations/jira/config` (Phase 9.1)
- **Summary**: Encrypt Jira API token using AES-256-GCM / Fernet and save configuration for tenant. Dispatches audit event (`integration.configuration_updated`).
- **RBAC Guard**: `integrations:manage` (`Role.ADMIN`+).
- **Request Body**: `SaveJiraConfigRequest` (`host_url`, `email`, `api_token`, `project_key`, `issue_type`).
- **Response**: `200 OK` returning `JiraConfigDTO` (api token masked).

#### `POST /api/v1/integrations/github/config` (Phase 9.1)
- **Summary**: Encrypt GitHub Personal Access Token using AES-256-GCM / Fernet and save configuration for tenant. Dispatches audit event (`integration.configuration_updated`).
- **RBAC Guard**: `integrations:manage` (`Role.ADMIN`+).
- **Request Body**: `SaveGitHubConfigRequest` (`repo_owner`, `repo_name`, `personal_access_token`).
- **Response**: `200 OK` returning `GitHubConfigDTO` (token masked).

#### `POST /api/v1/integrations/jira/issues/{finding_id}` (Phase 9.1)
- **Summary**: Format finding into Atlassian Document Format (ADF) and create ticket in connected Jira project. Dispatches audit event (`integration.issue_created`).
- **RBAC Guard**: `integrations:create` (`Role.SECURITY_ANALYST`+).
- **Path Parameters**: `finding_id` (UUID).
- **Request Body**: `CreateIssueRequest` (`custom_labels`, `assignee`).
- **Response**: `201 Created` returning `ExternalIssueDTO` (`issue_id`, `issue_key`, `issue_url`, `provider`, `status`, `created_at`).

#### `POST /api/v1/integrations/github/issues/{finding_id}` (Phase 9.1)
- **Summary**: Format finding into GitHub-Flavored Markdown and create issue in target GitHub repository. Dispatches audit event (`integration.issue_created`).
- **RBAC Guard**: `integrations:create` (`Role.SECURITY_ANALYST`+).
- **Path Parameters**: `finding_id` (UUID).
- **Request Body**: `CreateIssueRequest` (`custom_labels`, `assignee`).
- **Response**: `201 Created` returning `ExternalIssueDTO` (`issue_id`, `issue_key`, `issue_url`, `provider`, `status`, `created_at`).

#### `POST /api/v1/integrations/jira/{finding_id}/{issue_key}/sync` (Phase 9.1)
- **Summary**: Fetch Jira status and map state changes safely through `ControlledJiraStatusMapper` into Vulnova finding state. Dispatches audit event (`integration.issue_synced`).
- **RBAC Guard**: `integrations:update` (`Role.SECURITY_ANALYST`+).
- **Path Parameters**: `finding_id` (UUID), `issue_key` (string).
- **Response**: `200 OK` returning `SyncStatusResponse`.

#### `POST /api/v1/integrations/github/{finding_id}/{issue_number}/sync` (Phase 9.1)
- **Summary**: Fetch GitHub issue state and map state changes safely through `ControlledGitHubStatusMapper` into Vulnova finding state. Dispatches audit event (`integration.issue_synced`).
- **RBAC Guard**: `integrations:update` (`Role.SECURITY_ANALYST`+).
- **Path Parameters**: `finding_id` (UUID), `issue_number` (string).
- **Response**: `200 OK` returning `SyncStatusResponse`.

---

### Section J: Real-Time Notifications & Security Alert Webhooks Endpoints (Phase 9.2 ✅)

#### `GET /api/v1/notifications/channels` (Phase 9.2)
- **Summary**: Return configured Slack and Microsoft Teams notification channels for tenant (urls masked).
- **RBAC Guard**: `notifications:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning List of `NotificationChannelDTO`.

#### `POST /api/v1/notifications/channels` (Phase 9.2)
- **Summary**: Create and encrypt a new notification webhook channel. Dispatches audit event (`notification.channel_created`).
- **RBAC Guard**: `notifications:manage` (`Role.ADMIN`+).
- **Request Body**: `CreateChannelRequest` (`provider`, `name`, `webhook_url`, `event_types`, `min_severity`).
- **Response**: `201 Created` returning `NotificationChannelDTO`.

#### `PATCH /api/v1/notifications/channels/{channel_id}` (Phase 9.2)
- **Summary**: Update notification channel settings or encrypted webhook URL. Dispatches audit event (`notification.channel_updated`).
- **RBAC Guard**: `notifications:manage` (`Role.ADMIN`+).
- **Path Parameters**: `channel_id` (string).
- **Request Body**: `UpdateChannelRequest`.
- **Response**: `200 OK` returning `NotificationChannelDTO`.

#### `DELETE /api/v1/notifications/channels/{channel_id}` (Phase 9.2)
- **Summary**: Delete a notification webhook channel. Dispatches audit event (`notification.channel_deleted`).
- **RBAC Guard**: `notifications:manage` (`Role.ADMIN`+).
- **Path Parameters**: `channel_id` (string).
- **Response**: `204 No Content`.

#### `GET /api/v1/notifications/rules` (Phase 9.2)
- **Summary**: Fetch event routing rules and severity filters.
- **RBAC Guard**: `notifications:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning List of `NotificationRuleDTO`.

#### `POST /api/v1/notifications/test` (Phase 9.2)
- **Summary**: Dispatch an instant test security alert to verify Slack/Teams webhook connectivity. Dispatches audit event (`notification.sent` | `notification.failed`).
- **RBAC Guard**: `notifications:create` (`Role.SECURITY_ANALYST`+).
- **Request Body**: `TestNotificationRequest` (`channel_id`).
- **Response**: `200 OK` returning `NotificationDeliveryResponse`.

---

### Section K: CI/CD Pipeline Scanning CLI Endpoints (Phase 9.3)

#### `POST /api/v1/cli/tokens` (Phase 9.3)
- **Summary**: Generate a new secure CLI API token (`vn_cli_...`). Dispatches audit event (`cli.token_created`).
- **RBAC Guard**: `cli:manage` (`Role.ADMIN`+).
- **Request Body**: `CLITokenCreateRequest` (`name`, `expires_in_days`).
- **Response**: `201 Created` returning `CLITokenDTO` (raw_token present only on creation).

#### `GET /api/v1/cli/tokens` (Phase 9.3)
- **Summary**: List active CLI tokens for tenant organization.
- **RBAC Guard**: `cli:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning List of `CLITokenDTO` (raw_token masked).

#### `DELETE /api/v1/cli/tokens/{token_id}` (Phase 9.3)
- **Summary**: Revoke a CLI API token. Dispatches audit event (`cli.token_revoked`).
- **RBAC Guard**: `cli:manage` (`Role.ADMIN`+).
- **Response**: `204 No Content`.

#### `POST /api/v1/cli/scans/start` (Phase 9.3)
- **Summary**: Trigger a security scan job from CI/CD pipeline. Dispatches audit event (`cli.scan_started`).
- **RBAC Guard**: `cli:trigger` (`Role.SECURITY_ANALYST`+).
- **Request Body**: `CLIScanStartRequest` (`target_url`, `profile_id`, `project_name`, `branch`, `commit_sha`).
- **Response**: `201 Created` returning `CLIScanStatusResponse`.

#### `GET /api/v1/cli/scans/{scan_id}/status` (Phase 9.3)
- **Summary**: Fetch status and progress percentage for CLI polling.
- **RBAC Guard**: `cli:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `CLIScanStatusResponse`.

#### `GET /api/v1/cli/findings/summary` (Phase 9.3)
- **Summary**: Fetch severity breakdown metrics for scan.
- **RBAC Guard**: `cli:read` (`Role.VIEWER`+).
- **Query Parameters**: `scan_id` (string).
- **Response**: `200 OK` returning `CLIFindingSummaryDTO`.

#### `POST /api/v1/cli/gate/evaluate` (Phase 9.3)
- **Summary**: Evaluate CI/CD build security gate against configured thresholds. Dispatches audit event (`cli.scan_completed` | `cli.pipeline_failed`).
- **RBAC Guard**: `cli:read` (`Role.VIEWER`+).
- **Request Body**: `CLIPipelineGateRequest` (`scan_id`, `max_critical`, `max_high`, `max_medium`).
- **Response**: `200 OK` returning `CLIPipelineGateResult` (`gate_passed`, `exit_code`, `summary_text`, `failed_conditions`).

#### `GET /api/v1/cli/projects` (Phase 9.3)
- **Summary**: List registered projects and repositories for tenant.
- **RBAC Guard**: `cli:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning List of `CLIProjectDTO`.

---

### Section L: OWASP Top 10 (2021) Security Validation Endpoints (Phase 10.1)

#### `POST /api/v1/validation/owasp-top-10/run` (Phase 10.1)
- **Summary**: Trigger an automated in-memory OWASP Top 10 (2021) security assertion suite scan. Dispatches audit events (`validation.owasp_suite_started`, `validation.owasp_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `OWASPValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/owasp-top-10/results` (Phase 10.1)
- **Summary**: Fetch full category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `OWASPValidationSuiteResponse`.

#### `GET /api/v1/validation/owasp-top-10/summary` (Phase 10.1)
- **Summary**: Fetch high-level OWASP verification health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `OWASPVerificationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section M: OWASP API Security Top 10 (2023) Validation Endpoints (Phase 10.2)

#### `POST /api/v1/validation/api-security/run` (Phase 10.2)
- **Summary**: Trigger an automated in-memory OWASP API Security Top 10 (2023) assertion suite scan. Dispatches audit events (`validation.api_security_suite_started`, `validation.api_security_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `APIValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/api-security/results` (Phase 10.2)
- **Summary**: Fetch full API category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `APIValidationSuiteResponse`.

#### `GET /api/v1/validation/api-security/summary` (Phase 10.2)
- **Summary**: Fetch high-level API security verification health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `APIValidationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section N: Security Configuration & Infrastructure Validation Endpoints (Phase 10.3)

#### `POST /api/v1/validation/infrastructure/run` (Phase 10.3)
- **Summary**: Trigger an automated in-memory Infrastructure Security assertion suite scan. Dispatches audit events (`validation.infrastructure_suite_started`, `validation.infrastructure_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `InfrastructureValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/infrastructure/results` (Phase 10.3)
- **Summary**: Fetch full infrastructure category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `InfrastructureValidationSuiteResponse`.

#### `GET /api/v1/validation/infrastructure/summary` (Phase 10.3)
- **Summary**: Fetch high-level infrastructure security verification health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `InfrastructureValidationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section O: Platform Penetration Testing & Exploit Verification Endpoints (Phase 10.4)

#### `POST /api/v1/validation/pentest/run` (Phase 10.4)
- **Summary**: Trigger an automated in-memory Platform Penetration Testing & Exploit assertion suite scan. Dispatches audit events (`validation.pentest_suite_started`, `validation.pentest_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `PenTestValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/pentest/results` (Phase 10.4)
- **Summary**: Fetch full penetration testing category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `PenTestValidationSuiteResponse`.

#### `GET /api/v1/validation/pentest/summary` (Phase 10.4)
- **Summary**: Fetch high-level penetration testing health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `PenTestValidationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section P: Dependency Security Audit & SCA Enforcement Endpoints (Phase 10.5)

#### `POST /api/v1/validation/sca/run` (Phase 10.5)
- **Summary**: Trigger an automated in-memory Software Composition Analysis assertion suite scan. Dispatches audit events (`validation.sca_suite_started`, `validation.sca_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `SCAValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/sca/results` (Phase 10.5)
- **Summary**: Fetch full dependency security category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `SCAValidationSuiteResponse`.

#### `GET /api/v1/validation/sca/summary` (Phase 10.5)
- **Summary**: Fetch high-level dependency security verification health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `SCAValidationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section Q: Container Image Security Audit & Runtime Hardening Endpoints (Phase 10.6)

#### `POST /api/v1/validation/container/run` (Phase 10.6)
- **Summary**: Trigger an automated in-memory Container Image Security & Hardening assertion suite scan. Dispatches audit events (`validation.container_suite_started`, `validation.container_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `ContainerValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/container/results` (Phase 10.6)
- **Summary**: Fetch full container security category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `ContainerValidationSuiteResponse`.

#### `GET /api/v1/validation/container/summary` (Phase 10.6)
- **Summary**: Fetch high-level container security verification health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `ContainerValidationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section R: Secrets & Cryptographic Management Endpoints (Phase 10.7)

#### `POST /api/v1/validation/secrets/run` (Phase 10.7)
- **Summary**: Trigger an automated in-memory Secrets & Cryptographic Management assertion suite scan. Dispatches audit events (`validation.secrets_suite_started`, `validation.secrets_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `SecretsValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/secrets/results` (Phase 10.7)
- **Summary**: Fetch full secrets security category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `SecretsValidationSuiteResponse`.

#### `GET /api/v1/validation/secrets/summary` (Phase 10.7)
- **Summary**: Fetch high-level secrets security verification health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `SecretsValidationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section S: Threat Model Review & STRIDE Verification Endpoints (Phase 10.8)

#### `POST /api/v1/validation/threat/run` (Phase 10.8)
- **Summary**: Trigger an automated in-memory Threat Model Review & STRIDE Verification assertion suite scan. Dispatches audit events (`validation.threat_suite_started`, `validation.threat_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `ThreatValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/threat/results` (Phase 10.8)
- **Summary**: Fetch full STRIDE threat model security category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `ThreatValidationSuiteResponse`.

#### `GET /api/v1/validation/threat/summary` (Phase 10.8)
- **Summary**: Fetch high-level threat model security verification health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `ThreatValidationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section T: Automated Security Regression Endpoints (Phase 10.9)

#### `POST /api/v1/validation/regression/run` (Phase 10.9)
- **Summary**: Trigger an automated in-memory Automated Security Regression Testing assertion suite scan. Dispatches audit events (`validation.regression_suite_started`, `validation.regression_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `RegressionValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_pass_rate`, `category_results`).

#### `GET /api/v1/validation/regression/results` (Phase 10.9)
- **Summary**: Fetch full security regression category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `RegressionValidationSuiteResponse`.

#### `GET /api/v1/validation/regression/summary` (Phase 10.9)
- **Summary**: Fetch high-level security regression health summary metrics.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `RegressionValidationSummaryDTO` (`overall_pass_rate`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section U: Security Certification Validation Endpoints (Phase 10.10)

#### `POST /api/v1/validation/certification/run` (Phase 10.10)
- **Summary**: Trigger an automated in-memory Security Control Plane Final Certification assertion suite scan. Dispatches audit events (`validation.certification_suite_started`, `validation.certification_suite_completed`).
- **RBAC Guard**: `validation:execute` (`Role.SECURITY_ANALYST`+).
- **Response**: `200 OK` returning `CertificationValidationSuiteResponse` (`suite_id`, `overall_status`, `overall_certification_score`, `category_results`).

#### `GET /api/v1/validation/certification/results` (Phase 10.10)
- **Summary**: Fetch full security certification category assertion evaluation metrics and results for tenant organization.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `CertificationValidationSuiteResponse`.

#### `GET /api/v1/validation/certification/summary` (Phase 10.10)
- **Summary**: Fetch high-level enterprise security certification summary metrics and compliance score.
- **RBAC Guard**: `validation:read` (`Role.VIEWER`+).
- **Response**: `200 OK` returning `CertificationValidationSummaryDTO` (`overall_certification_score`, `overall_status`, `passed_categories`, `failed_categories`).

---

### Section V: Multi-Factor Authentication (MFA / TOTP) Endpoints (Phase 10.11)

#### `POST /api/v1/auth/mfa/setup` (Phase 10.11)
- **Summary**: Initialize MFA setup for authenticated user.
- **Auth**: Bearer JWT.
- **Response**: `200 OK` returning `MFASetupResponse` (`secret`, `provisioning_uri`, `qr_code_base64`, `recovery_codes`).

#### `POST /api/v1/auth/mfa/verify-setup` (Phase 10.11)
- **Summary**: Verify first 6-digit OTP code to confirm authenticator app binding and enable MFA.
- **Auth**: Bearer JWT.
- **Payload**: `MFAVerifySetupRequest` (`code`).
- **Response**: `200 OK` returning `{"status": "enabled", "message": "..."}`.

#### `POST /api/v1/auth/mfa/disable` (Phase 10.11)
- **Summary**: Disable MFA on account. Requires current password and valid OTP.
- **Auth**: Bearer JWT.
- **Payload**: `MFADisableRequest` (`current_password`, `code`).
- **Response**: `200 OK` returning `{"status": "disabled", "message": "..."}`.

#### `POST /api/v1/auth/mfa/challenge` (Phase 10.11)
- **Summary**: Verify OTP or single-use recovery code during login challenge, issuing session access and refresh tokens.
- **Payload**: `MFAChallengeRequest` (`mfa_login_token`, `code`).
- **Response**: `200 OK` returning `TokenResponse` (`access_token`, `user`, `mfa_required=False`).

#### `POST /api/v1/auth/mfa/recovery-codes/regenerate` (Phase 10.11)
- **Summary**: Regenerate 10 new single-use emergency backup recovery codes.
- **Auth**: Bearer JWT.
- **Payload**: `MFARecoveryRegenerateRequest` (`current_password`, `code`).
- **Response**: `200 OK` returning `MFARecoveryRegenerateResponse` (`recovery_codes`).

#### `GET /api/v1/auth/mfa/status` (Phase 10.11)
- **Summary**: Get current MFA configuration status, last verified timestamp, and backup codes count.
- **Auth**: Bearer JWT.
- **Response**: `200 OK` returning `MFAStatusResponse`.

---

### Section W: Database Performance Endpoints (Phase 11.1)

#### `GET /api/v1/database/performance/health` (Phase 11.1)
- **Summary**: Fetch database performance health summary, average latency, pool status, and recommendations.
- **RBAC Guard**: `admin:read` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `DatabaseHealthSummaryDTO`.

#### `POST /api/v1/database/performance/benchmark` (Phase 11.1)
- **Summary**: Run controlled query benchmark profiling suite against core platform models.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Params**: `iterations` (default 10).
- **Response**: `200 OK` returning `List[BenchmarkResultDTO]`.

#### `GET /api/v1/database/performance/slow-queries` (Phase 11.1)
- **Summary**: Retrieve captured slow query logs exceeding 100ms threshold.
- **RBAC Guard**: `admin:read` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `List[SlowQueryLogDTO]`.

---

### Section X: Rate Limiting & Response Headers Specification (Phase 11.2)

#### Global HTTP Rate Limit Response (`429 Too Many Requests`) (Phase 11.2)
- **Trigger**: Issued when client IP, user account, or tenant organization exceeds token bucket capacity.
- **Status Code**: `429 Too Many Requests`.
- **Response Headers**:
  - `X-RateLimit-Limit`: Maximum allowed requests in window (e.g. `100`, `1000`, `5000`).
  - `X-RateLimit-Remaining`: Remaining request count (`0`).
  - `X-RateLimit-Reset`: Time in seconds until bucket resets.
  - `Retry-After`: Recommended backoff delay in seconds.
- **Response Payload**:
  ```json
  {
    "error": {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Too many requests. Please slow down and try again later.",
      "request_id": "req-uuid-v4"
    }
  }
  ```

---

### Section Y: Centralized Observability & System Probes Endpoints (Phase 11.3)

#### `GET /metrics` (Phase 11.3)
- **Summary**: Expose application, database, cache, and security audit metrics formatted in standard Prometheus exposition text format.
- **Content-Type**: `text/plain; version=0.0.4`.
- **Response**: `200 OK` returning Prometheus metric text block.

#### `GET /api/v1/system/health` (Phase 11.3)
- **Summary**: Retrieve comprehensive operational health status summary across database, Redis, and background services.
- **Response**: `200 OK` returning `status`, `version`, `timestamp`, `uptime_seconds`, and `dependencies`.

#### `GET /api/v1/system/readiness` (Phase 11.3)
- **Summary**: Kubernetes readiness probe evaluating database connectivity.
- **Response**: `200 OK` when ready; `503 Service Unavailable` when database is unready.

#### `GET /api/v1/system/liveness` (Phase 11.3)
- **Summary**: Kubernetes liveness probe checking process vitality.
- **Response**: `200 OK` returning `{"status": "ALIVE", "ping": "pong"}`.
















---

### Section H: Production Operational & Health Telemetry Endpoints (Planned Era 11 📋)

#### `GET /health`
- **Summary**: Platform root health check returning high-level status indicator (`HEALTHY`, `DEGRADED`, `UNHEALTHY`). Publicly accessible.
- **Planned Era**: Era 11 (Phase 11.3).

#### `GET /health/liveness`
- **Summary**: Kubernetes / container orchestra liveness probe checking FastAPI process responsiveness. Publicly accessible.
- **Planned Era**: Era 11 (Phase 11.3).

#### `GET /health/readiness`
- **Summary**: Readiness probe checking active connections to PostgreSQL 16, Redis 7, and Celery message broker before routing ingress traffic. Publicly accessible.
- **Planned Era**: Era 11 (Phase 11.3).

#### `GET /metrics`
- **Summary**: Prometheus format time-series metrics endpoint exposing API request counters, HTTP latency histograms, Celery worker queue depth, and DB connection pool utilization. Protected by operational exporter token.
- **Planned Era**: Era 11 (Phase 11.3).




---

### Section Z: Database Backup & Point-in-Time Recovery (PITR) Endpoints (Phase 11.4 ✅)

#### `GET /api/v1/database/backups` (Phase 11.4)
- **Summary**: Retrieve list of retained PostgreSQL base backups, AES-256 encryption status, total storage consumption, and retention policy parameters.
- **RBAC Guard**: `admin:read` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `BackupMetadataDTO` (`backups`, `retention_days`, `total_backups_count`, `total_size_bytes`, `last_backup_at`).

#### `POST /api/v1/database/backups/create` (Phase 11.4)
- **Summary**: Execute an immediate base database export with AES-256 Fernet payload encryption and SHA-256 checksum generation, enforcing 30-day retention purging.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Response**: `201 Created` returning `BackupStatusDTO` (`backup_id`, `timestamp`, `size_bytes`, `checksum`, `status`, `storage_location`, `is_encrypted`).

#### `POST /api/v1/database/backups/verify` (Phase 11.4)
- **Summary**: Execute automated dry-run restore verification by decrypting a target backup archive and verifying DDL schema and table row count integrity.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Query Params**: `backup_id` (optional string, targets latest backup if omitted).
- **Response**: `200 OK` returning `BackupVerificationDTO` (`backup_id`, `verified_at`, `integrity_passed`, `schema_valid`, `row_counts`, `details`).

#### `GET /api/v1/database/backups/status` (Phase 11.4)
- **Summary**: Retrieve high-level operational health status of database backup automation, encryption status, and retention configuration.
- **RBAC Guard**: `admin:read` (`Role.ADMIN`+).
- **Response**: `200 OK` returning JSON status object (`status`, `total_backups`, `total_size_bytes`, `retention_days`, `last_backup_at`, `wal_archiving`, `encryption`).

---

### Section AA: Enterprise Disaster Recovery, Failover & Rollback Endpoints (Phase 11.5 ✅)

#### `GET /api/v1/disaster-recovery/status` (Phase 11.5)
- **Summary**: Retrieve current disaster recovery readiness, RTO/RPO targets, and component health state (primary database, secondary replica, Redis cluster).
- **RBAC Guard**: `admin:read` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `DisasterRecoveryStatusDTO` (`status`, `rto_target_minutes`, `rpo_target_minutes`, `primary_database_status`, `secondary_database_status`, `redis_cluster_status`, `last_backup_timestamp`, `last_dr_test_timestamp`, `active_recovery_id`).

#### `POST /api/v1/disaster-recovery/recover` (Phase 11.5)
- **Summary**: Execute a disaster recovery workflow (SIMULATION, PITR_RESTORE, FAILOVER, or ROLLBACK) with full 5-phase lifecycle tracking and RTO/RPO achievement validation.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Query Params**: `recovery_type` (string, default: `SIMULATION`).
- **Response**: `200 OK` returning `RecoveryExecutionDTO` (`recovery_id`, `executed_at`, `recovery_type`, `stages_completed`, `duration_seconds`, `rto_achieved_minutes`, `rpo_estimated_minutes`, `rto_target_met`, `rpo_target_met`, `success`, `details`).

#### `GET /api/v1/disaster-recovery/recovery-history` (Phase 11.5)
- **Summary**: Retrieve all past disaster recovery execution records and RTO/RPO outcomes.
- **RBAC Guard**: `admin:read` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `List[RecoveryExecutionDTO]`.

#### `POST /api/v1/disaster-recovery/failover` (Phase 11.5)
- **Summary**: Execute controlled primary-to-secondary database failover with DNS endpoint swap and post-promotion health validation.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `FailoverEventDTO` (`event_id`, `timestamp`, `triggered_by`, `primary_endpoint`, `secondary_endpoint`, `status`, `details`).

#### `GET /api/v1/disaster-recovery/failover-history` (Phase 11.5)
- **Summary**: Retrieve all past failover event records.
- **RBAC Guard**: `admin:read` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `List[FailoverEventDTO]`.

#### `POST /api/v1/disaster-recovery/rollback` (Phase 11.5)
- **Summary**: Execute application deployment rollback to a prior stable version with container image swap and health check validation.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Query Params**: `target_version` (string, default: `11.4.0`).
- **Response**: `200 OK` returning `RollbackStatusDTO` (`rollback_id`, `timestamp`, `current_version`, `target_version`, `health_check_passed`, `status`, `details`).

#### `GET /api/v1/disaster-recovery/rollback-history` (Phase 11.5)
- **Summary**: Retrieve all past deployment rollback execution records.
- **RBAC Guard**: `admin:read` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `List[RollbackStatusDTO]`.

---

### Section AB: Security Incident Response & Audit Escalation Endpoints (Phase 11.6 ✅)

#### `GET /api/v1/incidents` (Phase 11.6)
- **Summary**: Retrieve paginated list of security incidents for the authenticated organization.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Query Params**: `severity` (string, optional: `SEV-1`, `SEV-2`, `SEV-3`, `SEV-4`), `status` (string, optional: `DETECTED`, `TRIAGED`, `CONTAINED`, `INVESTIGATING`, `ERADICATED`, `RECOVERED`, `CLOSED`), `limit` (int, default: 50), `offset` (int, default: 0).
- **Response**: `200 OK` returning `IncidentListResponseDTO` (`incidents`, `total`, `limit`, `offset`).

#### `POST /api/v1/incidents` (Phase 11.6)
- **Summary**: Declare and classify a new security incident, trigger initial timeline recording, and log audit event.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Request Body**: `CreateIncidentRequestDTO` (`title`, `description`, `severity`, `lead_investigator_id`, `affected_services`, `indicators_of_compromise`, `details`).
- **Response**: `201 Created` returning `IncidentResponseDTO`.

#### `GET /api/v1/incidents/status/summary` (Phase 11.6)
- **Summary**: Retrieve high-level operational posture, severity counts, MTTC, and MTTR response times.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `IncidentStatusDTO` (`total_active_incidents`, `sev1_critical_count`, `sev2_high_count`, `sev3_medium_count`, `sev4_low_count`, `contained_count`, `mean_time_to_contain_minutes`, `mean_time_to_resolve_minutes`, `status`).

#### `GET /api/v1/incidents/{id}` (Phase 11.6)
- **Summary**: Fetch comprehensive incident details, chronological timelines, escalations, PIR, and duration metrics.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `IncidentResponseDTO`.

#### `PATCH /api/v1/incidents/{id}` (Phase 11.6)
- **Summary**: Transition incident lifecycle state and record state changes in timeline and audit logs.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Request Body**: `UpdateIncidentStateRequestDTO` (`status`, `note`, `lead_investigator_id`, `affected_services`, `indicators_of_compromise`, `details`).
- **Response**: `200 OK` returning `IncidentResponseDTO`.

#### `POST /api/v1/incidents/{id}/escalate` (Phase 11.6)
- **Summary**: Trigger multi-channel alert escalation workflow across PagerDuty, Slack, and Email.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Request Body**: `TriggerEscalationRequestDTO` (`channels`, `reason`, `details`).
- **Response**: `200 OK` returning `EscalationEventDTO` (`id`, `incident_id`, `severity`, `channels`, `status`, `notification_status`, `triggered_by`, `triggered_at`, `details`).

#### `GET /api/v1/incidents/{id}/timeline` (Phase 11.6)
- **Summary**: Retrieve chronological timeline milestones and linked audit logs for an incident.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `List[IncidentTimelineDTO]`.

#### `POST /api/v1/incidents/{id}/pir` (Phase 11.6)
- **Summary**: Create or update Post-Incident Review (PIR) with root cause, impact, timeline, lessons learned, and action items.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Request Body**: `CreatePIRRequestDTO` (`summary`, `root_cause`, `impact_assessment`, `timeline_summary`, `lessons_learned`, `action_items`).
- **Response**: `201 Created` returning `PostIncidentReviewDTO`.

#### `GET /api/v1/incidents/{id}/pir` (Phase 11.6)
- **Summary**: Fetch Post-Incident Review analysis for a security incident.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `PostIncidentReviewDTO`.

#### `GET /api/v1/incidents/{id}/forensics` (Phase 11.6)
- **Summary**: Retrieve correlated audit event clusters and SHA-256 evidence integrity package for forensic analysis.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `ForensicInvestigationResultDTO` (`incident_id`, `organization_id`, `investigation_timestamp`, `total_events_analyzed`, `correlated_clusters`, `suspicious_ips`, `affected_actors`, `forensic_integrity_sha256`, `summary`).

---

### Section AC: Final Security Audit & Penetration Testing Endpoints (Phase 12.1 ✅)

#### `GET /api/v1/security-audit/status` (Phase 12.1)
- **Summary**: Retrieve high-level security audit posture, total vulnerabilities tracked, remediation rate percentage, and compliance grade.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Response**: `200 OK` returning `SecurityAuditStatusDTO` (`status`, `last_audit_id`, `last_audit_timestamp`, `total_scans_executed`, `total_vulnerabilities_tracked`, `critical_findings`, `high_findings`, `medium_findings`, `low_findings`, `remediation_rate_percentage`, `compliance_grade`).

#### `GET /api/v1/security-audit/findings` (Phase 12.1)
- **Summary**: Retrieve paginated list of security audit findings with optional category, severity, and status filtering.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Query Params**: `category` (string, optional), `severity` (string, optional: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), `status` (string, optional: `OPEN`, `REMEDIATED`, `ACCEPTED_RISK`, `FALSE_POSITIVE`), `limit` (int, default: 50), `offset` (int, default: 0).
- **Response**: `200 OK` returning `List[SecurityAuditFindingDTO]`.

#### `POST /api/v1/security-audit/run` (Phase 12.1)
- **Summary**: Trigger automated multi-domain security audit and penetration verification across SAST, SCA, Config, API, Auth, RBAC, Secret, and Container domains.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Request Body**: `RunSecurityAuditRequestDTO` (`categories`, `include_dynamic_checks`, `details`).
- **Response**: `201 Created` returning `SecurityAuditExecutionDTO` (`audit_id`, `organization_id`, `executed_at`, `total_findings`, `critical_count`, `high_count`, `medium_count`, `low_count`, `open_findings_count`, `remediated_findings_count`, `overall_security_score`, `status`, `categories_analyzed`, `findings`, `audit_integrity_sha256`, `summary`).

#### `PATCH /api/v1/security-audit/findings/{finding_id}/remediate` (Phase 12.1)
- **Summary**: Update finding remediation status (`REMEDIATED`, `ACCEPTED_RISK`, `FALSE_POSITIVE`) and record audit event.
- **RBAC Guard**: `admin:manage` (`Role.ADMIN`+).
- **Request Body**: `RemediateFindingRequestDTO` (`status`, `remediation_notes`, `remediated_by`).
- **Response**: `200 OK` returning `SecurityAuditFindingDTO`.

---

### Section AD: Production Deployment API Considerations (Phase 12.2 ✅)

- **System Health & Readiness Endpoints**:
  - `GET /health`: Basic container process liveness probe (`200 OK`).
  - `GET /api/v1/system/readiness`: Deep database, Redis, MinIO, and Qdrant readiness check. Returns `200 OK` when all dependent services are healthy.
  - `GET /api/v1/system/liveness`: Container liveness check for Kubernetes Kubelet probes (`200 OK`).
- **Ingress TLS & Custom Domains**:
  - All production API endpoints must be accessed via HTTPS with TLS 1.2+ (`https://api.vulnova.enterprise.com/api/v1/...`).
  - NGINX Ingress controller automatically strips TLS at boundary and injects `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Request-ID` headers.
- **Rate Limiting & DDOS Governance**:
  - Production APIs enforce Redis-backed token bucket rate limits (100 req/min for authenticated endpoints, 10 req/min for auth endpoints).


---

## ⚡ 4. WebSocket Streaming Protocol

### Connection: `GET /api/v1/ws/scans/{scan_id}`
Clients connect to receive live streaming updates during scan execution.


