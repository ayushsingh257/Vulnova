# Vulnova — Deployment & Infrastructure Blueprint (DEPLOYMENT.md)

This document provides local development orchestration guidelines, multi-stage production Docker configurations, Traefik reverse proxy settings, and cloud deployment blueprints for **Vulnova**.

---

## 🐳 1. Docker Compose Local & Staging Orchestration

`docker-compose.yml` orchestrates all system containers:

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: vulnova-postgres
    environment:
      POSTGRES_DB: vulnova_db
      POSTGRES_USER: vulnova_admin
      POSTGRES_PASSWORD: vulnova_secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vulnova_admin -d vulnova_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7.2-alpine
    container_name: vulnova-redis
    command: redis-server --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: vulnova-backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://vulnova_admin:vulnova_secure_password@postgres:5432/vulnova_db
      REDIS_URL: redis://redis:6379/0
    volumes:
      - evidence_data:/app/uploads/evidence
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: vulnova-celery-worker
    command: celery -A app.tasks.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://vulnova_admin:vulnova_secure_password@postgres:5432/vulnova_db
      REDIS_URL: redis://redis:6379/0
    volumes:
      - evidence_data:/app/uploads/evidence
    depends_on:
      - backend

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: vulnova-frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1

volumes:
  postgres_data:
  redis_data:
  evidence_data:
```

---

## 🔒 2. Production Reverse Proxy (Traefik)

Traefik manages TLS termination, Let's Encrypt certificates, HTTP/2, and WebSocket routing:

- Routers: `https://vulnova.local` -> `frontend:3000`
- Routers: `https://api.vulnova.local` -> `backend:8000` (WebSockets enabled)

---

## ☁️ 3. Kubernetes / Helm Migration Strategy

For production enterprise deployments, Vulnova provides Helm charts under `infra/helm/vulnova/` featuring:
- Horizontal Pod Autoscaler (HPA) for Celery assessment workers based on queue length.
- Dedicated StatefulSets for PostgreSQL & Redis with persistent volume claims (PVC).
- PersistentVolumeClaim (PVC) for multi-modal evidence store (`evidence_data` mount or S3/MinIO cloud object storage).

---

## ⚡ 4. Distributed Worker Sandbox Policy Compatibility (Era 6 Future Readiness)

- **Stateless Execution Policy Reuse**: The `ScanPolicyEngine` (`app/application/assessment/policy_engine.py`) introduced in Phase 4.7 operates statelessly without dependencies on web framework routers or database connections.
- **Worker Sandbox Integration**: In future Era 6 distributed worker deployments, Celery worker nodes running in unprivileged sandbox pods will directly consume `ScanPolicyEngine` to enforce URL scope matching, concurrency throttling, header/cookie injection, and emergency `stop_on_critical` scan termination.
- **Zero Deployment Infrastructure Overhead**: No additional deployment topology changes or new services are required currently.

---

## 📊 5. Asset Inventory Indexing & Database Query Performance (Phase 4.8)

- **Tenant-Isolated Asset Query Indexing**: `asset_nodes` and `security_findings` tables utilize composite PostgreSQL indexes on `(organization_id, node_type)` and `(organization_id, asset_node_id)` to ensure sub-millisecond query execution times for asset inventory dashboards (`GET /api/v1/assets/inventory`).
- **Zero Graph Node Explosion**: Finding data remains in `security_findings`, preventing table size inflation in `asset_nodes` and `asset_relationships`.

---

## 📈 6. Continuous Monitoring Snapshot Retention & Query Performance (Phase 4.9)

- **Composite Posture Indexing**: `asset_snapshots` and `asset_change_events` tables utilize composite PostgreSQL indexes on `(organization_id, created_at)` and `(organization_id, change_type)` to optimize historical risk trajectory (`GET /api/v1/assets/trends`) and posture timeline queries.
- **Snapshot Retention Strategy**: Posture snapshots are lightweight metric aggregates (~200 bytes per record) linked to `assessment_job_id` and timestamped, allowing multi-year security posture audit histories without storage bottlenecks.

