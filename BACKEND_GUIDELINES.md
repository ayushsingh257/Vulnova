# Vulnova — Backend Code Standards & Engineering Guidelines (BACKEND_GUIDELINES.md)

This document specifies Python 3.12, FastAPI, Domain-Driven Design (DDD), and async programming standards for **Vulnova**.

---

## 🏛️ 1. Clean Architecture Layer Isolation

The backend codebase (`backend/app/`) is structured into strict architectural layers:

```
backend/app/
├── core/             # Framework configuration, security credentials, logging setup
├── domain/           # Core business entities, value objects, ports (abstract interfaces)
├── application/      # Use cases, scan orchestrator, AI pipelines, task definitions
├── infrastructure/   # Database adapters (SQLAlchemy, pgvector, Redis, Celery, LLM HTTP clients)
└── api/              # FastAPI HTTP routers, WebSocket handlers, Pydantic request/response schemas
```

### Layer Dependency Rule:
`api` -> `application` -> `domain` <- `infrastructure`

- **Core Rule**: `domain` NEVER imports from `infrastructure`, `api`, or `fastapi`.
- Concrete implementations in `infrastructure` implement ports defined in `domain`.

---

## 🐍 2. Python & FastAPI Code Rules

1. **Async by Default**: All I/O operations (database queries, HTTP calls, Redis operations) MUST be non-blocking using `async def` and `await`.
2. **Strict Type Annotations**: Every function parameter and return type must be explicitly type-annotated (`mypy --strict`).
3. **Pydantic v2 Schemas**: Request bodies and response models must use Pydantic models with explicit field descriptions and validation constraints.

```python
# Example FastAPI Endpoint Standard
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.schemas.scan import ScanCreateRequest, ScanResponse
from app.api.dependencies import get_current_user, require_permission
from app.domain.entities.user import User

router = APIRouter(prefix="/scans", tags=["Scans"])

@router.post(
    "",
    response_model=ScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("scans:create"))]
)
async def create_scan(
    payload: ScanCreateRequest,
    current_user: User = Depends(get_current_user)
) -> ScanResponse:
    """Dispatch a new dynamic security scan job."""
    # Use-case invocation logic here
    ...
```

---

## 🚨 3. Exception Handling & Error Hierarchy

Custom domain exceptions MUST inherit from `DomainException`:

```python
class DomainException(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)

class EntityNotFoundException(DomainException):
    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            message=f"{entity_name} with ID '{entity_id}' was not found.",
            code="ENTITY_NOT_FOUND"
        )
```

FastAPI exception handlers catch `DomainException` at the gateway boundary and convert them into standardized JSON responses (`API_SPEC.md`).

---

## 📜 4. Structured JSON Logging

All logs are emitted using `structlog` as formatted JSON:

```json
{
  "timestamp": "2026-08-01T12:00:00Z",
  "level": "info",
  "event": "scan_job_dispatched",
  "scan_job_id": "c73bcd8f-0e42-4f32-8419-756c66d214a1",
  "organization_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "correlation_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
}
```

---

## 🗄️ 5. Evidence Storage & Sensitive Data Sanitization

1. **Storage Provider Independence**: Evidence files (HTTP text dumps, HTML DOM snapshots, PNG screenshots) must be stored via `EvidenceArtifactStorage` interface abstraction supporting local storage (`uploads/evidence/<org_id>/<finding_id>/`) and future S3/MinIO cloud providers.
2. **Sensitive Data Sanitization**: Prior to persisting HTTP exchanges, headers, or cookies, all sensitive credentials (`Authorization` headers, `Cookie`/`Set-Cookie` directives, session IDs, JWT tokens, API keys) MUST be sanitized via `mask_sensitive_headers` and `mask_sensitive_cookies`.
3. **Integrity Verification**: Every evidence artifact MUST generate a SHA-256 checksum calculated over byte content upon save.
