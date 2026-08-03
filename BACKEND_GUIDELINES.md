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

---

## 🎯 6. Scan Profile & Execution Policy Architecture

1. **ScanProfileRegistry Responsibilities**: `ScanProfileRegistry` (`app/application/assessment/scan_profiles.py`) manages 10 pre-configured enterprise scan profiles (`quick_scan`, `web_scan`, `api_scan`, `infrastructure_scan`, `owasp_top_10`, `owasp_api_top_10`, `full_assessment`, `authenticated_scan`, `passive_scan`, `custom_scan`) mapping profiles to required plugin ID subsets.
2. **PluginRegistry as Source of Truth**: `ScanProfileRegistry` MUST NOT duplicate plugin metadata, descriptions, or implementation logic. Plugin availability and capabilities are strictly validated against `PluginRegistry.list_plugins()`.
3. **ScanPolicyEngine Separation**: Execution policy enforcement is encapsulated in a dedicated `ScanPolicyEngine` (`app/application/assessment/policy_engine.py`) rather than tightly coupled inside `AssessmentService`.
4. **Stateless Policy Evaluation**: Policy methods (`validate_policy`, `is_url_in_scope`, `enrich_request_headers`, `enrich_request_cookies`, `should_stop_on_critical`) operate statelessly on `ScanPolicy` objects without side effects.
5. **Future Distributed Worker Compatibility**: `ScanPolicyEngine` has zero dependencies on web framework routers or database sessions, ensuring full compatibility for reuse inside Era 6 distributed Celery worker sandboxes.

---

## 🔗 7. Multi-Source Finding Correlation & Asset Inventory Architecture

1. **Optional asset_node_id Linkage**: `asset_node_id` on `SecurityFindingModel` remains `Optional[UUID]` to preserve complete backward compatibility for legacy scan findings without requiring schema migration defaults.
2. **Zero Graph Node Explosion**: Findings MUST NOT be duplicated as graph nodes in `asset_nodes`. Security findings remain stored in `security_findings` table, linked via `asset_node_id` and target URL.
3. **Risk Intelligence Reuse**: Asset risk score calculation reuses composite risk scores (`composite_risk_score`) produced by `RiskIntelligenceEngine` (Phase 4.5) rather than computing secondary risk scores.
4. **Mandatory Tenant Boundary Isolation**: Every repository method in `AssetInventoryRepository` and `AssetGraphRepository` MUST include explicit `organization_id` filters to guarantee zero cross-tenant asset data leakage.

---

## 📈 8. Continuous Monitoring & Posture Snapshotting Architecture

1. **Organization-Isolated, Job-Linked Snapshots**: Posture snapshots (`AssetSnapshotModel`) MUST be linked to `organization_id` and `assessment_job_id`, timestamped for immutable security audit trail history.
2. **Risk Engine Reuse**: Posture metrics (`avg_risk_score`, `max_risk_score`) MUST reuse Phase 4.5 `RiskIntelligenceEngine` composite scores (`f.risk.composite_risk_score`) directly without secondary calculators.
3. **Finding Lifecycle State Tracking**: `ChangeDetectionEngine` MUST evaluate vulnerability lifecycle shifts (`FINDING_NEW`, `FINDING_RESOLVED`, `FINDING_REOPENED`) across consecutive assessment runs.
4. **Tenant-Isolated Trend Analytics**: Every method in `AssetTrendRepository` MUST include mandatory `organization_id` filtering.

---

## 🏷️ 9. Finding Triage & Automated Suppression Architecture

