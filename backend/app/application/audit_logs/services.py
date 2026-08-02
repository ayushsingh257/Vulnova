"""Audit Log Application Use Case Services."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.dto import (
    AuditLogListResponse,
    AuditLogResponse,
)
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.repositories.audit_log_repository import (
    AuditLogRepository,
)

logger = get_logger("vulnova.audit_logs")


class AuditLogService:
    """Application service for recording and retrieving security audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuditLogRepository(session)

    async def record_event(
        self,
        organization_id: UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        actor_user_id: Optional[UUID] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLogResponse:
        """Record an immutable security audit event into database.

        Execution is fail-safe: failures are logged as warnings to prevent audit logger
        errors from throwing uncaught exceptions during primary user transactions.
        """
        try:
            audit_log = AuditLogModel(
                id=uuid4(),
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action.strip(),
                resource_type=resource_type.strip(),
                resource_id=resource_id.strip() if resource_id else None,
                client_ip=client_ip.strip() if client_ip else None,
                user_agent=user_agent.strip() if user_agent else None,
                details=details or {},
                created_at=datetime.now(timezone.utc),
            )

            saved_log = await self.repo.create(audit_log)
            logger.info(
                "audit_event_recorded",
                action=action,
                organization_id=str(organization_id),
                actor_user_id=str(actor_user_id) if actor_user_id else None,
                resource_type=resource_type,
            )
            return AuditLogResponse.model_validate(saved_log)
        except Exception as e:
            logger.warning(
                "audit_event_recording_failed",
                action=action,
                organization_id=str(organization_id),
                error=str(e),
            )
            # Re-raise if within an explicit audit service call where return object is expected
            raise

    async def list_audit_logs(
        self,
        organization_id: UUID,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        actor_user_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditLogListResponse:
        """Fetch paginated audit log events for an organization."""
        # Sanitize limit & offset
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        logs, total = await self.repo.list_by_organization(
            organization_id=organization_id,
            action=action.strip() if action else None,
            resource_type=resource_type.strip() if resource_type else None,
            actor_user_id=actor_user_id,
            limit=safe_limit,
            offset=safe_offset,
        )

        dtos = [AuditLogResponse.model_validate(log) for log in logs]
        return AuditLogListResponse(
            audit_logs=dtos, total=total, limit=safe_limit, offset=safe_offset
        )

    async def get_audit_log_detail(
        self, audit_log_id: UUID, organization_id: UUID
    ) -> AuditLogResponse:
        """Fetch details for a specific audit event enforcing organization boundary."""
        audit_log = await self.repo.get_by_id_and_org(
            audit_log_id=audit_log_id, organization_id=organization_id
        )
        if not audit_log:
            raise ResourceNotFoundException(
                f"AuditLog with ID '{audit_log_id}' was not found"
            )

        return AuditLogResponse.model_validate(audit_log)
