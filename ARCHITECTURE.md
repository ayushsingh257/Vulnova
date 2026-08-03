# Vulnova — System Architecture & Design Specification (ARCHITECTURE.md)

This document describes the high-level architecture, subsystem boundaries, scanner sandbox isolation model, extensible plugin framework, event-driven architecture roadmap, data flow pipelines, microservice migration path, and component contracts for **Vulnova**.

---

## 📐 1. Architectural Principles & Clean Architecture

Vulnova is built around **Clean Architecture** and **Domain-Driven Design (DDD)** principles.

```
       ┌─────────────────────────────────────────────────────────┐
       │   Presentation Layer (Next.js 14 / FastAPI Routers)     │
       └───────────────────────────┬─────────────────────────────┘
                                   │
       ┌───────────────────────────▼─────────────────────────────┐
       │   Application Services (Scan Orchestrator, AI Engine)  │
       └───────────────────────────┬─────────────────────────────┘
                                   │
       ┌───────────────────────────▼─────────────────────────────┐
       │   Domain Layer (Entities, Value Objects, Security Rules)│
       └───────────────────────────▲─────────────────────────────┘
                                   │
       ┌───────────────────────────┴─────────────────────────────┐
       │   Infrastructure (PostgreSQL, Redis, Celery, Vector DB) │
       └─────────────────────────────────────────────────────────┘
```

1. **Independent of Frameworks**: Business logic in the Domain Layer does not depend on FastAPI, Next.js, or SQLAlchemy.
2. **Testable**: Domain rules and security scoring logic can be tested in isolation without spinning up web servers or databases.
3. **Independent of Database**: Swapping PostgreSQL or Redis adapters does not impact scan orchestration or AI analysis workflows.
4. **Independent of External Interfaces**: Scanners and AI providers are encapsulated behind abstract port interfaces (`ScannerPort`, `AIProviderPort`).

---

## 🛡️ 2. Scanner Sandbox Architecture & Worker Isolation

Because Vulnova executes dynamic security checks against external web targets, scanning workloads represent untrusted execution paths that MUST be completely isolated from the platform core control plane and database infrastructure.

```
                  ┌─────────────────────────────────────────┐
                  │   Vulnova Core Control Plane            │
                  │   (FastAPI Gateway & Control DB)        │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │          Scan Orchestrator              │
                  │   (Task Dispatcher & Scope Enforcer)    │
                  └────────────────────┬────────────────────┘
                                       │ Ephemeral Task Dispatch
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │  Isolated Scanner Sandbox Workers       │
                  │  (Unprivileged Worker Pool)             │
                  └─────────────────────────────────────────┘
```

### Sandbox Security Controls:
1. **Container Isolation**: Scanner worker processes run in unprivileged Linux containers (`read_only_rootfs: true`, `security_opt: [no-new-privileges:true]`, non-root user `UID 10001`). All Linux capabilities (`CAP_SYS_ADMIN`, `CAP_NET_RAW`) are dropped.
2. **Resource Limits**:
   - Max CPU per worker: `1.0 vCPU`
   - Max RAM per worker: `512MB`
   - Temporary Scratch Disk: `100MB` (in-memory `tmpfs`, wiped upon task completion)
3. **Network Restrictions & Egress Control**:
   - Internal Network Isolation: Workers are attached to a dedicated `sandbox_net` Docker bridge network with strict firewall rules blocking access to Vulnova control DBs, Redis, or internal management subnets.
   - Outbound Proxy: All scanner outbound traffic routes through a dedicated Egress Proxy filtering SSRF targets (preventing scans from hitting `169.254.169.254` AWS metadata or local loopbacks `127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`).
4. **Timeout Controls**: Hard execution caps (max 60 seconds per HTTP payload check, max 30 minutes per total scan job). Hung worker processes are force-killed by the orchestrator.
5. **Prevention of Core Compromise**: Sandbox workers communicate back to the orchestrator strictly via one-way JSON task result queues. Workers do not hold database connection strings or master encryption keys.

