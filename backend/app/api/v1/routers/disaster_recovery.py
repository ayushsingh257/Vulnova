"""FastAPI Disaster Recovery, Failover & Rollback Management Router."""

from typing import List

import structlog
from fastapi import APIRouter, Depends, Query, status

from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.disaster_recovery.dto import (
    DisasterRecoveryStatusDTO,
    FailoverEventDTO,
    RecoveryExecutionDTO,
    RollbackStatusDTO,
)
from app.infrastructure.disaster_recovery.failover_service import failover_service
from app.infrastructure.disaster_recovery.recovery_service import recovery_service
from app.infrastructure.disaster_recovery.rollback_service import rollback_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/disaster-recovery", tags=["Disaster Recovery & Rollback"])


@router.get(
    "/status",
    response_model=DisasterRecoveryStatusDTO,
    status_code=status.HTTP_200_OK,
    summary="Get DR Readiness Status",
    description="Retrieve current disaster recovery readiness, RTO/RPO targets, and component health state.",
)
async def get_dr_status(
    current_user: UserModel = Depends(require_permission("admin:read")),
) -> DisasterRecoveryStatusDTO:
    """Retrieve current DR readiness and system health status."""
    logger.info("dr_status_requested", user_id=current_user.id)
    return await recovery_service.get_dr_status()


@router.post(
    "/recover",
    response_model=RecoveryExecutionDTO,
    status_code=status.HTTP_200_OK,
    summary="Execute Recovery Workflow",
    description="Execute a disaster recovery workflow: PITR_RESTORE, FAILOVER, ROLLBACK, or SIMULATION.",
)
async def execute_recovery(
    recovery_type: str = Query(
        default="SIMULATION",
        description="Recovery type: SIMULATION, PITR_RESTORE, FAILOVER, ROLLBACK",
    ),
    current_user: UserModel = Depends(require_permission("admin:manage")),
) -> RecoveryExecutionDTO:
    """Execute a recovery or simulation workflow and return RTO/RPO results."""
    logger.info(
        "recovery_execution_requested",
        user_id=current_user.id,
        recovery_type=recovery_type,
    )
    return await recovery_service.execute_recovery(recovery_type=recovery_type)


@router.get(
    "/recovery-history",
    response_model=List[RecoveryExecutionDTO],
    status_code=status.HTTP_200_OK,
    summary="List Recovery History",
    description="Retrieve all past disaster recovery execution records and RTO/RPO outcomes.",
)
async def list_recovery_history(
    current_user: UserModel = Depends(require_permission("admin:read")),
) -> List[RecoveryExecutionDTO]:
    """Return all past recovery execution records."""
    logger.info("recovery_history_requested", user_id=current_user.id)
    return await recovery_service.list_recovery_history()


@router.post(
    "/failover",
    response_model=FailoverEventDTO,
    status_code=status.HTTP_200_OK,
    summary="Trigger Service Failover",
    description="Execute primary-to-secondary database failover with DNS swap and validation.",
)
async def trigger_failover(
    current_user: UserModel = Depends(require_permission("admin:manage")),
) -> FailoverEventDTO:
    """Trigger controlled primary-to-secondary failover promotion."""
    logger.info("failover_triggered", user_id=current_user.id)
    return await failover_service.trigger_failover(triggered_by="MANUAL_OPERATOR")


@router.get(
    "/failover-history",
    response_model=List[FailoverEventDTO],
    status_code=status.HTTP_200_OK,
    summary="List Failover Events",
    description="Retrieve all past failover event records.",
)
async def list_failover_events(
    current_user: UserModel = Depends(require_permission("admin:read")),
) -> List[FailoverEventDTO]:
    """Return all failover event records."""
    logger.info("failover_history_requested", user_id=current_user.id)
    return await failover_service.list_failover_events()


@router.post(
    "/rollback",
    response_model=RollbackStatusDTO,
    status_code=status.HTTP_200_OK,
    summary="Execute Deployment Rollback",
    description="Rollback application deployment to a prior version with health check validation.",
)
async def execute_rollback(
    target_version: str = Query(
        default="11.4.0",
        description="Target version to roll back to",
    ),
    current_user: UserModel = Depends(require_permission("admin:manage")),
) -> RollbackStatusDTO:
    """Execute deployment rollback to a target version."""
    logger.info(
        "rollback_requested",
        user_id=current_user.id,
        target_version=target_version,
    )
    return await rollback_service.execute_rollback(target_version=target_version)


@router.get(
    "/rollback-history",
    response_model=List[RollbackStatusDTO],
    status_code=status.HTTP_200_OK,
    summary="List Rollback History",
    description="Retrieve all past deployment rollback execution records.",
)
async def list_rollback_history(
    current_user: UserModel = Depends(require_permission("admin:read")),
) -> List[RollbackStatusDTO]:
    """Return all rollback execution records."""
    logger.info("rollback_history_requested", user_id=current_user.id)
    return await rollback_service.list_rollback_history()
