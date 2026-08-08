# Vulnova — Enterprise Disaster Recovery, RTO/RPO & Rollback Runbook

This operational runbook defines Vulnova's enterprise disaster recovery protocol, Recovery Time Objective (RTO < 1 hour), Recovery Point Objective (RPO < 5 minutes), failover automation, rollback hooks, and step-by-step restoration procedures.

---

## 🎯 1. RTO & RPO Targets

| Operational Metric | Target Threshold | Description |
|---|---|---|
| **RTO (Recovery Time Objective)** | **< 1 Hour** | Maximum tolerable duration of service interruption from disaster occurrence to full operational recovery. |
| **RPO (Recovery Point Objective)** | **< 5 Minutes** | Maximum acceptable data loss window measured by continuous PostgreSQL WAL archiving stream. |

---

## 🚨 2. Disaster Classification & Severity Matrix

| Severity Level | Disaster Category | Impacted Subsystem | Trigger Criteria | Action Protocol |
|---|---|---|---|---|
| **DR-SEV-1 (Critical)** | **Database Failure / Data Corruption** | PostgreSQL Primary Cluster | Primary DB unreachable, disk failure, or corrupted data state. | Execute automated WAL point-in-time recovery or failover to secondary replica. |
| **DR-SEV-2 (High)** | **Regional Outage / Infrastructure Loss** | Multi-Container Cluster | Cloud region network partition, host hardware crash, or full docker node outage. | Trigger regional DNS failover and spin up secondary disaster recovery stack. |
| **DR-SEV-3 (High)** | **Application Failure / Bad Deployment** | FastAPI / Celery / Next.js | High API HTTP 500 error rate (> 15%) post-deployment or crash loop. | Execute single-command deployment rollback hook (`rollback_deployment.sh`). |
| **DR-SEV-4 (Medium)** | **Cache / In-Memory State Loss** | Redis Cluster | Cache instance crash or memory eviction flush. | Restart Redis container; system gracefully degrades to DB without data loss. |
| **DR-SEV-5 (Critical)** | **Security Compromise / Breach** | Identity & Key Infrastructure | Compromised signing keys or credential leak. | Revoke all active sessions, rotate JWT secret keys, and isolate network egress. |

---

## 🔄 3. Recovery Lifecycle & Execution Procedures

### 3.0 Recovery Lifecycle Phases

Every disaster recovery operation follows a strict five-phase lifecycle:

1. **Detection**: Automated health probes (`/api/v1/system/readiness`, `/api/v1/system/liveness`) and Prometheus metric threshold alerts identify service degradation or failure.
2. **Containment**: Isolate failed components to prevent cascading failures. Halt incoming traffic to degraded services via load balancer health check failures.
3. **Recovery Execution**: Execute the appropriate recovery procedure based on disaster classification (PITR restore, failover promotion, deployment rollback).
4. **Validation**: Run post-recovery health checks, schema integrity verification, and service dependency validation before restoring traffic.
5. **Service Restoration**: Gradually restore traffic routing, confirm end-to-end functionality, and record DR event in audit trail.

### 3.1 Service Dependency Recovery Order

To prevent cascading connection exhaustion and initialization deadlocks, components MUST be restored in strict sequential order:

```text
┌─────────────────────────┐
│ 1. Storage & Network    │ (PostgreSQL Primary / Replica, Docker Networks)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 2. Cache Infrastructure │ (Redis Instance & Distributed Rate Limiter)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 3. Core Backend API     │ (FastAPI Services & Database Connection Pool)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 4. Asynchronous Workers │ (Celery Task Workers & Scan Orchestrator)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 5. Ingress & Frontend   │ (Next.js Application & Reverse Proxy Ingress)
└─────────────────────────┘
```

### 3.2 PostgreSQL Point-in-Time Recovery (PITR) & WAL Restoration

When database corruption or catastrophic failure occurs, perform Point-in-Time Recovery (PITR):

1. **Containment & Isolation**:
   ```bash
   docker compose stop backend celery_worker
   ```
2. **Promote Backup Archive**:
   - Locate latest encrypted backup payload (`var/backups/bkp_YYYYMMDD_HHMMSS.enc`).
   - Run decrypt utility (`BackupEncryptionUtility.decrypt_file()`).
3. **Execute Base Dump Restoration**:
   ```bash
   pg_restore -h localhost -U vulnova_admin -d vulnova_db --clean var/backups/decrypted_target.sql
   ```
4. **Replay WAL Logs (RPO < 5 min)**:
   - Configure `recovery.signal` in PostgreSQL data directory.
   - Set `restore_command = 'cp /var/lib/postgresql/wal_archive/%f "%p"'`.
   - Set `recovery_target_time = 'YYYY-MM-DD HH:MM:SS'`.
   - Start PostgreSQL service to replay WAL files up to the target timestamp.

### 3.3 Backup Restoration Process

1. Retrieve the latest encrypted backup from `var/backups/`.
2. Verify SHA-256 checksum integrity against stored metadata.
3. Decrypt backup archive using `BackupEncryptionUtility.decrypt_file()`.
4. Restore database from decrypted dump.
5. Validate schema integrity via `RestoreVerificationService.verify_restore()`.

### 3.4 Redis Recovery Process

1. Restart Redis container: `docker compose restart redis`.
2. Verify Redis health via `PING` response.
3. Multi-layer cache manager (`MultiLayerCacheManager`) automatically repopulates tenant lookup, session, and config caches on first access.
4. Distributed rate limiter counters reset naturally (sliding window expiry).

### 3.5 Application Recovery Process

1. Execute service recovery script: `./deployment/scripts/disaster-recovery/service_recovery.sh`.
2. Restart failed application containers in dependency order.
3. Verify system readiness via `GET /api/v1/system/readiness`.
4. Confirm health via `GET /api/v1/system/health`.

### 3.6 Application Deployment Rollback Procedure

If a bad release introduces regressions or crashes:

1. **Trigger Automated Rollback Script**:
   ```bash
   ./deployment/scripts/disaster-recovery/rollback_deployment.sh
   ```
2. **Execute REST Router Rollback Endpoint**:
   ```bash
   curl -X POST https://api.vulnova.local/api/v1/disaster-recovery/rollback \
     -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```
3. **Validate Deployment Health**:
   - Verify `GET /api/v1/system/readiness` returns `200 OK`.

---

## 📋 4. Post-Recovery Validation Checklist

- [ ] **Database Connectivity**: Verify connection pool ping (`pool_pre_ping=True`) and schema integrity.
- [ ] **Cache Liveness**: Verify Redis `PING` response and session cache layer accessibility.
- [ ] **API Endpoint Readiness**: Verify `/api/v1/system/readiness` returns HTTP 200 OK.
- [ ] **RBAC & Auth Integrity**: Validate JWT access token generation and permission checking.
- [ ] **Celery Worker Execution**: Dispatch test scan job to confirm worker task processing.
- [ ] **Audit Trail Record**: Confirm DR event recording in audit log system (`disaster_recovery.failover_executed`, `disaster_recovery.rollback_executed`).
- [ ] **Prometheus Metrics**: Confirm `/metrics` endpoint resumes exposing live counters.
- [ ] **Grafana Dashboards**: Verify dashboard data streams resume after recovery.