---

## 🧩 3. Enterprise Assessment Intelligence Pipeline & Evidence Subsystem

Vulnova transforms raw scanner outputs into normalized, deduplicated, and fully evidenced security intelligence prior to database persistence and AI analysis.

```
Assessment Request
        │
        ▼
Scan Profile Registry ──► (10 Predefined Enterprise Profiles ──► Plugin ID Subset Resolution)
        │
        ▼
Scan Policy Engine   ──► (RPS Throttling + Concurrency + Scope Rules + Auth Injection + Stop on Critical)
        │
        ▼
Plugin Execution     ──► (10 Production Security Assessment Plugins)
        │
        ▼
   Raw Findings
        │
        ▼
Risk Intelligence Engine ──► (CVSS v3.1/v4 + EPSS + Asset Multipliers ──► 0-100 Risk Score)
        │
        ▼
 Finding Deduplicator   ──► (SHA-256 Signature Hash ──► Canonical Link & Duplicate Flag)
        │
        ▼
Evidence Collection Engine ─► (Mask Headers/Cookies + HTTP Dumps + DOM Snapshots + PNG Screenshots)
        │
        ▼
Multi-Source Correlation Engine ─► (Link Finding to AssetNode + Aggregate Composite Risk Posture)
        │
        ▼
Posture Snapshot & Change Engine ──► (Compute Posture Snapshot + Track Finding Lifecycle State + Record Change Events)
        │
        ▼
Finding Triage & Suppression Engine ──► (Automated Suppression Rules + Analyst Triage Workflow + Audit History)
        │
        ▼
Normalized Database & Storage ──► (Storage Provider Bytes + DB Findings & Inventory Metadata)
        │
        ▼
Asset Inventory Intelligence & AI Security Copilot
```

### A. Profile-Driven Execution & Policy Enforcement
- **ScanProfileRegistry**: Maps enterprise scan profiles (`Quick Scan`, `Web Scan`, `API Scan`, `Infrastructure Scan`, `OWASP Top 10`, `OWASP API Top 10`, `Full Assessment`, `Authenticated Scan`, `Passive Scan`, `Custom Scan`) to required plugin execution subsets. `PluginRegistry` remains the single source of truth for plugin capability verification.
- **ScanPolicyEngine**: Centralized, stateless policy evaluator enforcing concurrency caps, rate limits (requests/sec), `robots.txt` compliance, wildcard include/exclude scope URL rules, custom authentication header/cookie injection, and `stop_on_critical` emergency scan termination triggers.
- **Era 6 Distributed Worker Compatibility**: `ScanPolicyEngine` is designed without tight coupling to `AssessmentService` or FastAPI HTTP layers. Its stateless functions (`validate_policy`, `is_url_in_scope`, `enrich_request_headers`, `should_stop_on_critical`) allow direct reuse inside distributed Celery worker sandboxes in Era 6.

### B. Risk Intelligence & Deduplication
- **RiskIntelligenceEngine**: Normalizes CVSS v3.1/v4 vectors, EPSS exploit likelihood scores, asset criticality multipliers (1.5x, 1.2x, 1.0x, 0.8x), composite risk scores (0.0–100.0), business impact ratings, and remediation SLA hour thresholds (Critical: 24h, High: 72h, Medium: 336h, Low: 720h).
- **FindingDeduplicator**: Generates SHA-256 signature hashes over `(organization_id, plugin_id, cwe_id, target_endpoint, parameter_name)` to merge duplicate finding instances into primary canonical findings.

### C. Multi-Modal Evidence Subsystem
- **EvidenceCollectionEngine**: Captures multi-modal proof for every normalized finding, including formatted HTTP request/response dumps, header JSON, cookie profiles, Playwright rendered HTML DOM snapshots, and visual PNG screenshots.
- **Sensitive Data Sanitization**: Automatically masks `Authorization` headers (`Bearer *******`, `Basic *******`), session cookies, API keys, and JWT tokens (`eyJ...`) before storage.
- **Storage Provider Independence**: `EvidenceArtifactStorage` provides an abstraction layer managing byte content, local filesystem paths (`uploads/evidence/<org_id>/<finding_id>/`), and future S3/MinIO cloud object stores.
- **Integrity Verification**: Computes a SHA-256 checksum for every saved evidence artifact to guarantee proof non-repudiation and data integrity.