1. **Backward Compatibility Preservation**: Finding triage MUST operate as an additional intelligence layer on top of existing `security_findings`. Original finding attributes, CVSS/EPSS risk scores, evidence artifacts, and asset graph linkages MUST NOT be overwritten or corrupted.
2. **Immutable Triage History**: Every finding triage state transition (`UNREVIEWED`, `CONFIRMED`, `FALSE_POSITIVE`, `RISK_ACCEPTED`, `REMEDIATED`, `REOPENED`) MUST be recorded in `FindingTriageHistoryModel` (`finding_triage_history` table) with actor attribution (`actor_user_id`), comments, and optional expiration dates (`risk_accepted_until`).
3. **Automated Suppression Rules**: `FindingSuppressionRuleModel` (`finding_suppression_rules` table) supports automated rule evaluation (`EXACT_CWE`, `TARGET_PATTERN`, `PLUGIN_ID`, `COMPOSITE`). Post-assessment, `FindingTriageService.evaluate_suppression_rules` overlays suppression metadata without altering underlying risk scores or evidence proof.
4. **Audit Logging Integration**: Triage operations MUST reuse existing `AuditLogService.record_event` patterns (`finding.triaged`, `suppression_rule.created`, `suppression_rule.deleted`).
5. **RBAC Guarding & Tenant Isolation**: Triage operations require `findings:triage` (`SECURITY_ANALYST`+), while suppression rule creation/deletion requires `findings:suppress` (`ADMIN`+). All repository queries MUST enforce mandatory `organization_id` tenant boundary isolation.

---

## 🤖 10. Multi-Provider LLM Gateway & Prompt Orchestrator Architecture

1. **Zero Mandatory Third-Party SDK Dependencies**: Provider adapters (`OpenAIAdapter`, `AnthropicAdapter`, `GoogleAdapter`, `LocalOllamaAdapter`) MUST execute REST requests using core `httpx.AsyncClient` without requiring third-party LLM SDK packages. Application startup MUST NOT fail if third-party LLM packages are uninstalled.
2. **Reusable Secret Encryption Service**: All external API keys and credentials MUST be encrypted at rest using AES-256-GCM (`SecretEncryptionService` in `app/security/encryption.py`), providing a reusable abstraction across Vulnova for cloud credentials and SIEM keys.
3. **Provider Health & Cooldown Tracking**: `LLMGatewayService` MUST track provider failures (`consecutive_failures`) and trigger a cooldown period (e.g. 5 minutes) when threshold is reached, automatically routing traffic to healthy secondary providers or local Ollama fallback.
4. **Immutable Security Prompt Versioning**: Prompt templates (`PromptTemplateModel`) are strictly immutable after creation. Modifying a prompt for an organization category and name MUST assign `version = max_version + 1` rather than overwriting existing records.
5. **Sensitive Prompt Context Sanitization**: `PromptOrchestratorService` MUST invoke `mask_sensitive_prompt_context` to strip/mask Authorization headers, Bearer tokens, cookies, API keys, and passwords before formatting prompt payloads.
6. **Internal Gateway Foundation for AI Agents**: `/ai/chat/completions` and `LLMGatewayService` serve as internal infrastructure. Future Era 5 AI agents (`AIFindingExplainerService`, `AttackPathSynthesizer`, `AIRemediationEngine`) MUST consume `LLMGatewayService` internally.

---

## 🤖 11. AI Finding Explainer & Impact Analysis Engine Architecture

1. **Domain Entity Classification**: `AIFindingExplanation` and `AIImpactAnalysis` are classified as **Domain Entities** (not Value Objects) because they possess persistent identity (`UUID`), lifecycle status (`COMPLETED`, `FAILED`, `STALE`), creation timestamps, and immutable audit history.
2. **Structured Output JSON Repair Recovery**: If initial LLM output fails JSON parsing, `AIFindingExplainerService` and `ImpactAnalysisService` MUST execute a retry-once recovery attempt using a strict JSON repair prompt before persisting a `FAILED` status record. Failed generation attempts MUST be recorded rather than silently discarded.
3. **Reuse Existing Risk Scores**: AI analysis services MUST read `risk_score` (the composite risk score from `RiskIntelligenceEngine`) directly from `SecurityFindingModel.risk_score`. Services MUST NOT recalculate or override composite risk scores.
4. **Context Sanitization & Prompt Injection Resistance**: All evidence dumps and finding descriptions MUST be passed through `mask_sensitive_prompt_context` prior to prompt rendering. System prompts MUST instruct the LLM to ignore embedded instructions in finding text.
5. **No Duplicate Request Logging**: AI analysis records store generated domain explanations and impact reports in `ai_finding_explanations` and `ai_impact_analyses` tables. Token consumption, latency, and USD costs are managed by `LLMGatewayService.generate_completion` and logged to `llm_request_logs`.



