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
