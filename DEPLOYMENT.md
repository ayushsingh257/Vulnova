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