### D. Multi-Source Finding Correlation & Asset Inventory Subsystem
- **AssessmentCorrelationEngine**: Synthesizes discovery targets (`AssetNode`), running technology stack fingerprints (`RUNS_TECH`), security findings, and evidence artifacts into consolidated asset risk posture metadata.
- **Backward Compatibility & Optional Linkage**: `asset_node_id` remains an optional field (`Optional[UUID]`) on `SecurityFindingModel` to ensure legacy findings remain valid without breaking existing database schemas.
- **Zero Graph Explosion**: Security findings remain in `security_findings` rather than duplicated as individual graph nodes, maintaining clean and fast graph topology traversal.
- **Risk Score Aggregation**: Asset composite risk scores reuse existing Phase 4.5 `RiskIntelligenceEngine` metrics (`composite_risk_score`) to aggregate maximum severity and risk ratings per asset node.

### E. Attack Surface Trend & Continuous Monitoring Subsystem
- **ContinuousMonitoringService**: Computes point-in-time posture snapshots (`AssetSnapshotModel`) linked to `organization_id` and `assessment_job_id`, timestamped for immutable security audit history.
- **ChangeDetectionEngine**: Compares current assessment state against historical baseline snapshots to detect vulnerability finding lifecycle transitions (`FINDING_NEW`, `FINDING_RESOLVED`, `FINDING_REOPENED`) and records discrete audit events in `AssetChangeEventModel`.
- **Historical Risk Trajectory**: Exposes organizational risk score trajectories (`GET /api/v1/assets/trends`) and posture event timelines (`GET /api/v1/security/posture/timeline`) reusing Phase 4.5 `RiskIntelligenceEngine` composite scores directly.
- **Tenant Boundary Security**: All inventory lookup APIs (`GET /api/v1/assets/inventory`, `GET /api/v1/assets/{asset_id}`) strictly enforce tenant boundary isolation (`organization_id`).

---

## ⚡ 4. Event-Driven Architecture Evolution Roadmap

Vulnova initiates task distribution via Celery and Redis. As platform scale demands grow, the architecture transitions to an **Event-Driven Architecture (EDA)** leveraging an enterprise event bus.

```
 [Target Verified] ──► (ScanCreatedEvent)
                              │
                              ▼
                     [Discovery Worker] ──► (DiscoveryCompletedEvent)
                                                   │
                                                   ▼
                                        [Assessment Worker Pool]
                                                   │
                                                   ├─► (AssessmentStartedEvent)
                                                   └─► (FindingCreatedEvent)
                                                             │
                                                             ▼
                                                   [Evidence & Risk Engine] ──► (FindingEnrichedEvent)
                                                             │
                                                             ▼
                                                   [AI Analyst Engine] ──► (AIAnalysisCompletedEvent)
```

### Supported Event Payload Types:
1. `ScanCreatedEvent`: Dispatched when target authorization is confirmed and a scan job is queued.
2. `DiscoveryCompletedEvent`: Emitted after crawling completes, carrying asset inventory tree payload.
3. `AssessmentStartedEvent`: Emitted when DAST plugins initialize execution against target endpoints.
4. `FindingCreatedEvent`: Emitted whenever a DAST plugin confirms a raw vulnerability.
5. `AIAnalysisCompletedEvent`: Emitted when the AI Analyst finishes CVSS scoring, attack path synthesis, and remediation code patch generation.

### Event Bus Migration Path:
The application uses an abstract `EventBusPort`. While initial phases utilize Celery + Redis Pub/Sub, the interface supports seamless drop-in adapters for **RabbitMQ (AMQP)**, **Apache Kafka**, or **NATS JetStream** without modifying domain logic.

