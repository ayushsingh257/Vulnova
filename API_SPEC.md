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

#### `POST /findings/{finding_id}/ai-analyze`
- **Summary**: Trigger autonomous AI Security Analyst re-evaluation.
- **Response (200 OK)**:
  ```json
  {
    "finding_id": "uuid...",
    "ai_analysis": {
      "cvss_score": 8.6,
      "cvss_vector": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N",
      "technical_impact": "Reflected Cross-Site Scripting allows arbitrary code execution in victim browser context.",
      "business_impact": "Potential session hijacking of administrative users leading to unauthorized account takeover.",
      "attack_scenario": "Attacker crafts malicious URL containing payload...",
      "remediation_patch": "```python\n# Sanitized input using HTML escape\nimport html\nsanitized_input = html.escape(user_input)\n```",
      "false_positive_probability": 0.05
    }
  }
  ```

---

## ⚡ 4. WebSocket Streaming Protocol

### Connection: `GET /api/v1/ws/scans/{scan_id}`
Clients connect to receive live streaming updates during scan execution.
