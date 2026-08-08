# Vulnova Enterprise Production Deployment Runbook

This document defines the production deployment architecture, Docker Compose orchestration, Kubernetes cluster manifests, TLS/HTTPS certificate management, Horizontal Pod Autoscaling (HPA), zero-downtime rolling updates, and disaster recovery rollback procedures for the Vulnova enterprise security platform.

---

## 1. Production Architecture Overview

Vulnova's production deployment supports both single-host Docker Compose and multi-node Kubernetes cluster architectures:

```text
                               ┌──────────────────────────────────────────────┐
                               │            NGINX / Ingress Controller         │
                               │  (TLS Termination, HSTS, CSP, Cert-Manager)  │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                   ┌──────────────────┴──────────────────┐
                                   ▼                                     ▼
                      ┌─────────────────────────┐           ┌─────────────────────────┐
                      │    Frontend Service     │           │     Backend API Pods    │
                      │  (Next.js App / Node)   │           │    (FastAPI / Uvicorn)   │
                      └─────────────────────────┘           └────────────┬────────────┘
                                                                         │
                   ┌──────────────────────┬──────────────────────────────┼──────────────────────────────┐
                   ▼                      ▼                              ▼                              ▼
      ┌────────────────────────┐┌───────────────────┐    ┌──────────────────────────────┐    ┌────────────────────┐
      │   PostgreSQL + Vector  ││   Redis Cluster   │    │  Celery Worker & Beat Pods   │    │   MinIO & Qdrant   │
      │ (Multi-Tenant Relational││  (Session/Cache)  │    │  (Async Scan Tasks & Cron)   │    │  (Reports & Vector)│
      └────────────────────────┘└───────────────────┘    └──────────────────────────────┘    └────────────────────┘
```

---

## 2. Docker Compose Production Deployment

### Quick Start
Single-command production deployment:
```bash
# 1. Copy environment template
cp .env.production.example .env.production

# 2. Configure production secrets in .env.production
nano .env.production

# 3. Validate Compose file syntax
docker compose -f docker-compose.prod.yml config

# 4. Launch production stack in background
docker compose -f docker-compose.prod.yml up -d --build
```

### Production Stack Services & Health Checks

| Service | Image | Internal Port | Health Check Endpoint / Command | Resource Limits |
|---|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | 5432 | `pg_isready -U vulnova_admin -d vulnova_db` | 2.0 CPUs / 4GB RAM |
| `redis` | `redis:7.2-alpine` | 6379 | `redis-cli ping` | 1.0 CPUs / 2GB RAM |
| `minio` | `minio/minio:RELEASE...` | 9000 | `curl -f http://localhost:9000/minio/health/live` | 1.0 CPUs / 2GB RAM |
| `qdrant` | `qdrant/qdrant:v1.7.4` | 6333 | `curl -f http://localhost:6333/healthz` | 1.0 CPUs / 2GB RAM |
| `backend` | Custom build | 8000 | `curl -f http://localhost:8000/health` | 2.0 CPUs / 4GB RAM |
| `celery-worker` | Custom build | N/A | Process liveness | 1.5 CPUs / 3GB RAM |
| `celery-beat` | Custom build | N/A | Process liveness | 0.5 CPUs / 1GB RAM |
| `frontend` | Custom build | 3000 | `wget --spider http://localhost:3000/` | 1.5 CPUs / 2GB RAM |

---

## 3. Kubernetes Production Cluster Deployment

### Directory Layout
```text
deployment/kubernetes/
├── namespace.yaml                # Dedicated namespace 'vulnova-prod'
├── configmap.yaml                # Non-sensitive environment variables
├── secrets.yaml.example          # Encrypted/Opaque secret definitions template
├── backend/                      # Backend API Deployment, ClusterIP Service, HPA
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── frontend/                     # Frontend App Deployment, ClusterIP Service, HPA
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── postgres/                     # StatefulSet & ClusterIP Service for PostgreSQL
│   ├── statefulset.yaml
│   └── service.yaml
├── redis/                        # Deployment & ClusterIP Service for Redis
│   ├── deployment.yaml
│   └── service.yaml
└── ingress/                      # NGINX Ingress with cert-manager TLS
    └── ingress.yaml
```

### Deployment Steps
```bash
# 1. Create Namespace
kubectl apply -f deployment/kubernetes/namespace.yaml

# 2. Apply ConfigMap & Secrets
kubectl apply -f deployment/kubernetes/configmap.yaml
# Ensure real secrets are created from secrets.yaml.example
kubectl apply -f deployment/kubernetes/secrets.yaml.example

# 3. Deploy Stateful Database & Cache Infrastructure
kubectl apply -f deployment/kubernetes/postgres/
kubectl apply -f deployment/kubernetes/redis/

# 4. Deploy Core Services (Backend, Frontend & HPA)
kubectl apply -f deployment/kubernetes/backend/
kubectl apply -f deployment/kubernetes/frontend/

# 5. Apply Ingress & Cert-Manager Rules
kubectl apply -f deployment/kubernetes/ingress/
```

---

## 4. TLS & HTTPS Configuration Strategy

- **In-Cluster TLS Manager**: `cert-manager` integrated with Let's Encrypt CA (`letsencrypt-prod`).
- **TLS Protocol Enforcement**: Minimum TLS 1.2 with TLS 1.3 preferred.
- **Security Headers Injection**:
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 5. Horizontal Pod Autoscaling (HPA) Strategy

- **Backend API HPA** (`backend/hpa.yaml`):
  - Target: 3 minimum replicas to 10 maximum replicas.
  - Scale-up trigger: CPU utilization > 75% OR Memory utilization > 80%.
- **Frontend App HPA** (`frontend/hpa.yaml`):
  - Target: 2 minimum replicas to 8 maximum replicas.
  - Scale-up trigger: CPU utilization > 75% OR Memory utilization > 80%.

---

## 6. Zero-Downtime Rolling Update & Rollback Procedures

### Rolling Deployment
```bash
# Update backend image version without downtime
kubectl set image deployment/vulnova-backend backend=vulnova/backend:v1.0.0 -n vulnova-prod

# Monitor rolling rollout status
kubectl rollout status deployment/vulnova-backend -n vulnova-prod
```

### Emergency Rollback
```bash
# Inspect rollout history
kubectl rollout history deployment/vulnova-backend -n vulnova-prod

# Rollback to immediate prior version
kubectl rollout undo deployment/vulnova-backend -n vulnova-prod

# Or execute container script rollback:
./deployment/scripts/disaster-recovery/rollback_deployment.sh
```