---

## 🔀 5. Extensible Security Plugin Framework

Vulnova features a modular plugin architecture that allows security engineers to add custom assessment checks without modifying the core scanning engine.

### A. Plugin Directory Structure
```
plugins/
└── sqli_assessment/
    ├── plugin.yaml
    ├── __init__.py
    ├── plugin.py
    └── payloads.json
```

### B. `plugin.yaml` Metadata Schema
Every security plugin is self-describing via a mandatory `plugin.yaml` manifest:

```yaml
plugin:
  name: "Advanced SQL Injection Detector"
  id: "vuln-dast-sqli-v1"
  version: "1.2.0"
  author: "Vulnova Security Core Team"
  description: "Detects error-based, time-based blind, and boolean-based SQL injection vulnerabilities."
  category: "INJECTION"
  severity: "CRITICAL"
  cwe_mapping:
    - "CWE-89"
  owasp_mapping:
    - "A03:2021-Injection"
    - "API8:2023-Security-Misconfiguration"
  execution_requirements:
    timeout_seconds: 120
    max_requests: 150
    requires_browser_dom: false
  required_permissions:
    - "network:outbound"
```

### C. Dynamic Plugin Execution Interface
The core scanner engine scans the `/plugins` registry on boot, validates `plugin.yaml` manifests against Pydantic schemas, and loads compliant plugins into the assessment pipeline.

---

## ⚡ 4. Event-Driven Architecture Evolution Roadmap

Vulnova initiates task distribution via Celery and Redis. As platform scale demands grow, the architecture transitions to an **Event-Driven Architecture (EDA)** leveraging an enterprise event bus.

```
 [Target Verified] ──► (ScanCreatedEvent)
                              │
                              ▼
                     [Discovery Worker] ──► (DiscoveryCompletedEvent)
                                                   │
                                                   ▼
                                        [Assessment Worker Pool]
                                                   │
                                                   ├─► (AssessmentStartedEvent)
                                                   └─► (FindingCreatedEvent)
                                                              │
                                                              ▼
                                                   [AI Analyst Engine] ──► (AIAnalysisCompletedEvent)
```

### Supported Event Payload Types:
1. `ScanCreatedEvent`: Dispatched when target authorization is confirmed and a scan job is queued.
2. `DiscoveryCompletedEvent`: Emitted after crawling completes, carrying asset inventory tree payload.
3. `AssessmentStartedEvent`: Emitted when DAST plugins initialize execution against target endpoints.
4. `FindingCreatedEvent`: Emitted whenever a DAST plugin confirms a raw vulnerability.
5. `AIAnalysisCompletedEvent`: Emitted when the AI Analyst finishes CVSS scoring, attack path synthesis, and remediation code patch generation.

### D. AI Finding Explainer & Impact Analysis Engine Subsystem (Phase 5.2)
The Phase 5.2 AI analysis subsystem operates as an autonomous AI Security Analyst layer:
- **AIFindingExplainerService**: Consumes Era 4 normalized findings, evidence dumps, and triage state to generate 8-field structured vulnerability explanations via LLM gateway with a retry-once JSON repair recovery strategy.
- **ImpactAnalysisService**: Enriches vulnerability data with CVSS vectors, EPSS probabilities, asset graph topology (`AssetNode`), composite risk scores (reads existing `risk_score` without recalculation), and evidence artifacts to produce executive and technical impact analysis reports.
- **Persistence & Auditability**: Stores immutable append-only records in `ai_finding_explanations` and `ai_impact_analyses` tables while reusing Phase 5.1's `LLMGatewayService` for token budget tracking and request audit logging.

### Event Bus Migration Path:
The application uses an abstract `EventBusPort`. While initial phases utilize Celery + Redis Pub/Sub, the interface supports seamless drop-in adapters for **RabbitMQ (AMQP)**, **Apache Kafka**, or **NATS JetStream** without modifying domain logic.

---

## 🔄 5. Core Component Interfaces

