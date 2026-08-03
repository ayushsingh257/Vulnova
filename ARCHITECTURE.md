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

### H. Security Knowledge Base & RAG Vector Engine Subsystem (Phase 5.6)
- **AIRAGKnowledgeService**: Implements Retrieval-Augmented Generation (RAG) vector engine backed by PostgreSQL `pgvector` (`vector(1536)`).
- **Source-Type Chunking & Embedding Metadata**: Configurable text chunking (`OWASP`/`CWE`: 512, `CVE_NVD`: 256, `INTERNAL_POLICY`: 768) with `embedding_model` and `embedding_dimension` tracking.
- **Governance Approval Workflow**: Human review lifecycle (`UNDER_REVIEW` -> `APPROVED` -> `INDEXED`) for uploaded security policies.

### I. Enterprise AI Security Copilot Subsystem (Phase 5.7)
- **SecurityCopilotService**: Conversational SOC analyst assistant synthesizing intelligence from all Era 5 engines into multi-turn investigation sessions.
- **AgentOrchestrator**: Multi-agent intent classification router dispatching queries to specialized sub-agent personas (`SECURITY_ANALYST`, `EXPLAINER`, `ATTACK_PATH`, `REMEDIATION`, `FALSE_POSITIVE`, `KNOWLEDGE_RAG`).
- **CopilotToolRegistry**: Safe read-only internal tool calling registry executing 7 security tools (`get_finding_details`, `get_asset_topology`, `get_risk_summary`, `search_rag_knowledge`, `get_remediation_plan`, `get_confidence_analysis`, `get_attack_path`) with audit logging.
- **Grounding & Explainability Tracking**: Assistant responses record explainability metadata (`response_confidence_score`, `sources_used`, `knowledge_chunks_used`, `tools_called`, `reasoning_summary`, `model_used`, `prompt_version`, `response_evaluation_metadata`).
- **Strict Non-Autonomous Read-Only Policy**: Operating strictly under human-in-the-loop controls with zero automated infrastructure mutation or finding suppression capability.

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

### E. AI Attack Path Synthesis Engine Subsystem (Phase 5.3)
The Phase 5.3 attack path synthesis subsystem provides graph-aware attack chain reasoning:
- **AIAttackPathService**: Synthesizes evidence-grounded attack paths from findings, evidence artifacts, and Asset Graph topology. Validates MITRE ATT&CK technique IDs (`T1190`, `T1059`, `T1068`, `T1021`, etc.) against `KNOWN_MITRE_TECHNIQUES` registry, calculates overall path confidence scores, and masks sensitive secrets.
- **Option A Relational Storage**: Persists normalized master/detail tables (`ai_attack_paths` and `ai_attack_path_steps`) for sub-millisecond relational queries by MITRE technique or finding ID.
- **SOC Analyst Feedback Loop**: Supports review state transitions (`GENERATED`, `REVIEWED`, `ACCEPTED`, `REJECTED`, `STALE`) and records reviewer notes and timestamps (`review_notes`, `reviewed_by`, `reviewed_at`).

