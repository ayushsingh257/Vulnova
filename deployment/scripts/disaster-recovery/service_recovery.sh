#!/usr/bin/env bash
# =============================================================================
# Vulnova — Service Recovery Script
# Era 11 Phase 11.5 — Enterprise Disaster Recovery Infrastructure
#
# Restarts all Vulnova services in strict dependency order to prevent
# cascading failures and connection exhaustion.
#
# Recovery Order: PostgreSQL → Redis → Backend → Celery Workers → Frontend
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/recovery_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "${SCRIPT_DIR}/logs"

log() {
    local level="$1"
    shift
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [${level}] $*" | tee -a "${LOG_FILE}"
}

wait_for_service() {
    local service_name="$1"
    local check_cmd="$2"
    local max_wait="${3:-30}"
    local elapsed=0

    while [[ ${elapsed} -lt ${max_wait} ]]; do
        if eval "${check_cmd}" > /dev/null 2>&1; then
            log "INFO" "${service_name} is healthy."
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    log "ERROR" "${service_name} failed to become healthy within ${max_wait}s."
    return 1
}

log "INFO" "====== Vulnova Service Recovery Script ======"
log "INFO" "Recovery order: PostgreSQL → Redis → Backend → Celery → Frontend"

# Step 1: PostgreSQL
log "INFO" "Step 1/5: Starting PostgreSQL..."
docker compose up -d postgres 2>/dev/null || true
wait_for_service "PostgreSQL" "docker compose exec -T postgres pg_isready -q"

# Step 2: Redis
log "INFO" "Step 2/5: Starting Redis..."
docker compose up -d redis 2>/dev/null || true
wait_for_service "Redis" "docker compose exec -T redis redis-cli ping"

# Step 3: Backend API
log "INFO" "Step 3/5: Starting Backend API..."
docker compose up -d backend 2>/dev/null || true
wait_for_service "Backend" "curl -sf http://localhost:8000/api/v1/system/readiness" 60

# Step 4: Celery Workers
log "INFO" "Step 4/5: Starting Celery Workers..."
docker compose up -d celery_worker 2>/dev/null || true
sleep 5
log "INFO" "Celery workers started."

# Step 5: Frontend (if applicable)
log "INFO" "Step 5/5: Starting Frontend..."
docker compose up -d frontend 2>/dev/null || true
sleep 5
log "INFO" "Frontend started."

# Final validation
log "INFO" "Running final health validation..."
if curl -sf http://localhost:8000/api/v1/system/readiness > /dev/null 2>&1; then
    log "INFO" "Final health check PASSED."
else
    log "ERROR" "Final health check FAILED. Manual intervention may be required."
    exit 1
fi

log "INFO" "====== Service Recovery Complete ======"
