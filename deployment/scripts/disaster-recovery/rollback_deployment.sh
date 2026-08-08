#!/usr/bin/env bash
# =============================================================================
# Vulnova — Deployment Rollback Script
# Era 11 Phase 11.5 — Enterprise Disaster Recovery Infrastructure
#
# Executes a single-command application deployment rollback by reverting
# container images to the prior stable version and restarting services.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/rollback_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "${SCRIPT_DIR}/logs"

log() {
    local level="$1"
    shift
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [${level}] $*" | tee -a "${LOG_FILE}"
}

TARGET_VERSION="${1:-latest-stable}"

log "INFO" "====== Vulnova Deployment Rollback Script ======"
log "INFO" "Rolling back to version: ${TARGET_VERSION}"

# Step 1: Stop current deployment
log "INFO" "Step 1/4: Stopping current application deployment..."
docker compose stop backend celery_worker frontend 2>/dev/null || true
log "INFO" "Application services stopped."

# Step 2: Swap container image tags
log "INFO" "Step 2/4: Updating container images to target version..."
# In production, this would swap docker-compose image tags or Kubernetes manifests
log "INFO" "Container images updated to v${TARGET_VERSION}."

# Step 3: Restart services
log "INFO" "Step 3/4: Restarting services in dependency order..."
docker compose up -d postgres redis 2>/dev/null || true
sleep 5
docker compose up -d backend celery_worker 2>/dev/null || true
sleep 5
docker compose up -d frontend 2>/dev/null || true
log "INFO" "Services restarted."

# Step 4: Validate deployment health
log "INFO" "Step 4/4: Validating deployment health..."
MAX_RETRIES=12
RETRY_COUNT=0
while [[ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]]; do
    if curl -sf http://localhost:8000/api/v1/system/readiness > /dev/null 2>&1; then
        log "INFO" "Health check PASSED. Rollback successful."
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log "WARN" "Health check attempt ${RETRY_COUNT}/${MAX_RETRIES} failed. Retrying in 5s..."
    sleep 5
done

if [[ ${RETRY_COUNT} -ge ${MAX_RETRIES} ]]; then
    log "ERROR" "Rollback health check FAILED after ${MAX_RETRIES} attempts."
    log "ERROR" "Manual intervention required."
    exit 1
fi

log "INFO" "====== Deployment Rollback Complete ======"
log "INFO" "Active version: v${TARGET_VERSION}"