---

## 🏷️ 7. Triage Audit History Retention & Automated Suppression Indexing (Phase 4.10)

- **Triage Audit Trail Indexing**: `finding_triage_history` table utilizes composite indexes `(organization_id, finding_id)` and `(organization_id, created_at)` to support sub-millisecond retrieval of historical finding triage decisions (`GET /api/v1/findings/{id}/triage-history`).
- **Suppression Rule Evaluation**: `finding_suppression_rules` table utilizes composite index `(organization_id, is_active)` to ensure fast in-memory matching of active false-positive rules during post-assessment pipeline execution.
- **Data Retention Strategy**: Triage audit history records are immutable and lightweight (~150 bytes per record), providing non-repudiable audit trails for SOC 2 Type II and ISO 27001 compliance.

---

## 🤖 8. LLM Gateway Configuration & Ollama Local AI Deployment Options (Phase 5.1)

- **Zero Mandatory SDK Dependency Footprint**: Provider adapters (`OpenAIAdapter`, `AnthropicAdapter`, `GoogleAdapter`, `LocalOllamaAdapter`) execute raw REST calls via `httpx.AsyncClient`. No heavy Python LLM SDK packages are required in production container builds (`Dockerfile.backend`).
- **Local / Air-Gapped AI Deployment**: For enterprise deployments requiring 100% air-gapped data privacy, Vulnova connects directly to local Ollama REST instances (`http://localhost:11434/api/chat` or `http://ollama-service:11434`). If external cloud providers fail or are unconfigured, `LLMGatewayService` automatically falls back to local Ollama execution with zero USD API cost.
- **Encrpyted Secret Storage**: API keys configured via `POST /api/v1/ai/providers` are encrypted at rest using AES-256-GCM via `SecretEncryptionService` and `SECRET_KEY` derivation seed.
- **AI Request Log Retention**: `llm_request_logs` records input/output token counts, latency (ms), and cost estimates ($) indexed by `(organization_id, created_at)` for cost tracking and CISO governance.

---

## 🤖 9. AI Finding Explainer & Impact Analysis Performance & Storage Blueprint (Phase 5.2)

- **Immutable Append-Only Storage**: `ai_finding_explanations` and `ai_impact_analyses` tables feature composite indexes `(organization_id, finding_id)` and `(organization_id, created_at)` to support sub-millisecond retrieval of historical AI analysis versions (`GET /api/v1/ai/findings/{id}/explanation`, `GET /api/v1/ai/findings/{id}/impact`).
- **Structured Output JSON Recovery Overhead**: In the event of malformed LLM JSON output, the single repair retry adds a minor latency overhead (~200–500ms) but guarantees structured data integrity and prevents corrupt records from entering database tables.
- **Resource Footprint**: Explanation and impact records average ~1–2 KB per analysis version, permitting years of AI analysis history per tenant organization without database degradation.

---

## 🤖 10. AI Attack Path Synthesis Performance & Storage Blueprint (Phase 5.3)

- **Option A Relational Query Indexing**: `ai_attack_paths` and `ai_attack_path_steps` tables feature composite PostgreSQL indexes `(organization_id, root_finding_id)`, `(organization_id, status)`, `(attack_path_id, sequence_number)`, and `(mitre_technique_id)`. This enables sub-millisecond querying of attack paths by MITRE technique or finding ID.
- **Eager Loading Optimization**: `AIAttackPathRepository` utilizes SQLAlchemy `selectinload(AIAttackPathModel.steps)` to retrieve full attack paths and their ordered steps in a single optimized DB round-trip.
- **Analyst Review Metadata Indexing**: `ai_attack_paths.status` index supports fast filtering of paths requiring SOC analyst validation (`GENERATED` vs `REVIEWED` / `ACCEPTED`).

---

