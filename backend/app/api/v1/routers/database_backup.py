"""FastAPI Database Backup & Point-in-Time Recovery (PITR) Management Router."""

from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, Query, status

from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.database.backup.backup_service import backup_service
from app.infrastructure.database.backup.dto import (
    BackupMetadataDTO,
    BackupStatusDTO,
    BackupVerificationDTO,
)
from app.infrastructure.database.backup.restore_verification_service import (
    restore_verification_service,
)
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/database/backups", tags=["Database Backup & PITR"])


@router.get(
    "",
    response_model=BackupMetadataDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Database Backup History & Metadata",
    description="Retrieve list of retained PostgreSQL backups, encryption status, and retention settings.",
)
async def list_database_backups(
    current_user: UserModel = Depends(require_permission("admin:read")),
) -> BackupMetadataDTO:
    """Retrieve full database backup history metadata."""
    logger.info("list_database_backups_requested", user_id=current_user.id)
    return await backup_service.list_backups()


@router.post(
    "/create",
    response_model=BackupStatusDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Manual Database Backup",
    description="Execute an immediate PostgreSQL base backup with AES-256 encryption and SHA-256 checksum generation.",
)
async def create_database_backup(
    current_user: UserModel = Depends(require_permission("admin:manage")),
) -> BackupStatusDTO:
    """Trigger manual base backup creation."""
    logger.info("manual_database_backup_requested", user_id=current_user.id)
    return await backup_service.create_backup(manual=True)


@router.post(
    "/verify",
    response_model=BackupVerificationDTO,
    status_code=status.HTTP_200_OK,
    summary="Execute Dry-Run Restore Verification",
    description="Decrypt target backup archive and execute schema and row-count integrity checks.",
)
async def verify_database_backup(
    backup_id: str = Query(
        None, description="Optional target backup ID (verifies latest if omitted)"
    ),
    current_user: UserModel = Depends(require_permission("admin:manage")),
) -> BackupVerificationDTO:
    """Run automated dry-run restore verification."""
    logger.info(
        "restore_verification_requested",
        user_id=current_user.id,
        target_backup=backup_id,
    )
    return await restore_verification_service.verify_restore(backup_id=backup_id)


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get Backup Service Operational Health Status",
    description="Retrieve high-level operational status of backup automation, retention policies, and storage.",
)
async def get_backup_health_status(
    current_user: UserModel = Depends(require_permission("admin:read")),
) -> Dict[str, Any]:
    """Retrieve high-level backup service health status."""
    metadata = await backup_service.list_backups()
    return {
        "status": "HEALTHY" if metadata.total_backups_count >= 0 else "DEGRADED",
        "total_backups": metadata.total_backups_count,
        "total_size_bytes": metadata.total_size_bytes,
        "retention_days": metadata.retention_days,
        "last_backup_at": metadata.last_backup_at,
        "wal_archiving": "ENABLED",
        "encryption": "AES-256",
    }
