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

### C. Scan Execution & Target Authorization (`/scans`)

#### `POST /scans`
- **Summary**: Dispatch new security scan job with mandatory legal target authorization confirmation.
- **Request Body**:
  ```json
  {
    "target_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "profile_id": "8f12a34b-9876-4321-a1b2-c3d4e5f67890",
    "enable_ai_analysis": true,
    "authorization_declaration": {
      "confirmed_ownership_or_permission": true,
      "declaration_text": "I confirm that I own this asset or have explicit permission to perform security testing.",
      "accepted_scope_boundary": "https://api.shop.enterprise.com/*"
    }
  }
  ```
- **Response (202 Accepted)**:
  ```json
  {
    "scan_job_id": "c73bcd8f-0e42-4f32-8419-756c66d214a1",
    "status": "QUEUED",
    "authorization_declaration_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
    "estimated_duration_seconds": 300
  }
  ```

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