### A. Scanner Plugin Interface (`backend/app/domain/ports/scanner.py`)
```python
from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel

class TargetContext(BaseModel):
    url: str
    headers: dict
    cookies: dict
    tech_stack: List[str]

class RawFinding(BaseModel):
    plugin_id: str
    title: str
    severity_label: str
    target_url: str
    request_dump: str
    response_dump: str
    evidence_id: str

class AssessmentPluginPort(ABC):
    @property
    @abstractmethod
    def plugin_id(self) -> str:
        pass

    @abstractmethod
    async def execute(self, target: TargetContext) -> List[RawFinding]:
        """Execute vulnerability tests against target context."""
        pass
```

### B. AI Security Analyst Interface (`backend/app/domain/ports/ai_analyst.py`)
```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class AIAnalysisResult(BaseModel):
    cvss_score: float
    cvss_vector: str
    technical_impact: str
    business_impact: str
    attack_scenario: str
    remediation_patch: str
    false_positive_probability: float

class AIAnalystPort(ABC):
    @abstractmethod
    async def analyze_finding(
        self, 
        finding: RawFinding, 
        business_context: str
    ) -> AIAnalysisResult:
        """Perform contextual AI analysis on raw scanner finding."""
        pass
```

---

## 🔀 6. Microservice Migration Path

While Vulnova starts as a modular FastAPI monolith, every domain component is strictly isolated to allow seamless migration to independent microservices:

1. **Discovery Service**: Can be split into standalone worker deployment with dedicated Chromium instances.
2. **Assessment Engine Service**: Can scale horizontally as independent stateless scanner pods.
3. **AI Analyst Service**: Can run on dedicated GPU instances hosting local LLM inference engines (Ollama / vLLM).
4. **Control Plane / API Gateway**: Remains lightweight FastAPI gateway managing OAuth2, routing, and WebSocket streaming.

---

## 🤖 7. Multi-Provider LLM Gateway & Prompt Orchestrator Architecture (Phase 5.1)

Phase 5.1 establishes Vulnova's enterprise AI infrastructure abstraction layer:

```text
Era 4 Normalized Findings & Evidence
                 │
                 ▼
     [PromptOrchestratorService]
     ├── Sensitive Secret Masking (mask_sensitive_prompt_context)
     ├── Variable Interpolation & Security Context Format
     └── Immutable Prompt Versioning (version = max_ver + 1)
                 │
                 ▼
        [LLMGatewayService]
        ├── Provider Health Tracking (Cooldown on 3 consecutive errors)
        ├── Priority-Based Fallback Routing
        └── Token Budget & Cost Estimation ($/1K tokens)
                 │
                 ▼
   ┌─────────────┼─────────────┬─────────────┐
   ▼             ▼             ▼             ▼
[OpenAI]    [Anthropic]    [Google]      [Ollama]
Adapter      Adapter       Adapter       Adapter
(httpx)      (httpx)       (httpx)       (httpx)
```

### Architectural Axioms:
1. **Zero Mandatory SDK Dependencies**: Provider adapters (`OpenAIAdapter`, `AnthropicAdapter`, `GoogleAdapter`, `LocalOllamaAdapter`) execute raw REST requests via `httpx.AsyncClient`. Zero third-party SDK packages are required, preventing startup failures in air-gapped or local Ollama deployments.
2. **Reusable Secret Encryption**: Provider API keys are encrypted at rest using AES-256-GCM (`SecretEncryptionService`), reusable across Vulnova for cloud and SIEM integration credentials.
3. **Health Cooldown & Automatic Fallback**: The gateway tracks provider failures and puts unhealthy providers into a cooldown state, routing requests to secondary providers or local Ollama fallback.
4. **Immutable Security Prompt Templates**: Prompts (`PromptTemplateModel`) are versioned immutably to guarantee audit reproducibility.
5. **Internal Gateway Foundation**: Downstream Era 5 agents (`AIFindingExplainerService`, `AttackPathSynthesizer`, `AIRemediationEngine`) consume `LLMGatewayService` internally rather than HTTP routing.

