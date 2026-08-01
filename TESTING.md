# Vulnova — Testing Strategy & Quality Assurance Matrix (TESTING.md)

This document defines the testing strategy, test pyramid breakdown, framework tools, DAST engine self-testing, security regression tests, and code coverage requirements for **Vulnova**.

---

## 🧪 1. Testing Pyramid & Minimum Standards

Vulnova enforces strict testing standards across all components:

| Test Level | Framework / Tool | Scope | Minimum Coverage Target |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | `pytest` / `vitest` | Domain logic, Pydantic schemas, UI components, utility parsers | **85% Line Coverage** |
| **Integration Tests** | `pytest-asyncio` + TestContainers | FastAPI routers, PostgreSQL queries, Redis caching, Celery tasks | **80% Path Coverage** |
| **E2E UI Tests** | `Playwright` | Full user flows: Login, Scan Launch, Live Progress, Triage | **100% Critical Flows** |
| **DAST Verification** | Custom Vulnerable Testbed | DAST scanner plugins tested against intentionally vulnerable apps | **100% Plugin Detection Accuracy** |
| **Security Gates** | `Semgrep`, `Gitleaks`, `Trivy` | SAST, secret leak detection, container image vulnerabilities | **Zero High/Critical Findings** |

---

## ⚡ 2. Backend Unit & Integration Testing (`pytest`)

### A. Fixture Standard
Integration tests use `TestContainers` to spin up isolated PostgreSQL (`pgvector`) and Redis instances:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check_returns_200():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

---

## 🎭 3. Frontend & End-to-End Testing (`Playwright`)

End-to-end tests verify key customer workflows in Chromium:

- User Registration & OAuth Login
- Organization Settings & Team Invitation
- Launching Dynamic Security Scan
- Monitoring WebSocket Live Progress Stream
- Viewing AI Security Analyst Remediation Patch

---

## 🛡️ 4. DAST Plugin Verification Suite

Every DAST assessment plugin (SQLi, XSS, SSRF, IDOR) must pass automated verification against standard vulnerable test targets (e.g., OWASP Juice Shop or custom benchmark containers) to ensure:
- Zero false negatives on benchmark vulnerabilities.
- Zero false positives on safe benchmark parameters.
- Clean execution within target timeout limits.
