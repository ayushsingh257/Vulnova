"""Application Service managing scan execution lifecycle, state machine transitions, locks, and retries."""

from typing import Dict, Optional, Set
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.scan_event_publisher import (
    ScanEventPublisherService,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import (
    ConflictException,
    ResourceNotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.domain.entities.scan_lifecycle import (
    RetryPolicy,
    ScanExecutionState,
)
from app.infrastructure.database.models.assessment import AssessmentJobModel
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)
from app.infrastructure.workers.scan_lock_manager import DistributedScanLockManager

logger = get_logger("vulnova.scan_lifecycle_manager")

# Strict State Transition Matrix
VALID_TRANSITIONS: Dict[ScanExecutionState, Set[ScanExecutionState]] = {
    ScanExecutionState.QUEUED: {
        ScanExecutionState.CRAWLING,
        ScanExecutionState.CANCELLED,
        ScanExecutionState.FAILED,
    },
    ScanExecutionState.CRAWLING: {
        ScanExecutionState.ASSESSING,
        ScanExecutionState.RETRYING,
        ScanExecutionState.CANCELLED,
        ScanExecutionState.FAILED,
    },
    ScanExecutionState.ASSESSING: {
        ScanExecutionState.AI_ANALYSIS,
        ScanExecutionState.RETRYING,
        ScanExecutionState.CANCELLED,
        ScanExecutionState.FAILED,
    },
    ScanExecutionState.AI_ANALYSIS: {
        ScanExecutionState.COMPLETED,
        ScanExecutionState.RETRYING,
        ScanExecutionState.CANCELLED,
        ScanExecutionState.FAILED,
    },
    ScanExecutionState.RETRYING: {
        ScanExecutionState.QUEUED,
        ScanExecutionState.CRAWLING,
        ScanExecutionState.CANCELLED,
        ScanExecutionState.FAILED,
    },
    ScanExecutionState.COMPLETED: set(),  # Terminal
    ScanExecutionState.FAILED: set(),  # Terminal
    ScanExecutionState.CANCELLED: set(),  # Terminal
}


class ScanLifecycleManagerService:
    """Application Service orchestrating scan execution lifecycle state machine, lock acquisition, and retries."""

    def __init__(
        self,
        session: AsyncSession,
        repo: Optional[AssessmentRepository] = None,
        publisher: Optional[ScanEventPublisherService] = None,
    ) -> None:
        self.session = session
        self.repo = repo or AssessmentRepository(session)
        self.audit_service = AuditLogService(session)
        self.lock_manager = DistributedScanLockManager()
        self.publisher = publisher or ScanEventPublisherService()

    def is_valid_transition(
        self, current_state: ScanExecutionState, target_state: ScanExecutionState
    ) -> bool:
        """Check if transition from current_state to target_state is allowed by matrix."""
        if current_state == target_state:
            return True
        allowed = VALID_TRANSITIONS.get(current_state, set())
        return target_state in allowed

    async def acquire_target_lock(
        self,
        organization_id: UUID,
        target_url: str,
        job_id: Optional[UUID] = None,
        ttl_seconds: int = 3600,
    ) -> None:
        """Acquire distributed scan lock on target URL. Throws ConflictException if locked."""
        owner = str(job_id) if job_id else "scan_job"
        acquired = await self.lock_manager.acquire_lock(
            organization_id=organization_id,
            target_url=target_url,
            ttl_seconds=ttl_seconds,
            owner_id=owner,
        )
        if not acquired:
            logger.warning(
                "scan_lifecycle.lock_collision",
                org_id=str(organization_id),
                target_url=target_url,
            )
            raise ConflictException(
                f"A scan job is already in progress for target '{target_url}' in your organization."
            )

    async def release_target_lock(self, organization_id: UUID, target_url: str) -> bool:
        """Release distributed lock on target URL."""
        return await self.lock_manager.release_lock(organization_id, target_url)

    async def transition_state(
        self,
        organization_id: UUID,
        job_id: UUID,
        target_state: ScanExecutionState,
        current_step: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        error_message: Optional[str] = None,
        actor_id: Optional[UUID] = None,
    ) -> AssessmentJobModel:
        """Advance scan execution state machine to target_state with transition validation.

        Raises:
            ResourceNotFoundException: If job_id is not found.
            ValidationException: If transition violates VALID_TRANSITIONS matrix.
        """
        job = await self.repo.get_job_by_id(organization_id, job_id)
        if not job:
            raise ResourceNotFoundException(
                f"Assessment job '{job_id}' not found in organization."
            )

        current_enum = ScanExecutionState(job.execution_state or "QUEUED")

        if not self.is_valid_transition(current_enum, target_state):
            logger.warning(
                "scan_lifecycle.invalid_transition_attempted",
                job_id=str(job_id),
                current_state=current_enum.value,
                target_state=target_state.value,
            )
            raise ValidationException(
                f"Invalid state transition from '{current_enum.value}' to '{target_state.value}'."
            )

        job.execution_state = target_state.value

        updated_job = await self.repo.update_execution_state(
            organization_id=organization_id,
            job_id=job_id,
            execution_state=target_state.value,
            current_step=current_step,
            duration_seconds=duration_seconds,
            error_message=error_message,
        )
        if updated_job is None:
            raise ResourceNotFoundException(
                f"Failed to update state for job '{job_id}'."
            )

        # Auto-release target lock on terminal states
        if target_state in (
            ScanExecutionState.COMPLETED,
            ScanExecutionState.FAILED,
            ScanExecutionState.CANCELLED,
        ):
            await self.release_target_lock(organization_id, job.target_url)

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="scan.state_transition",
            resource_type="assessment_job",
            resource_id=str(job_id),
            actor_user_id=actor_id,
            details={
                "previous_state": current_enum.value,
                "new_state": target_state.value,
                "current_step": current_step,
                "target_url": job.target_url,
            },
        )

        try:
            await self.publisher.publish_state_change(
                organization_id=organization_id,
                job_id=job_id,
                previous_state=current_enum.value,
                new_state=target_state.value,
                current_step=current_step,
            )
        except Exception as e:
            logger.warning("scan_lifecycle.publish_event_failed", error=str(e))

        logger.info(
            "scan_lifecycle.state_transition",
            job_id=str(job_id),
            previous_state=current_enum.value,
            new_state=target_state.value,
            step=current_step,
        )
        return updated_job

    async def handle_scan_failure(
        self,
        organization_id: UUID,
        job_id: UUID,
        exception: Exception,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> ScanExecutionState:
        """Handle execution exception by triggering managed retry or terminal failure."""
        job = await self.repo.get_job_by_id(organization_id, job_id)
        if not job:
            raise ResourceNotFoundException(f"Job '{job_id}' not found.")

        policy = retry_policy or RetryPolicy()
        error_msg = str(exception) or type(exception).__name__

        if job.retry_count < policy.max_retries:
            next_attempt = job.retry_count + 1
            delay = policy.compute_backoff_delay(job.retry_count)

            # Record retry attempt
            await self.repo.increment_retry_count(organization_id, job_id, error_msg)

            await self.audit_service.record_event(
                organization_id=organization_id,
                action="scan.retry_scheduled",
                resource_type="assessment_job",
                resource_id=str(job_id),
                details={
                    "retry_count": next_attempt,
                    "max_retries": policy.max_retries,
                    "backoff_delay_seconds": delay,
                    "error": error_msg,
                },
            )
            logger.warning(
                "scan_lifecycle.retry_scheduled",
                job_id=str(job_id),
                attempt=next_attempt,
                delay_sec=delay,
                error=error_msg,
            )
            return ScanExecutionState.RETRYING
        else:
            # Retries exhausted -> terminal failure
            await self.transition_state(
                organization_id=organization_id,
                job_id=job_id,
                target_state=ScanExecutionState.FAILED,
                error_message=f"Execution failed after {job.retry_count} retries: {error_msg}",
            )
            return ScanExecutionState.FAILED

    async def handle_scan_cancellation(
        self,
        organization_id: UUID,
        job_id: UUID,
        cancelled_by: UUID,
        reason: str = "User cancelled scan execution",
    ) -> AssessmentJobModel:
        """Signal abort and transition job state to CANCELLED."""
        return await self.transition_state(
            organization_id=organization_id,
            job_id=job_id,
            target_state=ScanExecutionState.CANCELLED,
            error_message=reason,
            actor_id=cancelled_by,
        )
