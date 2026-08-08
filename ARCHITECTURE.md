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

---

## 📡 11. Real-Time Scan Progress & WebSocket Event Stream Architecture (Phase 6.4)

Phase 6.4 introduces a high-throughput, low-latency WebSocket event streaming server and Redis Pub/Sub adapter (`/api/v1/ws/scans/{scan_id}`):

```text
         [ ScanLifecycleManagerService ]  (Single Source of Truth)
                       │
                       ▼
          [ ScanEventPublisherService ]
                       │
                       ▼
      [ RedisPubSubManager (Redis Channel) ]
   "vulnova:scan:events:{org_id}:{scan_id}"
                       │
                       ▼
         [ ScanStreamManagerService ]
       ├── WebSocket Connection Registry
       ├── Heartbeat Timeout Cleanup (90s)
       └── Payload Size Validation (64KB)
                       │
                       ▼
    [ WebSocket Endpoint: /api/v1/ws/scans/{scan_id} ]
       ├── 1. JWT Auth Handshake (?token=...)
       ├── 2. Tenant Isolation Check (org_id match)
       ├── 3. RBAC Permission (scans:read)
       └── 4. Real-Time JSON Event Fanout (<100ms)
```

### Key Architectural Safeguards:
1. **Single Source of Truth**: State transition logic strictly resides in `ScanLifecycleManagerService`. The WebSocket streaming layer never mutates scan states; it listens to and broadcasts lifecycle events.
2. **Decoupled Redis Pub/Sub**: `RedisPubSubManager` decouples background Celery scanner workers from web server processes, allowing multi-node event fanout with an in-memory queue fallback for offline/test environments.
3. **Connection Rate Limiting & Protection**:
   - `MAX_CONNECTIONS_PER_ORG = 50` (Max concurrent WebSocket connections per tenant).
   - `HEARTBEAT_INTERVAL_SECONDS = 30` (30s ping/pong heartbeats).
   - `CONNECTION_TIMEOUT_SECONDS = 90` (Stale connection pruning).
   - `MAX_EVENT_PAYLOAD_SIZE = 64KB` (Event payload size cap).

---

## 🖥️ 12. Scan Management Portal & Frontend Service Abstraction (Phase 7.4)

Phase 7.4 introduces the **Scan Management Portal & Live Monitor Gateway**, establishing a clean decoupling between frontend UI components, API service abstraction, and backend scan operations:

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                         Security Analyst Web Portal                         │
  │                  (/scans  &  /scans/[id] Telemetry Route)                   │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                     Frontend Scans Service Abstraction                      │
  │                     (frontend/services/scans.service.ts)                    │
  └───────────────────┬─────────────────────────────────────┬───────────────────┘
                      │ REST API                            │ WebSocket Stream
                      ▼                                     ▼
  ┌───────────────────────────────────────┐   ┌─────────────────────────────────┐
  │      FastAPI Assessment Router        │   │   WebSocket Scan Stream Router    │
  │   (/api/v1/assessments, /telemetry)   │   │(/api/v1/scans/{scan_id}/stream) │
  └─────────┬───────────────────┬─────────┘   └─────────────────┬───────────────┘
            │                   │                               │
            ▼                   ▼                               ▼
┌──────────────────────┐ ┌──────────────────────┐   ┌───────────────────────────┐
│  AssessmentService   │ │ScanManagementService │   │   Redis Pub/Sub Channel   │
│(Creation & Dispatch) │ │(Listing, Controls)   │   │(vulnova:scan:events:{org})│
└──────────────────────┘ └──────────┬───────────┘   └───────────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  PostgreSQL Database │
                         │  (assessment_jobs)   │
                         └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Target Data Exposure Protection**: Exposes ONLY domain-masked target URL identifiers (`https://a***.s***.e***.com`) in summary list endpoints (`GET /api/v1/assessments`). Full raw target URLs are restricted to authorized detail endpoints (`GET /api/v1/assessments/{id}/telemetry`) with `scans:read` permissions.
2. **Decoupled Application Services Architecture**: `ScanManagementService` handles paginated queries (`list_assessments_paginated`), telemetry payload assembly (`get_assessment_telemetry_summary`), and lifecycle state control delegation (`pause`, `resume`, `cancel`, `retry`), keeping `AssessmentService` focused strictly on assessment creation and dispatch logic.
3. **Frontend API Abstraction Service**: `frontend/services/scans.service.ts` encapsulates all REST API calls and WebSocket connections outside React components.
4. **Visual Scan Activity Execution Timeline**: `ScanActivityTimeline` component renders step execution progression milestones (`QUEUED`, `PROBING`, `CRAWLING`, `ASSESSING`, `VERIFYING`, `COMPLETED`), target verification events, plugin executions, and finding discovery events.

---

## 🔍 13. Vulnerability Investigation Workspace & AI Remediation Architecture (Phase 7.5)

