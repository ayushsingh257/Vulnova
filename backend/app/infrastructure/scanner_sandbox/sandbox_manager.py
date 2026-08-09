"""Scanner Sandbox Orchestration Manager."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.infrastructure.database.models.scanner_sandbox import ScannerSandboxModel
from app.infrastructure.database.repositories.scanner_sandbox_repository import (
    ScannerSandboxRepository,
)
from app.infrastructure.scanner_sandbox.container_driver import (
    EphemeralContainerDriver,
)
from app.infrastructure.scanner_sandbox.dto import (
    SandboxCreationRequestDTO,
    SandboxExecutionResultDTO,
    SandboxSecurityConfigDTO,
    SandboxStatus,
    ScannerSandboxDTO,
)
from app.infrastructure.scanner_sandbox.security_policy import ScannerSecurityPolicy

logger = logging.getLogger("vulnova.scanner_sandbox.manager")


class ScannerSandboxManager:
    """Enterprise manager governing the complete lifecycle of isolated scanner execution sandboxes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ScannerSandboxRepository(session)
        self.audit_service = AuditLogService(session)
        self.driver = EphemeralContainerDriver()

    async def execute_sandboxed_scan(
        self,
        request: SandboxCreationRequestDTO,
        actor_user_id: Optional[UUID] = None,
    ) -> SandboxExecutionResultDTO:
        """Create an ephemeral sandbox, execute active scanning, collect results, and destroy the container."""
        # 1. Resolve security configuration
        security_config = request.custom_security_config or SandboxSecurityConfigDTO()

        # 2. Validate Security Policy
        validated_config = ScannerSecurityPolicy.validate_security_config(
            security_config
        )

        # 3. Create Sandbox Record in Database (Status: CREATED)
        sandbox_uuid = uuid4()
        container_name = f"vulnova-sb-{str(sandbox_uuid)[:8]}"

        db_model = ScannerSandboxModel(
            id=sandbox_uuid,
            organization_id=request.organization_id,
            scan_job_id=request.scan_job_id,
            container_id=container_name,
            image_name=self.driver.image_name,
            status=SandboxStatus.CREATED.value,
            cpu_limit=validated_config.cpu_limit,
            memory_limit=validated_config.memory_limit,
            read_only_rootfs=validated_config.read_only_rootfs,
            network_mode=validated_config.network_mode,
            execution_metadata={
                "target_url": request.target_url,
                "enabled_plugins": request.enabled_plugins,
                "non_root_uid": validated_config.non_root_uid,
                "non_root_gid": validated_config.non_root_gid,
            },
        )
        await self.repo.create_sandbox(db_model)

        # 4. Audit Log: Sandbox Created
        await self._log_audit_event(
            action="sandbox_created",
            organization_id=request.organization_id,
            user_id=actor_user_id,
            sandbox_id=sandbox_uuid,
            details={
                "scan_job_id": str(request.scan_job_id),
                "target_url": request.target_url,
                "container_id": container_name,
            },
        )

        # 5. Transition to RUNNING & Audit Log
        await self.repo.update_status(sandbox_uuid, SandboxStatus.RUNNING.value)
        await self._log_audit_event(
            action="scanner_started",
            organization_id=request.organization_id,
            user_id=actor_user_id,
            sandbox_id=sandbox_uuid,
            details={"scan_job_id": str(request.scan_job_id), "status": "RUNNING"},
        )

        # 6. Execute Scanning Task in Container Sandbox
        result = await self.driver.create_and_run_sandbox(
            sandbox_id=sandbox_uuid,
            scan_job_id=request.scan_job_id,
            target_url=request.target_url,
            enabled_plugins=request.enabled_plugins,
            config=validated_config,
        )

        # 7. Transition DB state to COMPLETED or FAILED
        final_status = (
            SandboxStatus.COMPLETED
            if result.status == SandboxStatus.COMPLETED
            else SandboxStatus.FAILED
        )
        await self.repo.update_status(
            sandbox_id=sandbox_uuid,
            status=final_status.value,
            exit_code=result.exit_code,
            execution_metadata={
                "duration_seconds": result.duration_seconds,
                "findings_count": len(result.raw_findings),
                "error_log": result.error_log,
            },
        )

        audit_action = (
            "scanner_completed"
            if result.status == SandboxStatus.COMPLETED
            else "sandbox_failed"
        )
        await self._log_audit_event(
            action=audit_action,
            organization_id=request.organization_id,
            user_id=actor_user_id,
            sandbox_id=sandbox_uuid,
            details={
                "exit_code": result.exit_code,
                "duration_seconds": result.duration_seconds,
                "findings_count": len(result.raw_findings),
            },
        )

        # 8. Destroy Sandbox Container Resource Immediately Post-Scan
        await self.driver.destroy_container(result.container_id)
        await self.repo.update_status(sandbox_uuid, SandboxStatus.DESTROYED.value)

        # 9. Audit Log: Sandbox Destroyed
        await self._log_audit_event(
            action="sandbox_destroyed",
            organization_id=request.organization_id,
            user_id=actor_user_id,
            sandbox_id=sandbox_uuid,
            details={
                "container_id": result.container_id,
                "scan_job_id": str(request.scan_job_id),
            },
        )

        result.status = SandboxStatus.DESTROYED
        return result

    async def get_sandbox(
        self, sandbox_id: UUID, organization_id: UUID
    ) -> Optional[ScannerSandboxDTO]:
        """Retrieve details of a specific scanner sandbox enforcing tenant boundaries."""
        db_model = await self.repo.get_sandbox_by_id(sandbox_id, organization_id)
        if not db_model:
            return None
        return self._to_dto(db_model)

    async def list_sandboxes(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ScannerSandboxDTO], int]:
        """List paginated sandboxes for an organization."""
        models, total = await self.repo.list_sandboxes_by_org(
            organization_id, status, page, page_size
        )
        dtos = [self._to_dto(m) for m in models]
        return dtos, total

    async def force_destroy_sandbox(
        self,
        sandbox_id: UUID,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> bool:
        """Force destroy a dangling or running container sandbox."""
        db_model = await self.repo.get_sandbox_by_id(sandbox_id, organization_id)
        if not db_model:
            return False

        await self.driver.destroy_container(db_model.container_id)
        await self.repo.update_status(sandbox_id, SandboxStatus.DESTROYED.value)

        await self._log_audit_event(
            action="sandbox_destroyed",
            organization_id=organization_id,
            user_id=actor_user_id,
            sandbox_id=sandbox_id,
            details={"force_destroy": True, "container_id": db_model.container_id},
        )
        return True

    async def _log_audit_event(
        self,
        action: str,
        organization_id: UUID,
        user_id: Optional[UUID],
        sandbox_id: UUID,
        details: Dict[str, Any],
    ) -> None:
        """Internal helper to dispatch immutable audit log events."""
        try:
            payload = {"sandbox_id": str(sandbox_id), **details}
            await self.audit_service.record_event(
                organization_id=organization_id,
                action=f"scanner_sandbox.{action}",
                resource_type="scanner_sandbox",
                resource_id=str(sandbox_id),
                actor_user_id=user_id,
                details=payload,
            )
        except Exception as err:
            logger.warning("Failed to record sandbox audit log event: %s", str(err))

    def _to_dto(self, model: ScannerSandboxModel) -> ScannerSandboxDTO:
        """Convert database model to API DTO."""
        return ScannerSandboxDTO(
            id=model.id,
            organization_id=model.organization_id,
            scan_job_id=model.scan_job_id,
            container_id=model.container_id,
            image_name=model.image_name,
            status=SandboxStatus(model.status),
            cpu_limit=model.cpu_limit,
            memory_limit=model.memory_limit,
            read_only_rootfs=model.read_only_rootfs,
            network_mode=model.network_mode,
            exit_code=model.exit_code,
            execution_metadata=model.execution_metadata,
            created_at=model.created_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            destroyed_at=model.destroyed_at,
        )