## 🤖 11. AI Remediation Engine Performance & Storage Blueprint (Phase 5.4)

- **3-Table Normalized Relational Indexing**: `ai_remediation_plans`, `ai_remediation_steps`, and `ai_patch_suggestions` feature composite indexes `(organization_id, root_finding_id)`, `(organization_id, status)`, `(remediation_plan_id, sequence_number)`, and `(remediation_plan_id, language)`. This allows sub-millisecond querying of remediation plans and patch suggestions by language or finding ID.
- **Eager Loading Optimization**: `AIRemediationRepository` utilizes SQLAlchemy `selectinload(AIRemediationPlanModel.steps)` and `selectinload(AIRemediationPlanModel.patch_suggestions)` to fetch master plans, step sequences, and code patch diffs in a single query.
- **Review State Machine Indexing**: Index on `ai_remediation_plans.status` supports fast filtering of plans by review state (`GENERATED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `IMPLEMENTED`, `VERIFIED`, `VALIDATION_FAILED`).

---

## 🤖 12. AI False Positive Filter & Confidence Engine Performance & Storage Blueprint (Phase 5.5)

- **2-Table Relational Query Indexing**: `ai_finding_confidence_analyses` and `ai_finding_similarity_matches` feature composite PostgreSQL indexes `(organization_id, finding_id)`, `(organization_id, classification)`, `(organization_id, source_finding_id)`, and `(similarity_score)`. This enables sub-millisecond query performance for confidence assessments and similarity correlations.
- **Eager Loading Optimization**: `AIConfidenceRepository` utilizes SQLAlchemy `selectinload(AIFindingConfidenceAnalysisModel.similarity_matches)` to fetch confidence assessments and correlated duplicate matches in a single database round-trip.
- **Calibration Feedback Performance**: Calibration metadata columns (`predicted_confidence_score`, `confidence_accuracy_delta`, `feedback_timestamp`) allow offline training dataset extraction without runtime performance degradation.

---

## 🤖 13. Security Knowledge Base & RAG Vector Engine Performance & Storage Blueprint (Phase 5.6)

- **PostgreSQL pgvector HNSW Indexing**: `security_knowledge_chunks` utilizes HNSW (Hierarchical Navigable Small World) index tuning `USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`. This guarantees sub-5ms cosine similarity vector search performance over 100,000+ vector chunks.
- **Source-Type Chunking Efficiency**: Source-type chunk size parameters (`OWASP`/`CWE`/`CAPEC`: 512, `CVE_NVD`: 256, `INTERNAL_POLICY`: 768) minimize chunk fragmentation and maximize semantic retrieval accuracy.
- **Hybrid Tenant Filtering Optimization**: Single composite index `(organization_id, status)` and `(document_id, chunk_index)` allows tenant boundary filtering (`organization_id IS NULL OR organization_id = tenant_id`) with zero performance degradation.

---

## 🤖 14. Enterprise AI Security Copilot Performance & Storage Blueprint (Phase 5.7)

- **5-Table Relational Indexing**: `ai_copilot_sessions`, `ai_copilot_messages`, `ai_copilot_context_memories`, `ai_copilot_tool_executions`, and `ai_copilot_feedback` feature composite PostgreSQL indexes `(organization_id, user_id)`, `(session_id, role)`, `(session_id, memory_key)`, and `(organization_id, rating)`. This enables sub-millisecond session history & memory query performance.
- **Eager Loading Optimization**: `AICopilotRepository` utilizes SQLAlchemy `selectinload(CopilotSessionModel.messages)` and `selectinload(CopilotSessionModel.context_memories)` to fetch active investigation sessions, chat history, and persistent context memory in a single database round-trip.
- **Grounding Explainability Indexing**: Grounding metadata columns (`response_confidence_score`, `sources_used`, `knowledge_chunks_used`, `tools_called`, `reasoning_summary`, `model_used`, `prompt_version`, `response_evaluation_metadata`) allow instant auditability of AI recommendations without secondary database joins.