Phase 7.5 introduces a dedicated analyst vulnerability investigation workspace (`/vulnerabilities/[id]`), synthesizing raw security findings, multi-modal evidence artifacts, attack paths, and AI fix guidance:

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                         Security Analyst Investigation                      │
  │                  (/vulnerabilities/[id] Intelligence Route)                 │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                  Frontend Vulnerabilities Service Abstraction               │
  │                 (frontend/services/vulnerabilities.service.ts)              │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │ REST API
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                 FastAPI Vulnerability Intelligence Router                   │
  │                      (/api/v1/vulnerabilities/*)                            │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                     FindingIntelligenceService Aggregator                   │
  │            (app/application/finding/finding_intelligence_service.py)        │
  └──────────┬───────────────────┬───────────────────┬───────────────────┬──────┘
             │                   │                   │                   │
             ▼                   ▼                   ▼                   ▼
  ┌────────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
  │AssessmentRepository││EvidenceRepository││AIAttackPathRepo  ││AIRemediationRepo │
  │(SecurityFinding)   ││(EvidenceArtifact)││(AIAttackPath)    ││(AIRemediation)   │
  └────────────────────┘└──────────────────┘└──────────────────┘└──────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Table Duplication Safeguard**: Operates as a read-only intelligence aggregator on top of 9 existing ORM models (`security_findings`, `evidence_artifacts`, `assessment_jobs`, `finding_triage_history`, `ai_finding_explanations`, `ai_attack_paths`, `ai_remediation_plans`). Introduces zero redundant tables or secondary risk engines.
2. **Multi-Modal Evidence Normalization**: Maps raw storage evidence artifacts (`HTTP_EXCHANGE`, `SCREENSHOT`, `DOM_SNAPSHOT`, `PLUGIN_OUTPUT`, `TRACE_LOG`) into human-readable UI labels with SHA-256 non-repudiation integrity verification.
3. **On-Demand Advisory AI Fix Generation**: `POST /api/v1/vulnerabilities/{id}/remediation-ai` invokes `AIRemediationService.generate_remediation_plan()` (Phase 5.4) under a strict non-executable human approval policy.
4. **Tenant Isolation & RBAC Boundaries**: Every query enforces `organization_id = current_user.organization_id`. Endpoints require permissions (`findings:read`, `findings:ai_attack_path`, `findings:ai_remediate`).

---

## ⚙️ 14. Enterprise Administration Workspace & Control Plane Architecture (Phase 7.6)

Phase 7.6 introduces the centralized administrative control plane workspace (`/settings/*`) for team member governance, RBAC role boundary visualization, machine-to-machine API key management, and security posture overview:

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                    Enterprise Administration Control Plane                  │
  │    (/settings/organization, /settings/users, /settings/roles,              │
  │     /settings/api-keys, /settings/security)                                 │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                   Frontend Admin Service Abstraction                        │
  │                     (frontend/services/admin.service.ts)                    │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │ REST API (/api/v1/admin/*)
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                     FastAPI Administrative REST Router                      │
  │                     (app/api/v1/routers/admin.py)                           │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                     AdminService Aggregator Service                         │
  │                  (app/application/admin/admin_service.py)                  │
  └──────────┬───────────────────┬───────────────────┬───────────────────┬──────┘
             │                   │                   │                   │
             ▼                   ▼                   ▼                   ▼
  ┌────────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
  │OrganizationService ││   UserService    ││  APIKeyService   ││ AuditLogService  │
  │(OrganizationModel) ││   (UserModel)    ││  (APIKeyModel)   ││ (AuditLogModel)  │
  └────────────────────┘└──────────────────┘└──────────────────┘└──────────────────┘
```

### Key Architectural Safeguards:
1. **100% Schema & Model Reuse**: Reuses existing `OrganizationModel`, `UserModel`, `APIKeyModel`, `AuditLogModel`, `PERMISSION_MAP`, and `Role` enum across Era 2 foundations. Zero new database tables or permission engines created.
2. **Sole Owner & Self-Deactivation Protections**: `update_user_role` and `deactivate_user` enforce active owner count checks (`count_owners_in_org <= 1`) and self-deactivation guards (`target_user_id != current_user.id`), preventing accidental lockout of organization control.
3. **Raw API Key Show-Once Governance**: Machine-to-machine API keys created via `POST /api/v1/admin/api-keys` return raw secret token (`vn_live_...`) ONCE in response DTO. Only `key_prefix` and SHA-256 `key_hash` are stored in database.
4. **Detailed API Key Audit Logging**: Audit log events for `api_key.created` and `api_key.revoked` record `actor_user_id`, `organization_id`, `resource_id` (api_key_id), `timestamp`, `action`, and scope metadata.
5. **Canonical Permission Consistency**: Endpoints enforce permissions (`organization:read`, `organization:update`, `users:read`, `users:invite`, `users:update_role`, `users:remove`, `api_keys:read`, `api_keys:create`, `api_keys:revoke`) matching `PERMISSION_MAP` across backend, `SECURITY.md`, and `API_SPEC.md`.

---

## 📊 15. PDF & HTML Executive Security Report Generator Architecture (Phase 8.1)

Phase 8.1 introduces the enterprise executive security report generation engine capable of assembling CISO-level security posture reports, time-series risk velocity analytics, vulnerability breakdowns, and rendering HTML and PDF document exports:

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                   Next.js 14 CISO Executive Reporting Workspace              │
  │                          (/reports, /reports/[id])                          │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                  ReportsService Frontend API Abstraction                    │
  │                     (frontend/services/reports.service.ts)                  │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │ REST API (/api/v1/reports/*)
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                     FastAPI Executive Reporting REST Router                 │
  │                     (app/api/v1/routers/reports.py)                         │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                   ExecutiveSecurityReportService Aggregator                 │
  │                 (app/application/reporting/report_service.py)               │
  └──────┬────────────────────┬────────────────────┬────────────────────┬───────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
  ┌──────────────┐    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Dashboard   │    │  Executive   │     │HTMLRenderer  │     │ PDFGenerator │
  │  Analytics   │    │  Analytics   │     │ Service      │     │ Service      │
  │  Service     │    │  Service     │     │ (Jinja2)     │     │ (WeasyPrint) │
  └──────────────┘    └──────────────┘     └──────────────┘     └──────────────┘
```

### Key Architectural Safeguards:
1. **Dual Template & Rendering Engine**: `HTMLRendererService` uses Jinja2 `FileSystemLoader` with `templates/executive_report.html` and print-ready A4 stylesheet (`templates/style.css`). `PDFGeneratorService` converts HTML to PDF binary streams via WeasyPrint with graceful fallback to a compliant binary PDF/1.4 wrapper if system libraries (`libgobject`, `libcairo`) are missing.
2. **Zero Database Table Duplication**: Aggregates posture metrics, time-series risk trends, attack surface environment coverage, vulnerability severity breakdowns, top findings, and threat advisories from existing `DashboardAnalyticsService`, `ExecutiveAnalyticsService`, and `ThreatAdvisoryService`. Zero new database tables created for report generation.
3. **Tenant Boundary Isolation & Audit Trail Non-Repudiation**: Enforces strict tenant boundary isolation (`organization_id = current_user.organization_id`). Every report payload generation and PDF download records immutable security audit events (`report.generated`, `report.downloaded`) via `AuditLogService`.
4. **Canonical RBAC Permissions**: Endpoint handlers enforce canonical permissions (`reports:create`, `reports:read`, `reports:export`) matching `PERMISSION_MAP`.
5. **Developer Technical Remediation Export Architecture (Phase 8.2)**:
   - **Streaming & Memory-Efficient Batch Cursors**: Bulk export handlers (`export_json_stream`, `export_csv_stream`, `export_markdown_stream`) query PostgreSQL using offset/limit batch cursors (`_stream_findings`, batch size 50) and stream output chunks directly into FastAPI `StreamingResponse` objects. This prevents memory bloat and worker OOM crashes when processing large enterprise finding datasets.
   - **On-Demand Generation & Zero Archival Overhead**: Introduces zero report archival tables, zero export history schemas, and zero object storage dependencies. All exports are dynamically compiled from authoritative PostgreSQL tables (`security_findings`, `evidence_artifacts`, `ai_remediation_plans`, `ai_finding_explanations`, `ai_attack_paths`, `assessment_jobs`).
   - **Multi-Format Technical Packages**: Formats finding records into machine-readable JSON arrays, spreadsheet-ready CSV tables, and developer ticket-ready Markdown documentation with GitHub/Jira formatted sections. Single vulnerability exports compile intelligence, multi-modal evidence dumps, attack chain graphs, and AI fix recommendations into ticket packages with automated token/credential masking (`sanitize_sensitive_data`).
   - **RBAC & Immutable Audit Log Integration**: Enforces `reports:export` permission (`Role.SECURITY_ANALYST` level 20+) and dispatches immutable audit log events (`report.exported`, `vulnerability.exported`) tracking format, resource ID, actor ID, finding count, and timestamp via `AuditLogService`.

---

## 📊 17. Compliance Intelligence Layer & Framework Mapping Architecture (Phase 8.3)

Phase 8.3 introduces a zero-duplication compliance intelligence layer that dynamically evaluates tenant security findings against enterprise compliance standards:

```text
                               ┌──────────────────────────────────────────────┐
                               │       Next.js 14 Compliance Workspace        │
                               │  (/compliance, /compliance/[framework], DTOs)│
                               └──────────────────────┬───────────────────────┘
                                                      │ GET /api/v1/compliance/*
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │           FastAPI Compliance Router          │
                               │  (compliance:read, compliance:export RBAC)   │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │          ComplianceMappingService            │
                               │  (Batch Cursors & Audit Event Dispatcher)    │
                               └──────────┬────────────────────────┬──────────┘
                                          │                        │
                                          ▼                        ▼
                               ┌──────────────────────┐ ┌─────────────────────┐
                               │   FrameworkMapper    │ │   AuditLogService   │
                               │(Active Finding Filter│ │(compliance.viewed,  │
                               │ & Score Calculation) │ │ compliance.exported)│
                               └──────────┬───────────┘ └─────────────────────┘
                                          │
                                          ▼
                       ┌──────────────────────────────────────┐
                       │  Static Framework Mapping Modules    │
                       │ ┌──────────────────────────────────┐ │
                       │ │ OWASP Top 10 (OWASP Top 10 2021) │ │
                       │ ├──────────────────────────────────┤ │
                       │ │ OWASP ASVS (OWASP ASVS 4.0.3)     │ │
                       │ ├──────────────────────────────────┤ │
                       │ │ PCI-DSS (PCI DSS 4.0)            │ │
                       │ ├──────────────────────────────────┤ │
                       │ │ ISO 27001 (ISO 27001:2022)        │ │
                       │ └──────────────────────────────────┘ │
                       └──────────────────────────────────────┘
```

### Key Architectural Controls:
1. **Explicit Version Metadata**: Framework mapping definitions maintain authoritative version strings: `OWASP Top 10 2021`, `OWASP ASVS 4.0.3`, `PCI DSS 4.0`, and `ISO 27001:2022`.
2. **Zero Database Table Duplication**: Reuses existing `security_findings`, `evidence_artifacts`, and `assessment_jobs` tables. Compliance posture scores and control statuses are evaluated on demand without introducing compliance mapping database tables or document archival storage.
3. **Active Open Finding Filter**: `FrameworkMapper` strictly filters for active open findings (`OPEN`, `CONFIRMED`, `NEW`, `UNREAD`, `TRIAGED`, `IN_REMEDIATION`). Resolved, verified fixed, and false-positive findings do not impact compliance scores.
4. **End-to-End Control-to-Evidence Traceability**: Every evaluated control maintains complete traceability: `Framework Control -> Vulnerability Finding -> Evidence Artifact Checksum -> Target Asset -> Remediation Guidance` (`ComplianceFindingMappingDTO`).
5. **Granular RBAC & Audit Trail**: REST endpoints enforce `compliance:read` (`Role.VIEWER` level 10+) for overview and controls retrieval, and `compliance:export` (`Role.SECURITY_ANALYST` level 20+) for report downloads. Dispatches immutable audit log events (`compliance.viewed`, `compliance.exported`) via `AuditLogService`.

---

## 📈 16. Enterprise Production Reliability & Observability Architecture (Planned Era 11)

Era 11 introduces the production reliability, observability, disaster recovery, and incident response architecture designed for high-availability enterprise SaaS operation:

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                    Vulnova Application Layer & Web Services                 │
  │            (FastAPI Gateway, Celery Workers, Next.js 14 Frontend)           │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                 Monitoring & Observability Telemetry Layer                  │
  │  (Prometheus Exporter /metrics, Structlog JSON Formatter, Sentry SDK Hook)  │
  └──────────┬───────────────────────────┬───────────────────────────┬──────────┘
             │ Metrics                   │ JSON Logs                 │ Exception Traces
             ▼                           ▼                           ▼
  ┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
  │Prometheus TimeSeries│      │ Loki / ELK Central │      │ Sentry Error       │
  │     Database       │      │   Log Aggregator   │      │ Tracking Platform  │
  └──────────┬─────────┘      └──────────┬─────────┘      └──────────┬─────────┘
             │                           │                           │
             └───────────────────────────┼───────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │             Grafana Unified Operational Dashboards & Alert Rules            │
  │     (Latency SLAs, Queue Depth, DB Pool Exhaustion, SEV-1 Escalations)     │
  └─────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Safeguards:
1. **Multi-Layer Observability & Telemetry**:
   - Application Layer emits structured JSON logs (`structlog`), Prometheus time-series metrics (`/metrics`), and Sentry exception stack traces without impacting worker thread throughput.
   - Health probes (`/health`, `/health/liveness`, `/health/readiness`) monitor database connection pool availability, Redis Pub/Sub connectivity, and Celery worker queue health.
2. **Database Reliability & Recovery Layer**:
   - **Continuous WAL Archiving**: PostgreSQL Write-Ahead Logs (WAL) streamed continuously to encrypted object storage for Point-in-Time Recovery (PITR) up to any specific second within 30 days.
   - **Automated Restore Verification**: Daily automated restore dry-runs in an isolated sandbox environment validate snapshot integrity and measure restore speed.
3. **Infrastructure Failover & Zero-Downtime Rollbacks**:
   - Health monitors detect node failures and trigger multi-region database failover within Recovery Time Objective (RTO < 1 hour) and Recovery Point Objective (RPO < 5 minutes).
   - Single-command zero-downtime deployment rollback strategies (`docker compose rollback` / Helm rollback) guarantee instant mitigation if problematic releases pass staging.
4. **Security Incident Escalation & Response**:
   - Automated PagerDuty/Slack escalation rules route `SEV-1 Critical` and `SEV-2 High` incidents directly to on-call security engineers.
   - Forensic audit investigation workflows leverage immutable `AuditLogService` records with actor user ID, client IP, timestamp, and target resource context.

---

## 🔗 18. Enterprise Integration & External Workflow Architecture (Phase 9.1)

Phase 9.1 establishes an enterprise integration engine enabling bi-directional vulnerability synchronization between Vulnova and external issue trackers (Atlassian Jira Cloud and GitHub Issues):

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                 Next.js Integration Workspace & Control Plane               │
  │                     (/integrations, /integrations/settings)                 │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │ HTTPS / JSON
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                   FastAPI Enterprise Integrations Router                    │
  │                      (/api/v1/integrations/* endpoints)                     │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                           IntegrationService                                │
  │    (Credential Encryption, External Issue Dispatcher, Lifecycle Sync)       │
  └──────────┬───────────────────────────┬───────────────────────────┬──────────┘
             │                           │                           │
             ▼                           ▼                           ▼
  ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
  │      JiraClient      │    │     GitHubClient     │    │SecretEncryptionService│
  │ (Atlassian REST API) │    │  (GitHub REST API)   │    │(AES-256-GCM / Fernet)│
  └──────────┬───────────┘    └──────────┬───────────┘    └──────────────────────┘
             │                           │
             ▼                           ▼
  ┌──────────────────────┐    ┌──────────────────────┐
  │  Jira Cloud Project  │    │  GitHub Repository   │
  │   (/rest/api/3/issue)│    │  (/repos/owner/repo) │
  └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication & Plaintext Secret Protection**:
   - Provider credentials (API tokens and PATs) are encrypted at rest using AES-256-GCM / Fernet via `SecretEncryptionService`.
   - Plaintext credentials are **NEVER** stored in database tables, logged in application telemetry, or returned in API responses.
   - Created issue references are stored directly within existing finding metadata (`evidence_json`). No unnecessary database tables (`integration_configs`, `ticket_history`) are created.
2. **Controlled State Transition Layer**:
   - External status updates pass through controlled state transition mappers (`ControlledJiraStatusMapper`, `ControlledGitHubStatusMapper`) before modifying internal Vulnova finding states.
   - External state changes (`DONE`/`CLOSED` -> `RESOLVED`, `IN_PROGRESS` -> `IN_REMEDIATION`) pass through strict validation rules, preventing external tools from unvalidated direct mutation of internal security posture.
3. **Tenant Isolation & RBAC Protection**:
   - Every integration call enforces strict tenant boundaries (`organization_id = current_user.organization_id`).
   - Granular permissions: `integrations:read` (VIEWER+), `integrations:create`/`integrations:update` (SECURITY_ANALYST+), `integrations:manage` (ADMIN+).
4. **Auditability & Non-Repudiation**:
   - Dispatches immutable security audit log events (`integration.configuration_updated`, `integration.issue_created`, `integration.issue_synced`) recording actor user ID, provider, external ticket ID, and timestamp.

---

## 🔔 19. Real-Time Notification & Alert Webhook Architecture (Phase 9.2)

Phase 9.2 introduces an enterprise real-time security alert dispatching framework supporting Slack Workspaces and Microsoft Teams Channels:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Security Event Trigger / Assessment Pipeline                │
│  (Vulnerability Discovered, Scan Completed, Compliance Dropped, Ticket Sync)│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Async Non-Blocking Dispatch
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            NotificationService                              │
│       (Tenant Rule Evaluation, Event Routing, Audit Event Dispatcher)       │
└──────────────────┬──────────────────────────────────────┬───────────────────┘
                   │                                      │
                   ▼                                      ▼
┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│        SlackWebhookProvider        │  │        TeamsWebhookProvider        │
│   (Slack Block Kit JSON Messages)  │  │  (Microsoft Teams Adaptive Cards)  │
└──────────────────┬─────────────────┘  └──────────────────┬─────────────────┘
                   │                                      │
                   ▼ HTTPS POST                           ▼ HTTPS POST
┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│   Slack Incoming Webhook Endpoint  │  │  Teams Office 365 Connector Webhook│
└────────────────────────────────────┘  └────────────────────────────────────┘
```

### Key Architectural Safeguards:
1. **Resilient Asynchronous Delivery**:
   - Webhook notifications run asynchronously without blocking core vulnerability processing, scan execution, or compliance evaluation.
   - HTTP errors, timeouts, or 500 status codes from external webhooks are caught and logged without raising unhandled exceptions or breaking security workflows.
2. **Secret Token Encryption & URL Masking**:
2. **Zero Database Table Duplication**: Aggregates posture metrics, time-series risk trends, attack surface environment coverage, vulnerability severity breakdowns, top findings, and threat advisories from existing `DashboardAnalyticsService`, `ExecutiveAnalyticsService`, and `ThreatAdvisoryService`. Zero new database tables created for report generation.
3. **Tenant Boundary Isolation & Audit Trail Non-Repudiation**: Enforces strict tenant boundary isolation (`organization_id = current_user.organization_id`). Every report payload generation and PDF download records immutable security audit events (`report.generated`, `report.downloaded`) via `AuditLogService`.
4. **Canonical RBAC Permissions**: Endpoint handlers enforce canonical permissions (`reports:create`, `reports:read`, `reports:export`) matching `PERMISSION_MAP`.
5. **Developer Technical Remediation Export Architecture (Phase 8.2)**:
   - **Streaming & Memory-Efficient Batch Cursors**: Bulk export handlers (`export_json_stream`, `export_csv_stream`, `export_markdown_stream`) query PostgreSQL using offset/limit batch cursors (`_stream_findings`, batch size 50) and stream output chunks directly into FastAPI `StreamingResponse` objects. This prevents memory bloat and worker OOM crashes when processing large enterprise finding datasets.
   - **On-Demand Generation & Zero Archival Overhead**: Introduces zero report archival tables, zero export history schemas, and zero object storage dependencies. All exports are dynamically compiled from authoritative PostgreSQL tables (`security_findings`, `evidence_artifacts`, `ai_remediation_plans`, `ai_finding_explanations`, `ai_attack_paths`, `assessment_jobs`).
   - **Multi-Format Technical Packages**: Formats finding records into machine-readable JSON arrays, spreadsheet-ready CSV tables, and developer ticket-ready Markdown documentation with GitHub/Jira formatted sections. Single vulnerability exports compile intelligence, multi-modal evidence dumps, attack chain graphs, and AI fix recommendations into ticket packages with automated token/credential masking (`sanitize_sensitive_data`).
   - **RBAC & Immutable Audit Log Integration**: Enforces `reports:export` permission (`Role.SECURITY_ANALYST` level 20+) and dispatches immutable audit log events (`report.exported`, `vulnerability.exported`) tracking format, resource ID, actor ID, finding count, and timestamp via `AuditLogService`.

---

## 📊 17. Compliance Intelligence Layer & Framework Mapping Architecture (Phase 8.3)

Phase 8.3 introduces a zero-duplication compliance intelligence layer that dynamically evaluates tenant security findings against enterprise compliance standards:

```text
                               ┌──────────────────────────────────────────────┐
                               │       Next.js 14 Compliance Workspace        │
                               │  (/compliance, /compliance/[framework], DTOs)│
                               └──────────────────────┬───────────────────────┘
                                                      │ GET /api/v1/compliance/*
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │           FastAPI Compliance Router          │
                               │  (compliance:read, compliance:export RBAC)   │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │          ComplianceMappingService            │
                               │  (Batch Cursors & Audit Event Dispatcher)    │
                               └──────────┬────────────────────────┬──────────┘
                                          │                        │
                                          ▼                        ▼
                               ┌──────────────────────┐ ┌─────────────────────┐
                               │   FrameworkMapper    │ │   AuditLogService   │
                               │(Active Finding Filter│ │(compliance.viewed,  │
                               │ & Score Calculation) │ │ compliance.exported)│
                               └──────────┬───────────┘ └─────────────────────┘
                                          │
                                          ▼
                       ┌──────────────────────────────────────┐
                       │  Static Framework Mapping Modules    │
                       │ ┌──────────────────────────────────┐ │
                       │ │ OWASP Top 10 (OWASP Top 10 2021) │ │
                       │ ├──────────────────────────────────┤ │
                       │ │ OWASP ASVS (OWASP ASVS 4.0.3)     │ │
                       │ ├──────────────────────────────────┤ │
                       │ │ PCI-DSS (PCI DSS 4.0)            │ │
                       │ ├──────────────────────────────────┤ │
                       │ │ ISO 27001 (ISO 27001:2022)        │ │
                       │ └──────────────────────────────────┘ │
                       └──────────────────────────────────────┘
```

### Key Architectural Controls:
1. **Explicit Version Metadata**: Framework mapping definitions maintain authoritative version strings: `OWASP Top 10 2021`, `OWASP ASVS 4.0.3`, `PCI DSS 4.0`, and `ISO 27001:2022`.
2. **Zero Database Table Duplication**: Reuses existing `security_findings`, `evidence_artifacts`, and `assessment_jobs` tables. Compliance posture scores and control statuses are evaluated on demand without introducing compliance mapping database tables or document archival storage.
3. **Active Open Finding Filter**: `FrameworkMapper` strictly filters for active open findings (`OPEN`, `CONFIRMED`, `NEW`, `UNREAD`, `TRIAGED`, `IN_REMEDIATION`). Resolved, verified fixed, and false-positive findings do not impact compliance scores.
4. **End-to-End Control-to-Evidence Traceability**: Every evaluated control maintains complete traceability: `Framework Control -> Vulnerability Finding -> Evidence Artifact Checksum -> Target Asset -> Remediation Guidance` (`ComplianceFindingMappingDTO`).
5. **Granular RBAC & Audit Trail**: REST endpoints enforce `compliance:read` (`Role.VIEWER` level 10+) for overview and controls retrieval, and `compliance:export` (`Role.SECURITY_ANALYST` level 20+) for report downloads. Dispatches immutable audit log events (`compliance.viewed`, `compliance.exported`) via `AuditLogService`.

---

## 📈 16. Enterprise Production Reliability & Observability Architecture (Planned Era 11)

Era 11 introduces the production reliability, observability, disaster recovery, and incident response architecture designed for high-availability enterprise SaaS operation:

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                    Vulnova Application Layer & Web Services                 │
  │            (FastAPI Gateway, Celery Workers, Next.js 14 Frontend)           │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                 Monitoring & Observability Telemetry Layer                  │
  │  (Prometheus Exporter /metrics, Structlog JSON Formatter, Sentry SDK Hook)  │
  └──────────┬───────────────────────────┬───────────────────────────┬──────────┘
             │ Metrics                   │ JSON Logs                 │ Exception Traces
             ▼                           ▼                           ▼
  ┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
  │Prometheus TimeSeries│      │ Loki / ELK Central │      │ Sentry Error       │
  │     Database       │      │   Log Aggregator   │      │ Tracking Platform  │
  └──────────┬─────────┘      └──────────┬─────────┘      └──────────┬─────────┘
             │                           │                           │
             └───────────────────────────┼───────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │             Grafana Unified Operational Dashboards & Alert Rules            │
  │     (Latency SLAs, Queue Depth, DB Pool Exhaustion, SEV-1 Escalations)     │
  └─────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Safeguards:
1. **Multi-Layer Observability & Telemetry**:
   - Application Layer emits structured JSON logs (`structlog`), Prometheus time-series metrics (`/metrics`), and Sentry exception stack traces without impacting worker thread throughput.
   - Health probes (`/health`, `/health/liveness`, `/health/readiness`) monitor database connection pool availability, Redis Pub/Sub connectivity, and Celery worker queue health.
2. **Database Reliability & Recovery Layer**:
   - **Continuous WAL Archiving**: PostgreSQL Write-Ahead Logs (WAL) streamed continuously to encrypted object storage for Point-in-Time Recovery (PITR) up to any specific second within 30 days.
   - **Automated Restore Verification**: Daily automated restore dry-runs in an isolated sandbox environment validate snapshot integrity and measure restore speed.
3. **Infrastructure Failover & Zero-Downtime Rollbacks**:
   - Health monitors detect node failures and trigger multi-region database failover within Recovery Time Objective (RTO < 1 hour) and Recovery Point Objective (RPO < 5 minutes).
   - Single-command zero-downtime deployment rollback strategies (`docker compose rollback` / Helm rollback) guarantee instant mitigation if problematic releases pass staging.
4. **Security Incident Escalation & Response**:
   - Automated PagerDuty/Slack escalation rules route `SEV-1 Critical` and `SEV-2 High` incidents directly to on-call security engineers.
   - Forensic audit investigation workflows leverage immutable `AuditLogService` records with actor user ID, client IP, timestamp, and target resource context.

---

## 🔗 18. Enterprise Integration & External Workflow Architecture (Phase 9.1)

Phase 9.1 establishes an enterprise integration engine enabling bi-directional vulnerability synchronization between Vulnova and external issue trackers (Atlassian Jira Cloud and GitHub Issues):

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                 Next.js Integration Workspace & Control Plane               │
  │                     (/integrations, /integrations/settings)                 │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │ HTTPS / JSON
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                   FastAPI Enterprise Integrations Router                    │
  │                      (/api/v1/integrations/* endpoints)                     │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                           IntegrationService                                │
  │    (Credential Encryption, External Issue Dispatcher, Lifecycle Sync)       │
  └──────────┬───────────────────────────┬───────────────────────────┬──────────┘
             │                           │                           │
             ▼                           ▼                           ▼
  ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
  │      JiraClient      │    │     GitHubClient     │    │SecretEncryptionService│
  │ (Atlassian REST API) │    │  (GitHub REST API)   │    │(AES-256-GCM / Fernet)│
  └──────────┬───────────┘    └──────────┬───────────┘    └──────────────────────┘
             │                           │
             ▼                           ▼
  ┌──────────────────────┐    ┌──────────────────────┐
  │  Jira Cloud Project  │    │  GitHub Repository   │
  │   (/rest/api/3/issue)│    │  (/repos/owner/repo) │
  └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication & Plaintext Secret Protection**:
   - Provider credentials (API tokens and PATs) are encrypted at rest using AES-256-GCM / Fernet via `SecretEncryptionService`.
   - Plaintext credentials are **NEVER** stored in database tables, logged in application telemetry, or returned in API responses.
   - Created issue references are stored directly within existing finding metadata (`evidence_json`). No unnecessary database tables (`integration_configs`, `ticket_history`) are created.
2. **Controlled State Transition Layer**:
   - External status updates pass through controlled state transition mappers (`ControlledJiraStatusMapper`, `ControlledGitHubStatusMapper`) before modifying internal Vulnova finding states.
   - External state changes (`DONE`/`CLOSED` -> `RESOLVED`, `IN_PROGRESS` -> `IN_REMEDIATION`) pass through strict validation rules, preventing external tools from unvalidated direct mutation of internal security posture.
3. **Tenant Isolation & RBAC Protection**:
   - Every integration call enforces strict tenant boundaries (`organization_id = current_user.organization_id`).
   - Granular permissions: `integrations:read` (VIEWER+), `integrations:create`/`integrations:update` (SECURITY_ANALYST+), `integrations:manage` (ADMIN+).
4. **Auditability & Non-Repudiation**:
   - Dispatches immutable security audit log events (`integration.configuration_updated`, `integration.issue_created`, `integration.issue_synced`) recording actor user ID, provider, external ticket ID, and timestamp.

---

## 🔔 19. Real-Time Notification & Alert Webhook Architecture (Phase 9.2)

Phase 9.2 introduces an enterprise real-time security alert dispatching framework supporting Slack Workspaces and Microsoft Teams Channels:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Security Event Trigger / Assessment Pipeline                │
│  (Vulnerability Discovered, Scan Completed, Compliance Dropped, Ticket Sync)│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Async Non-Blocking Dispatch
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            NotificationService                              │
│       (Tenant Rule Evaluation, Event Routing, Audit Event Dispatcher)       │
└──────────────────┬──────────────────────────────────────┬───────────────────┘
                   │                                      │
                   ▼                                      ▼
┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│        SlackWebhookProvider        │  │        TeamsWebhookProvider        │
│   (Slack Block Kit JSON Messages)  │  │  (Microsoft Teams Adaptive Cards)  │
└──────────────────┬─────────────────┘  └──────────────────┬─────────────────┘
                   │                                      │
                   ▼ HTTPS POST                           ▼ HTTPS POST
┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│   Slack Incoming Webhook Endpoint  │  │  Teams Office 365 Connector Webhook│
└────────────────────────────────────┘  └────────────────────────────────────┘
```

### Key Architectural Safeguards:
1. **Resilient Asynchronous Delivery**:
   - Webhook notifications run asynchronously without blocking core vulnerability processing, scan execution, or compliance evaluation.
   - HTTP errors, timeouts, or 500 status codes from external webhooks are caught and logged without raising unhandled exceptions or breaking security workflows.
2. **Secret Token Encryption & URL Masking**:
   - Webhook URLs (which contain secret tokens) are encrypted at rest using AES-256-GCM / Fernet via `SecretEncryptionService`.
   - Webhook URLs returned in REST API payloads are masked (e.g. `https://hooks.slack.com/services/T00/B00/*****XXXX`), ensuring zero plaintext secret leaks.
3. **Tenant Isolation & Granular RBAC**:
   - Channel configuration and alert dispatching enforce `organization_id = current_user.organization_id`.
   - Permissions: `notifications:read` (VIEWER+), `notifications:create`/`notifications:update` (SECURITY_ANALYST+), `notifications:manage` (ADMIN+).
4. **Audit Visibility**:
   - Dispatches audit events (`notification.channel_created`, `notification.channel_updated`, `notification.channel_deleted`, `notification.sent`, `notification.failed`) recording delivery status and HTTP response codes.

---

## 20. CI/CD Pipeline Security Scanning & CLI Tool Architecture (Phase 9.3)

Vulnova provides an independent distributable Python CLI tool (`vulnova-cli`) and REST API module (`/api/v1/cli/*`) allowing engineering teams to automate security scans, monitor job progress, query vulnerability severity metrics, and evaluate build security gates directly in CI/CD pipelines.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Build / Runner Environment                           │
│       (GitHub Actions, GitLab CI/CD, Jenkins, Developer Workstation)       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ CLI Executable (`vulnova scan start`, etc.)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Vulnova Developer CLI (`cli/`)                         │
│     (Zero DB / Zero Frontend, Token Auth, --json Output, --quiet Mode)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (X-API-Key: vn_cli_...)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FastAPI CLI Router (`/api/v1/cli/*`)                   │
│        (Tenant Isolation, RBAC Guard, Audit Logging, Gate Verification)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│      CLIScanningService      │              │       AuditLogService        │
│ (Scan Trigger & Gate Check)  │              │ (cli.scan_started, failed)   │
└──────────────────────────────┘              └──────────────────────────────┘
```

### Key Architectural Safeguards:
1. **Independent Distributable Architecture**:
   - `cli/` module has zero dependency on frontend or backend internal code. Uses standard library HTTP clients communicating exclusively over authenticated REST APIs.
2. **Zero Plaintext Secret Leakage**:
   - Tokens use `vn_cli_` prefixes + SHA-256 digests (`APIKeyModel`). Raw tokens are shown once upon creation.
   - CLI logs never print API tokens, secrets, or sensitive vulnerability evidence.
3. **Machine-Readable Automation Modes**:
   - `--json`: Formats all CLI responses into structured JSON for build system parsers (`jq`).
   - `--quiet`: Suppresses human-targeted spinners/formatting for clean build log outputs.
4. **Standard Build Exit Codes**:
   - `0`: Security scan & build gate PASSED cleanly.
   - `1`: Security gate FAILED (vulnerabilities exceeded configured thresholds).
   - `2`: Network, authentication, or CLI execution error.

---

## 21. OWASP Top 10 (2021) Security Validation Suite Architecture (Phase 10.1)

Vulnova provides an automated, in-memory Security Validation Engine (`OWASPValidationRunnerService`) that continuously evaluates tenant application posture and active platform security controls against all 10 OWASP Top 10 (2021) categories (A01 Broken Access Control through A10 SSRF).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Next.js 14 OWASP Validation Workspace                       │
│      (/validation/owasp, OWASPPassRateCard, OWASPCategoryGrid, Modal)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               FastAPI OWASP Validation Router (/api/v1/validation/*)        │
│       (validation:read, validation:execute RBAC Guards & Audit Log Hook)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       OWASPValidationRunnerService                          │
│     (Executes Category Assertion Checks A01 - A10 against Tenant Posture)   │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  AssessmentService   │    │FrameworkMapper (OWASP│    │   AuditLogService    │
│(Findings & Evidence) │    │   Top 10 2021 Rules) │    │(validation.completed)│
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Era 8 compliance architecture: introduces zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run -> Evaluate Category Assertions -> Log Audit Event -> Return Response`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation run generates a unique runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.owasp_suite_started`, `validation.owasp_suite_completed`) for correlation across SIEM systems.
3. **Explainable Failure Diagnostics**:
   - Every category result returns explicit diagnostics: `failure_reason`, target `affected_subsystem` (e.g. `SecretEncryptionService`, `SSRFValidator`, `RBACPolicy`), and actionable `remediation_guidance`.
4. **Deep SSRF Firewall Validation**:
   - Direct integration with `is_safe_target_url` verifying private IP range blocking (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`, AWS IMDS `169.254.169.254`) and DNS rebinding protections.
5. **Tenant Isolation & Granular RBAC**:
   - All validation runs enforce `organization_id = current_user.organization_id`.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 22. OWASP API Security Top 10 (2023) Validation Suite Architecture (Phase 10.2)

Vulnova provides an automated API security assertion engine (`APISecurityValidationRunnerService`) that continuously evaluates tenant REST API routes and platform security controls against all 10 OWASP API Security Top 10 (2023) categories (API1 BOLA through API10 Unsafe Consumption of APIs).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Next.js 14 API Security Workspace                           │
│     (/validation/api-security, PassRateCard, CategoryGrid, DetailsModal)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             FastAPI API Security Validation Router (/api/v1/validation/api-security/*)
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   APISecurityValidationRunnerService                        │
│    (Executes Category Checks API1 - API10 against Vulnova REST Layer)       │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  RBAC & Auth Engine  │    │  SSRF & Rate Limiter │    │   AuditLogService    │
│(JWT, API Key, Tenant)│    │(is_safe_target_url)  │    │(validation.api_comp) │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run -> Execute API Category Assertions -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.api_security_suite_started`, `validation.api_security_suite_completed`).
3. **Explainable Failure Diagnostics & Endpoint Mapping**:
   - Every API category result returns explicit diagnostic feedback: `failure_reason`, target `affected_endpoint` (e.g. `/api/v1/vulnerabilities/{id}`), `affected_subsystem` (e.g. `OrganizationIsolation`, `RateLimiter`), and actionable `remediation_guidance`.
4. **Deep BOLA & Security Control Verification**:
   - Verifies BOLA tenant boundaries (`organization_id`), JWT expiration enforcement, API key prefixes (`vn_live_`, `vn_cli_`), rate limiting (`RateLimiter`), CORS/headers, and third-party payload sanitization.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 23. Security Configuration & Infrastructure Validation Suite Architecture (Phase 10.3)

Vulnova provides an automated infrastructure security assertion engine (`InfrastructureSecurityValidationRunnerService`) that continuously evaluates tenant deployment posture, container security, supply chain lockfiles, CI/CD pipelines, database security, logging, RBAC access controls, network SSRF firewalls, cloud metadata, and operational security readiness across all 10 Infrastructure Security categories (INFRA1 through INFRA10).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│               Next.js 14 Infrastructure Security Workspace                   │
│   (/validation/infrastructure, PassRateCard, CategoryGrid, DetailsModal)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│       FastAPI Infrastructure Validation Router (/api/v1/validation/infrastructure/*)
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 InfrastructureSecurityValidationRunnerService               │
│  (Executes Category Checks INFRA1 - INFRA10 against Infrastructure Controls)│
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  SSRF & Rate Limiter │    │ Vuln Intelligence &  │    │   AuditLogService    │
│(is_safe_target_url)  │    │   CI/CD Gate Engine  │    │(infra_suite_completed)│
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1, Phase 10.2 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run Validation -> Execute Infrastructure Assertions -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.infrastructure_suite_started`, `validation.infrastructure_suite_completed`).
3. **Explainable Failure Diagnostics & Component Mapping**:
   - Every infrastructure category result returns explicit diagnostic feedback: `failure_reason`, target `affected_component` (e.g. `Dockerfile & Docker Compose Runtime`, `Dependency Lockfiles`), and actionable `remediation_guidance`.
4. **Deep Container, Supply Chain & Cloud Control Verification**:
   - Verifies non-root container execution (`USER appuser`), supply chain lockfiles (`pyproject.toml`, `package-lock.json`), CI/CD pipeline gate enforcement, database connection encryption, `AuditLogService` & alert webhooks (Slack/Teams), and AWS IMDS cloud metadata blocking.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 24. Platform Penetration Testing & Exploit Verification Suite Architecture (Phase 10.4)

Vulnova provides an automated penetration test assertion engine (`PenTestValidationRunnerService`) that continuously evaluates active exploit scenarios simulating real-world attack vectors against platform API Gateway, Auth, Multi-Tenant Boundaries, Injections, SSRF Egress, Mass Assignment, Rate Limits, CORS, Error Leakages, and Webhooks across all 10 PenTest categories (PEN1 through PEN10).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│             Next.js 14 Penetration Testing Workspace                         │
│     (/validation/pentest, PassRateCard, CategoryGrid, DetailsModal)        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          FastAPI PenTest Router (/api/v1/validation/pentest/*)              │
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PenTestValidationRunnerService                           │
│  (Executes Exploit Verification Checks PEN1 - PEN10 against Core Services)   │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  SSRF & Auth Engine  │    │  RBAC & Rate Limiter │    │   AuditLogService    │
│(is_safe_target_url)  │    │ (require_permission) │    │(pentest_completed)   │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1, 10.2, 10.3 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run Penetration Suite -> Execute Exploit Assertions -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.pentest_suite_started`, `validation.pentest_suite_completed`).
3. **Explainable Failure Diagnostics & Target Mapping**:
   - Every PenTest category result returns explicit diagnostic feedback: `failure_reason`, target `affected_target` (e.g. `/api/v1/auth/login`, `/api/v1/vulnerabilities/{id}`), and actionable `remediation_guidance`.
4. **Deep Exploit Vector Verification**:
   - Verifies JWT signature tampering rejection, multi-tenant IDOR boundaries (`organization_id`), SQL/Command injection protection, AWS IMDS metadata exfiltration blocking (`is_safe_target_url`), rate limit DoS protection (`RateLimiter`), CORS origin whitelisting, production stack trace suppression, and webhook HMAC signature verification.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 25. Dependency Security Audit & SCA Enforcement Suite Architecture (Phase 10.5)

Vulnova provides an automated Software Composition Analysis (SCA) verification engine (`SCAValidationRunnerService`) that continuously evaluates third-party dependencies, lockfile integrity, outdated packages, CI/CD pipeline gates (`pip-audit`, `npm audit`), open-source license compliance, typosquatting, transitive tree depth, version pinning guards, DB drivers, and 30-day CVE remediation SLAs across all 10 SCA categories (SCA1 through SCA10).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│             Next.js 14 Dependency Security Workspace                         │
│       (/validation/sca, PassRateCard, CategoryGrid, DetailsModal)           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             FastAPI SCA Router (/api/v1/validation/sca/*)                   │
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SCAValidationRunnerService                             │
│   (Executes SCA & Supply Chain Checks SCA1 - SCA10 against Manifests)        │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│VulnerabilityIntelServ│    │   CI/CD Gate Engine  │    │   AuditLogService    │
│  (CVE Mapping Engine)│    │(pip-audit, npm audit)│    │ (sca_suite_completed)│
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1, 10.2, 10.3, 10.4 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run SCA Validation -> Execute SCA Category Assertions -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.sca_suite_started`, `validation.sca_suite_completed`).
3. **Explainable Failure Diagnostics & Package Mapping**:
   - Every SCA category result returns explicit diagnostic feedback: `failure_reason`, target `affected_package` (e.g. `PyPI & NPM Dependencies`, `Dependency Lockfiles`), and actionable `remediation_guidance`.
4. **Deep Supply Chain & License Verification**:
   - Verifies lockfile cryptographic hash pins (`pyproject.toml`, `package-lock.json`), CI/CD `pip-audit`/`npm audit` gate rules, open-source license compliance (MIT, Apache, GPL), typosquatting detection, strict version pinning syntax (`==`), and database driver security (asyncpg, psycopg).
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 26. Container Image Security Audit & Runtime Hardening Suite Architecture (Phase 10.6)

Vulnova provides an automated container security verification engine (`ContainerValidationRunnerService`) that continuously evaluates base image CVEs, unprivileged execution (`USER appuser`), minimal distroless footprints, Linux capability drops (`cap_drop: [ALL]`), `HEALTHCHECK` directives, secret exposure in layers, cgroup resource throttling, custom bridge network isolation (`vulnova-network`), Seccomp profiles, and SHA-256 image digest pinning across all 10 Container categories (CONTAINER1 through CONTAINER10).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│             Next.js 14 Container Security Workspace                          │
│     (/validation/container, PassRateCard, CategoryGrid, DetailsModal)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          FastAPI Container Router (/api/v1/validation/container/*)          │
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ContainerValidationRunnerService                            │
│  (Executes Hardening Checks CONTAINER1 - CONTAINER10 against Docker Profiles)│
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ Dockerfile & Compose │    │  Trivy Image Scanner │    │   AuditLogService    │
│  Hardening Verifier  │    │  (Container Audit)   │    │(container_completed) │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1 through 10.5 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run Container Validation -> Execute Hardening Assertions -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.container_suite_started`, `validation.container_suite_completed`).
3. **Explainable Failure Diagnostics & Container Mapping**:
   - Every Container category result returns explicit diagnostic feedback: `failure_reason`, target `affected_container` (e.g. `Dockerfile & Docker Compose Runtime User`, `Seccomp & AppArmor Security Profiles`), and actionable `remediation_guidance`.
4. **Deep Container Hardening & Controlled Warning Handling**:
   - Verifies unprivileged execution (`USER appuser`), Linux capability dropping (`cap_drop: [ALL]`), `no-new-privileges` flag, cgroup CPU/memory limits (`memory: 1g`), `/health` probes, and SHA-256 image digest pinning. Emits controlled `WARNING` status if binary scanner tools are absent.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 27. Secrets & Cryptographic Management Audit Suite Architecture (Phase 10.7)

Vulnova provides an automated secrets scanning & cryptographic verification engine (`SecretsValidationRunnerService`) that continuously evaluates Gitleaks hardcoded secret scanning (with controlled warning status when Gitleaks binary is uninstalled), AES-256-GCM authenticated envelope encryption (`CryptoService`), JWT signing key entropy (min 256-bit entropy), machine-to-machine SHA-256 API key hashing & constant-time `hmac.compare_digest` verification, webhook HMAC-SHA256 signatures (`X-Vulnova-Signature`), TLS 1.2/1.3 in-transit encryption standards, secret key rotation policies & versioning metadata (without inventing fake rotation history), Argon2id/bcrypt password hashing work factors, CI/CD pipeline secret masking, and 90-day secrets governance SLAs across all 10 Secrets categories (SECRET1 through SECRET10).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│            Next.js 14 Secrets & Cryptography Workspace                       │
│       (/validation/secrets, PassRateCard, CategoryGrid, DetailsModal)       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          FastAPI Secrets Router (/api/v1/validation/secrets/*)             │
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 SecretsValidationRunnerService                              │
│   (Executes Cryptographic Checks SECRET1 - SECRET10 against Platform)       │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│    CryptoService     │    │ Gitleaks & Auth Engine│    │   AuditLogService    │
│(AES-256-GCM Envelope)│    │(Secret Scan / Hashes)│    │ (secrets_completed)  │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1 through 10.6 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run Secrets Validation -> Execute Cryptographic Assertions -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.secrets_suite_started`, `validation.secrets_suite_completed`).
3. **Explainable Failure Diagnostics & Secrets Mapping**:
   - Every Secrets category result returns explicit diagnostic feedback: `failure_reason`, target `affected_secret` (e.g. `Database Sensitive Field Encryption (CryptoService AES-256-GCM)`, `JWT Auth Signing Key & Algorithm Enforcement`), and actionable `remediation_guidance`.
4. **Deep Cryptographic Verification & Controlled Warning Handling**:
   - Verifies AES-256-GCM envelope encryption, SHA-256 API key digests, HMAC-SHA256 webhook signatures, TLS 1.2/1.3 transport standards, and key rotation policy metadata. Emits controlled `WARNING` status if Gitleaks binary scanner is uninstalled and validates rotation policy without fake historical records.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 28. Threat Model Review & STRIDE Verification Suite Architecture (Phase 10.8)

Vulnova provides an automated threat model verification engine (`ThreatValidationRunnerService`) that continuously evaluates all 6 Microsoft STRIDE threat categories: Spoofing (JWT identity validation, API key SHA-256 hashing & `vn_live_` prefixes), Tampering (Pydantic payload schema sanitization, SQL ORM parameterization, webhook HMAC-SHA256 signatures), Repudiation (mandatory `AuditLogService` event tracking), Information Disclosure (multi-tenant `organization_id` boundary isolation, AES-256-GCM field encryption, production stack trace masking, SSRF egress blocking), Denial of Service (Redis-backed `RateLimiter`, Celery worker concurrency limits), and Elevation of Privilege (RBAC role hierarchy `VIEWER` < `ANALYST` < `ADMIN`, IDOR prevention, container sandbox `cap_drop: [ALL]` & `USER appuser`) across all 10 STRIDE categories (STRIDE1 through STRIDE10).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│          Next.js 14 Threat Model & STRIDE Security Workspace                │
│       (/validation/threat, PassRateCard, CategoryGrid, DetailsModal)        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          FastAPI Threat Router (/api/v1/validation/threat/*)                │
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ThreatValidationRunnerService                               │
│  (Executes STRIDE Matrix Assertions STRIDE1 - STRIDE10 against Platform)     │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ Platform Auth & RBAC │    │ Crypto & Egress Guard│    │   AuditLogService    │
│ (Tenant Isolation)   │    │(AES-256-GCM / SSRF)  │    │  (threat_completed)  │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1 through 10.7 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run Threat Validation -> Execute STRIDE Assertions -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.threat_suite_started`, `validation.threat_suite_completed`).
3. **Explainable Failure Diagnostics & Component Mapping**:
   - Every STRIDE category result returns explicit diagnostic feedback: `failure_reason`, target `affected_component` (e.g. `User JWT Bearer Authentication & Token Expiration`, `Multi-Tenant Database Queries (organization_id Scope)`), and actionable `remediation_guidance`.
4. **Deep Architectural STRIDE Verification**:
   - Verifies identity authentication guards, API key hashing, input sanitization, webhook signatures, audit event tracking, multi-tenant boundaries, field encryption & SSRF egress blocking, Redis rate limiting, RBAC permission hierarchy, and container sandbox capability dropping.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 29. Automated Security Regression Testing Framework Architecture (Phase 10.9)

Vulnova provides an automated security regression engine (`RegressionValidationRunnerService`) that continuously evaluates all 10 Security Regression categories: REGRESSION1 (OWASP Web Top 10), REGRESSION2 (OWASP API Security Top 10), REGRESSION3 (Security Config & Infrastructure), REGRESSION4 (Penetration Exploits), REGRESSION5 (SCA Supply Chain), REGRESSION6 (Container Hardening), REGRESSION7 (Secrets & Cryptography), REGRESSION8 (STRIDE Threat Model), REGRESSION9 (RBAC Hierarchy & Privilege Escalation), and REGRESSION10 (Audit Logging Non-Repudiation).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│          Next.js 14 Security Regression Testing Workspace                   │
│      (/validation/regression, PassRateCard, CategoryGrid, DetailsModal)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│       FastAPI Security Regression Router (/api/v1/validation/regression/*)  │
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               RegressionValidationRunnerService                             │
│ (Executes Assertion Matrix REGRESSION1 - REGRESSION10 against Platform)     │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  Security Findings   │    │ Auth & Policy Engine │    │   AuditLogService    │
│  Regression State    │    │(RBAC / Tenant Scope) │    │(regression_completed)│
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1 through 10.8 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run Regression Suite -> Execute Security Assertion Matrix -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.regression_suite_started`, `validation.regression_suite_completed`).
3. **Explainable Failure Diagnostics & Component Mapping**:
   - Every regression category result returns explicit diagnostic feedback: `failure_reason`, target `affected_component` (e.g. `FastAPI Web Routers & Middleware`, `AuditLogService Mandatory Event Dispatcher`), and actionable `remediation_guidance`.
4. **Continuous Regression Assertion Matrix**:
   - Verifies zero active SQLi/XSS/SSRF/RCE regressions, BOLA/BFLA guards, header hardening, pentest exploit re-execution blocking, supply chain lockfile hash integrity, container capability dropping, secret entropy, tenant isolation boundaries, RBAC decorators, and non-repudiation audit tracking.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 30. Security Control Plane Final Certification Architecture (Phase 10.10)

Vulnova provides a comprehensive security control plane final certification engine (`CertificationValidationRunnerService`) evaluating all 10 Security Control Plane domains completed during Era 10: CERTIFICATION1 (OWASP Web & API Top 10 Security Control Plane Certification), CERTIFICATION2 (Infrastructure & Configuration Certification), CERTIFICATION3 (Penetration Testing Readiness Certification), CERTIFICATION4 (Dependency & SCA Supply Chain Certification), CERTIFICATION5 (Container Security Certification), CERTIFICATION6 (Secrets & Cryptographic Certification), CERTIFICATION7 (Threat Model & STRIDE Certification), CERTIFICATION8 (Security Regression Certification), CERTIFICATION9 (Governance & Access Control Certification), and CERTIFICATION10 (Enterprise Compliance Readiness Certification).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│          Next.js 14 Security Certification Workspace                        │
│      (/validation/certification, ScoreCard, CategoryGrid, DetailsModal)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (Bearer JWT / X-API-Key)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│      FastAPI Certification Router (/api/v1/validation/certification/*)      │
│      (validation:read, validation:execute RBAC Guards & Audit Log Hooks)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              CertificationValidationRunnerService                           │
│ (Executes Assertion Matrix CERTIFICATION1 - CERTIFICATION10 against Platform)│
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ Security Control     │    │ Auth & Policy Engine │    │   AuditLogService    │
│ Certification State  │    │(RBAC / Tenant Scope) │    │(cert_completed)      │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Zero Database Table Duplication**:
   - Matches Phase 10.1 through 10.9 & Era 8 design patterns: zero new database tables, zero schema migrations, and zero archival storage overhead.
   - Operates in memory: `Run Certification Suite -> Execute Security Control Plane Assertions -> Record Audit Event -> Return DTO`.
2. **Ephemeral Audit Correlation Token (`suite_id`)**:
   - Each validation execution generates a runtime `uuid4()` string (`suite_id`) recorded in audit log events (`validation.certification_suite_started`, `validation.certification_suite_completed`).
3. **Explainable Failure Diagnostics & Control Domain Mapping**:
   - Every certification category result returns explicit diagnostic feedback: `failure_reason`, target `affected_control` (e.g. `OWASP Web Top 10 & API Security Top 10 Validation Engines`, `CryptoService AES-256-GCM Envelope Encryption & SHA-256 Key Hashing`), and actionable `remediation_guidance`.
4. **Comprehensive Control Plane Assertion Matrix**:
   - Evaluates OWASP Web/API engines, infrastructure header hardening, pentest exploit readiness, SCA supply chain lockfile cryptographic pins, container unprivileged execution & capability drops, secret scanning entropy, STRIDE threat mitigations, regression guards, RBAC hierarchy, and enterprise compliance readiness score.
5. **Tenant Isolation & Granular RBAC**:
   - Enforces `organization_id = current_user.organization_id` across all validation runs.
   - Permissions: `validation:read` (`Role.VIEWER` level 10+), `validation:execute` (`Role.SECURITY_ANALYST` level 20+), `validation:manage` (`Role.ADMIN` level 30+).

---

## 31. Multi-Factor Authentication Architecture (Phase 10.11)

Vulnova provides an enterprise Multi-Factor Authentication (MFA / TOTP) engine (`MFAService`) implementing RFC 6238 time-based one-time passcodes, AES-256-GCM encrypted TOTP secrets storage, Base64 QR code rendering, and single-use emergency backup recovery codes.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│             Next.js 14 MFA Workspace & Components                           │
│        (/security/mfa, QRCodeDisplay, OTPVerificationForm, StatusCard)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (/api/v1/auth/mfa/*)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          FastAPI MFA Router & Authentication Pipeline                       │
│    (Login Password Check -> MFA Challenge Token -> OTP Verification)        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MFAService                                        │
│ (TOTPService pyotp / CryptoService AES-256-GCM / RecoveryService SHA-256)   │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ UserModel (DB)       │    │ JWT Challenge Tokens │    │   AuditLogService    │
│(mfa_enabled, secret) │    │(mfa_login_token)     │    │(mfa_enabled/success) │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **AES-256-GCM Secret Encryption**:
   - Stored TOTP secrets are encrypted using `CryptoService` AES-256-GCM envelope encryption before persistence in `users.mfa_secret`. Plaintext secrets are never stored.
2. **Cryptographic SHA-256 Recovery Codes**:
   - Single-use recovery codes ('A1B2-C3D4-E5') are hashed using SHA-256 before JSON storage in `users.mfa_backup_codes`. Once consumed, codes are permanently removed.
3. **Two-Stage Authentication Challenge**:
   - When MFA is enabled, primary password verification returns an ephemeral signed JWT `mfa_login_token` (5 min expiration) requiring secondary OTP verification via `POST /api/v1/auth/mfa/challenge`.
4. **Time Drift Tolerance & Rate Limiting**:
   - RFC 6238 TOTP verification includes a 30s drift window. Failed attempts trigger `security.mfa_verification_failed` audit logs.
5. **Complete Security Audit Trail**:
   - All MFA lifecycle actions emit non-repudiable audit logs (`security.mfa_enabled`, `security.mfa_disabled`, `security.mfa_verification_success`, `security.mfa_verification_failed`, `security.mfa_recovery_used`).

---

## 32. Database Performance & Optimization Architecture (Phase 11.1)

Vulnova provides an enterprise database performance framework (`QueryAnalyzerService`, `DatabaseBenchmarkService`, `DatabaseQueryMonitor`) for PostgreSQL latency optimization, connection pool health, and composite index tuning.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Next.js 14 Database Performance Workspace                   │
│        (/database/performance, DatabasePerformanceCard, BenchmarkTable)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST (/api/v1/database/performance/*)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 FastAPI Database Performance REST Router                    │
│            (Health Metrics -> Query Benchmarking -> Slow Query Logs)        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Database Performance Layer                           │
│   (QueryAnalyzerService / DatabaseBenchmarkService / DatabaseQueryMonitor)  │
└──────────┬───────────────────────────┬───────────────────────────┬──────────┘
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ Composite Indexes    │    │ SQLAlchemy Pool      │    │ Slow Query Monitor   │
│(ix_users_org_role,   │    │(pool_size=20,        │    │(Threshold: >100ms,   │
│ ix_audit_logs_created│    │ max_overflow=10)     │    │ cursor events)       │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Production-Grade Connection Pooling**:
   - SQLAlchemy `AsyncEngine` configured with `pool_size=20`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=1800`, and `pool_pre_ping=True` to prevent connection starvation under high concurrency.
2. **Structural Composite Indexing**:
   - Alembic migration `0004_add_performance_indexes.py` defines composite indexes (`ix_users_org_role`, `ix_users_org_active`, `ix_audit_logs_org_action`, `ix_audit_logs_org_created`, `ix_refresh_tokens_user_revoked`, `ix_api_keys_org_active`).
3. **Automated Query Analyzer**:
   - `QueryAnalyzerService` analyzes execution patterns, captures slow query duration metadata, and outputs table-level index recommendations.
4. **Controlled Query Benchmarking**:
   - `DatabaseBenchmarkService` executes batch latency profiling for core queries, outputting average, p95, and p99 latency metrics.
5. **Slow Query Threshold Alerting**:
   - `DatabaseQueryMonitor` attaches SQLAlchemy event listeners (`before_cursor_execute`, `after_cursor_execute`) to detect and log queries exceeding the 100ms threshold.

---

## 33. Redis Caching & Distributed Rate Limiting Architecture (Phase 11.2)

Vulnova provides an enterprise Redis caching and distributed rate limiting architecture (`RedisClientManager`, `CacheService`, `MultiLayerCacheManager`, `DistributedRateLimiter`, `RateLimitMiddleware`).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Incoming HTTP Request                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RateLimitMiddleware                               │
│           (Identifies IP / User ID, checks Token Bucket in Redis)           │
└──────────────────┬──────────────────────────────────────┬───────────────────┘
                   │ Allowed                              │ Rate Exceeded
                   ▼                                      ▼
┌──────────────────────────────────────┐     ┌────────────────────────────────┐
│      Execute Route & Application     │     │ HTTP 429 Too Many Requests     │
│  (MultiLayerCacheManager: Tenant,    │     │ Headers: X-RateLimit-Limit,    │
│   User Session, Static Policy Cache) │     │ X-RateLimit-Remaining, Reset   │
└──────────────────────────────────────┘     └────────────────────────────────┘
```

### Key Architectural Safeguards:
1. **Graceful Degradation Resilience**:
   - `RedisClientManager` handles connection pool failures gracefully (`_is_available` flag). If Redis is offline, caching and rate limiting fall back to in-memory stores without interrupting HTTP application traffic.
2. **Multi-Layer Cache Hierarchy**:
   - **Tenant Lookup Cache**: `tenant:{org_id}` (15 min TTL).
   - **User Session Cache**: `session:{user_id}` (30 min TTL).
   - **Static Configuration Cache**: `config:{key}` (1 hour TTL).
3. **Token Bucket Rate Limiting**:
   - `DistributedRateLimiter` enforces atomic Redis sliding window token buckets per IP, per User, and per Organization (Anonymous: 100 req/min, Authenticated: 1000 req/min, Admin: 5000 req/min).
4. **Standard Compliance Headers**:
   - All responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.

---

## 34. Centralized Observability, Telemetry & Distributed Monitoring Architecture (Phase 11.3)

Vulnova provides an enterprise observability architecture (`StructuredLoggingService`, `MetricsCollector`, `TracingService`, `RequestTracingMiddleware`, `SystemHealthRouter`) integrated with Prometheus and Grafana.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Incoming HTTP Request                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RequestTracingMiddleware                           │
│        (Generates X-Request-ID, X-Correlation-ID, starts OTel span)         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ Prometheus Metrics   │    │ JSON Structured Logs │    │ Health & Readiness   │
│ GET /metrics         │    │(Sanitized passwords) │    │ GET /api/v1/system/* │
└──────────┬───────────┘    └──────────────────────┘    └──────────────────────┘
           │ Scraped by 15s interval
           ▼
┌──────────────────────┐    ┌──────────────────────┐
│ Prometheus Server    │───►│ Grafana Dashboards   │
│ (port 9090)          │    │ (port 3001)          │
└──────────────────────┘    └──────────────────────┘
```

### Key Architectural Safeguards:
1. **Context-Enriched Tracing**:
   - Every request is tagged with an immutable `X-Request-ID` and `X-Correlation-ID` propagated across log events, metrics counters, and OpenTelemetry distributed spans.
2. **Sensitive Data Redaction**:
   - `mask_sensitive_data()` automatically sanitizes passwords, JWTs, API tokens, TOTP secrets, and authorization headers prior to log serialization.
3. **Prometheus Exposition**:
   - `GET /metrics` exposes real-time HTTP throughput, query latency, database pool connections, Redis availability, and security audit counters.
4. **Grafana Dashboards**:
   - Provisioned dashboards for API Performance (`api_performance.json`), Database Metrics (`database_performance.json`), and Security Audit (`security_audit.json`).
---

## 💾 35. PostgreSQL Database Backup Strategy & Point-in-Time Recovery (PITR) Architecture (Phase 11.4)

Phase 11.4 establishes enterprise-grade database resilience, automated base backup creation, AES-256 Fernet payload encryption, SHA-256 checksum tracking, 30-day retention cleanup, Write-Ahead Logging (WAL) archiving for Point-in-Time Recovery (PITR), dry-run restore verification, and REST management router (`/api/v1/database/backups`):

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Database Backup REST Router                      │
│                        (/api/v1/database/backups)                           │
│           (GET list, POST create, POST verify, GET status)                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DatabaseBackupService Core Engine                     │
│                (Applies 30-day retention & metadata tracking)               │
└───────────────────┬─────────────────────────────────────┬───────────────────┘
                    │ 1. Generate Dump                    │ 2. Encrypt Dump
                    ▼                                     ▼
┌───────────────────────────────────────┐   ┌─────────────────────────────────┐
│     PostgreSQL Base Dump (.sql)       │   │    BackupEncryptionUtility      │
│  (pg_dump / simulated schema dump)    │───►│  (AES-256 Fernet + SHA-256)    │
└───────────────────────────────────────┘   └────────────────┬────────────────┘
                                                             │
                                                             ▼ Writes encrypted backup
                                            ┌─────────────────────────────────┐
                                            │ Encrypted Storage Archive (.enc)│
                                            │ (var/backups/bkp_YYYYMMDD.enc)  │
                                            └────────────────┬────────────────┘
                                                             │
                                                             ▼ 3. Verify Restore
                                            ┌─────────────────────────────────┐
                                            │   RestoreVerificationService    │
                                            │(Decrypts & checks DDL + rows)   │
                                            └─────────────────────────────────┘
```

### Key Architectural Safeguards:
1. **AES-256 Encrypted Backup Storage**:
   - `BackupEncryptionUtility` derives a 32-byte Fernet key from `settings.jwt_secret` (`hashlib.sha256`), encrypting database dump files before writing to disk (`var/backups/*.enc`). Unencrypted temporary files are deleted immediately.
2. **Automated 30-Day Retention Policy**:
   - `_apply_retention_policy()` purges backup files older than `RETENTION_DAYS = 30` automatically after every backup execution.
3. **Point-in-Time Recovery (PITR) & WAL Archiving**:
   - `deployment/postgres/postgresql.conf` configures `archive_mode = on`, `archive_command`, `archive_timeout = 60`, `wal_level = replica`, and `max_wal_senders` for continuous WAL streaming.
4. **Dry-Run Restore Verification**:
   - `RestoreVerificationService` performs dry-run restore validation by decrypting target backup archives in isolated temporary directories, verifying SHA-256 checksums, checking DDL schema integrity, and validating row counts.
5. **Role-Based REST API Management**:
   - `/api/v1/database/backups` endpoints are protected with `admin:read` (read-only history/status) and `admin:manage` (trigger backup/restore verification) RBAC permissions.

## 🛡️ 36. Enterprise Disaster Recovery, Failover & Rollback Architecture (Phase 11.5)

Vulnova implements an enterprise disaster recovery infrastructure with documented RTO (< 1 hour) and RPO (< 5 minutes) targets, automated failover workflows, deployment rollback mechanisms, and validated recovery procedures.

### Core Components:

| Component | Location | Purpose |
|---|---|---|
| **RecoveryService** | `app/infrastructure/disaster_recovery/recovery_service.py` | Orchestrates the 5-phase recovery lifecycle (Detection → Containment → Recovery → Validation → Restoration) with RTO/RPO tracking. |
| **FailoverService** | `app/infrastructure/disaster_recovery/failover_service.py` | Manages automated primary-to-secondary PostgreSQL failover with DNS endpoint swap and health validation. |
| **RollbackService** | `app/infrastructure/disaster_recovery/rollback_service.py` | Executes application deployment rollback to prior stable versions with container image swap and health check validation. |
| **DR API Router** | `app/api/v1/routers/disaster_recovery.py` | 7 REST endpoints for DR status, recovery execution, failover control, rollback operations, and event history — all `admin:read`/`admin:manage` RBAC-protected. |
| **DR Runbook** | `docs/operations/DISASTER_RECOVERY.md` | Comprehensive operational runbook with disaster classification matrix, recovery procedures, and post-recovery validation checklist. |
| **Automated Scripts** | `deployment/scripts/disaster-recovery/` | Bash automation for failover (`failover.sh`), service recovery (`service_recovery.sh`), and deployment rollback (`rollback_deployment.sh`). |

### Recovery Lifecycle Architecture:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│           FastAPI DR Router (/api/v1/disaster-recovery/*)                   │
│           (admin:read, admin:manage RBAC Guards & Structured Audit Logs)   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │ Recovery     │ │ Failover     │ │ Rollback     │
          │ Service      │ │ Service      │ │ Service      │
          │ (5-Phase     │ │ (Primary →   │ │ (Version     │
          │  Lifecycle)  │ │  Secondary)  │ │  Rollback)   │
          └──────────────┘ └──────────────┘ └──────────────┘
```

### Key Architectural Decisions:
1. **Zero Database Table Additions**: All DR state is managed in-memory with structured log persistence, consistent with Era 8+ zero-migration patterns.
2. **RTO/RPO Validated**: Every recovery execution tracks actual RTO achievement (minutes) and estimated RPO (based on WAL archiving frequency) against defined targets.
3. **Dependency-Ordered Recovery**: Service restoration follows strict sequential order (PostgreSQL → Redis → Backend → Celery → Frontend) to prevent cascading failures.
4. **RBAC-Protected Operations**: All DR endpoints require `admin:read` (status/history) or `admin:manage` (execute recovery/failover/rollback) permissions.











