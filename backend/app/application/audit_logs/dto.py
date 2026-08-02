"""Audit Log Data Transfer Objects (DTOs) for Application Services and API Routers."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Public security audit event response model."""

    id: UUID
    organization_id: UUID
    actor_user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Paginated response list wrapper for organization security audit logs."""

    audit_logs: List[AuditLogResponse]
    total: int
    limit: int
    offset: int