### F. AI Remediation Engine & Fix Recommendation Subsystem (Phase 5.4)
The Phase 5.4 remediation subsystem transforms multi-layer vulnerability intelligence into non-executable fix recommendations:
- **AIRemediationService**: Synthesizes multi-tier remediation plans, step actions, and code/config patch diff suggestions (`PYTHON`, `JAVASCRIPT`, `GO`, `JAVA`, `NGINX`, `DOCKER`, `TERRAFORM`, `YAML`) from 7 intelligence layers under a strict **Human Approval Safety Policy** (zero auto-execution capability).
- **3-Table Normalized Relational Schema**: Persists master plans (`ai_remediation_plans`), step actions (`ai_remediation_steps`), and code patch diffs (`ai_patch_suggestions`) with CVE/CWE mapping, dual confidence metrics (`ai_confidence_score`, `effectiveness_confidence_score`), and operational risk flags (`requires_backup`, `requires_downtime`, `rollback_available`).
- **Analyst Review State Machine**: Supports review workflows (`GENERATED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `IMPLEMENTED`, `VERIFIED`, `VALIDATION_FAILED`) with reviewer attribution (`reviewed_by`, `review_notes`).

### G. AI False Positive Filter & Finding Confidence Subsystem (Phase 5.5)
The Phase 5.5 confidence subsystem delivers analyst-assisted finding classification and duplicate similarity intelligence:
- **AIConfidenceAnalysisService**: Evaluates security findings across 8 intelligence layers to produce classifications (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `NEEDS_REVIEW`), confidence scores (0.0–1.0), evidence quality ratings (0.0–1.0), and multi-signal duplicate similarity matches across 8 signals (`CVE`, `CWE`, `ENDPOINT`, `ASSET_NODE`, `PLUGIN_ID`, `VULNERABILITY_TITLE`, `AFFECTED_COMPONENT`, `ATTACK_TECHNIQUE`).
- **Non-Suppression Safety Policy**: AI evaluations serve as advisory analyst intelligence. Zero automated finding closure, deletion, or suppression code exists in the service.
- **Score Calibration Feedback Loop**: Records calibration tracking metadata (`predicted_confidence_score`, `analyst_final_decision`, `confidence_accuracy_delta`, `feedback_timestamp`) during analyst review (`PATCH /api/v1/ai/confidence-analysis/{id}/review`).

### H. Security Knowledge Base & RAG Vector Subsystem (Phase 5.6)
The Phase 5.6 RAG subsystem provides vector-indexed security knowledge retrieval:
- **AIRAGKnowledgeService**: Orchestrates document ingestion, source-type configurable text chunking (`OWASP`/`CWE`/`CAPEC`: 512/64, `CVE_NVD`: 256/32, `INTERNAL_POLICY`: 768/128), embedding vector generation, document governance approval workflows (`UNDER_REVIEW` -> `APPROVED` -> `INDEXED`), semantic vector similarity search, and tailored finding RAG context block formatting.
- **PostgreSQL pgvector & HNSW Storage**: Stores 1536-dimensional embeddings in `security_knowledge_chunks` with HNSW cosine similarity indexing (`vector_cosine_ops`, `m=16`, `ef_construction=64`) across 3 normalized tables (`security_knowledge_documents`, `security_knowledge_chunks`, `rag_search_logs`).
- **Hybrid Tenant Boundary Protection**: Enforces `organization_id IS NULL OR organization_id = tenant_id` to allow shared global benchmarks (OWASP/CWE) while isolating private tenant security policies.

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

---

## ⚡ 8. Distributed Scanning Orchestration & Worker Sandbox Architecture (Phase 6.1)

Phase 6.1 establishes Vulnova's distributed worker application and container sandbox security infrastructure:

```text
               [ Control Plane API Gateway ]
                             │
                             ▼
              [ WorkerOrchestratorService ]
              ├── Task Security Validation
              ├── Container Sandbox Config (1 vCPU, 512MB RAM)
              └── Multi-Tenant Audit Logging
                             │
                             ▼
                [ Celery Priority Queues ]
         ┌───────────────┼───────────────┬───────────────┐
         ▼               ▼               ▼               ▼
   [scans.high]   [scans.default]  [scans.low]    [ai.priority]
         │               │               │               │
         └───────────────┼───────────────┴───────────────┘
                         │
                         ▼
        [ Celery Worker Sandbox Cluster ]
       (UID 10001, Read-Only RootFS, Egress Filter)
```

### Architectural Axioms:
1. **Container Sandbox Isolation**: Worker task executions enforce container sandbox resource limits (`cpu_limit_vcpu=1.0`, `memory_limit_mb=512`, `read_only_rootfs=True`, `no_new_privs=True`, unprivileged UID/GID `10001`, dropped `ALL` capabilities, and network egress filtering).
2. **Execution Isolation Safeguard**: Celery workers do NOT execute raw OS commands directly. All job executions pass through `Celery Worker -> Task Queue -> Sandbox Executor -> Job Dispatch`.
3. **Multi-Tenant Database Auditing**: `WorkerNodeModel` (`worker_nodes`) and `WorkerTaskModel` (`worker_task_executions`) include `organization_id` and `requested_by` fields for multi-tenant isolation and capacity metrics calculation.

---

## 🎯 9. Target Scan Configuration & Authorized Assessment Contract Architecture (Phase 6.2)

Phase 6.2 deploys a mandatory pre-scan legal authorization gate and scan target management subsystem:

```text
               [ API Request: POST /assessments ]
                              │
                              ▼
                 [ AssessmentPolicyEngine ]
    1. Check is_authorized_assessment == True (Consent)
    2. Lookup target URL in scan_targets table (Registration)
    3. Verify target status == ACTIVE (Lifecycle)
    4. Validate SSRF Egress Firewall (Safety)
    5. Persist authorization_declarations record (Audit)
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
        [ REJECT (403) ]              [ ALLOW (201) ]
  (Missing consent, unregistered,      (Passes to AssessmentService
   archived, or SSRF prohibited)        & WorkerOrchestrator)
```

### Architectural Axioms:
1. **Mandatory Authorization Consent**: Every assessment scan request must explicitly include `is_authorized_assessment=True`. Unconfirmed requests are hard-rejected with HTTP 403 Forbidden.
2. **Scan Target Registration Gate**: Target URLs must be pre-registered in `scan_targets` under the requesting organization with `ACTIVE` status before scanning.
3. **Immutable Consent Audit Trail**: Every authorization consent event persists a timestamped `authorization_declarations` record (`scan_target_id`, `declared_by`, `authorization_scope`, `ip_address`) for legal compliance.
4. **Worker Dispatch Protection**: `WorkerOrchestratorService` enforces authorization metadata validation prior to Celery priority queue dispatching, preventing unauthorized background task executions.

---

## 🔄 10. Scan Execution Lifecycle State Machine & Retry Engine Architecture (Phase 6.3)

Phase 6.3 establishes Vulnova's scan execution state machine, distributed Redis lock manager, and retry engine:

```text
               [ API / Worker Scan Request ]
                             │
                             ▼
              [ DistributedScanLockManager ]
              ├── Check Redis Lock (lock:scan:{org_id}:{target_sha256})
              └── Reject Duplicate Executions (HTTP 409 Conflict)
                             │
                             ▼
             [ ScanLifecycleManagerService ]
       [QUEUED] ──► [CRAWLING] ──► [ASSESSING] ──► [AI_ANALYSIS] ──► [COMPLETED]
          │             │              │                │
          │         (Error)        (Error)          (Error)
          │             │              │                │
          ▼             └──────────────┼────────────────┘
      [CANCELLED]                      ▼
                            [RETRYING] (attempt < max)
                                       │
                                   (Exhausted)
                                       ▼
                                   [FAILED]
```

### Architectural Axioms:
1. **Granular Execution Lifecycle**: Scans advance through explicit states (`QUEUED` → `CRAWLING` → `ASSESSING` → `AI_ANALYSIS` → `COMPLETED`). Out-of-order state jumps are rejected by a strict `VALID_TRANSITIONS` matrix.
2. **Distributed Redis Target Locking**: `DistributedScanLockManager` uses atomic Redis SETNX keys (`lock:scan:{org_id}:{url_sha256}`) to prevent concurrent duplicate scan runs against identical target assets.
3. **Exponential Backoff Retry Engine**: Transient scan failures trigger managed retries with exponential backoff (`base_delay=5s`, `backoff_factor=2.0`, `max_retries=3`).
4. **Terminal Failure & Lock Cleanup**: Terminal failure or cancellation hooks release distributed locks automatically and record timestamped audit entries (`scan.state_transition`).



