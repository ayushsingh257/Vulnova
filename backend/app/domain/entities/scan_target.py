"""Domain entities and value objects for Phase 6.2 Target Scan Configuration & Authorized Assessment Contract."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class TargetEnvironment(str, Enum):
    """Deployment environment classification of a scan target."""

    PRODUCTION = "PRODUCTION"
    STAGING = "STAGING"
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"


class TargetStatus(str, Enum):
    """Lifecycle status of a registered scan target."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    SUSPENDED = "SUSPENDED"


class AuthorizationScope(str, Enum):
    """Scope of the authorized security assessment declaration."""

    FULL = "full"
    PASSIVE_ONLY = "passive_only"
    CUSTOM = "custom"


@dataclass
class ScanTarget:
    """Domain model representing a registered scan target within an organization."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    name: str = ""
    target_url: str = ""
    environment: TargetEnvironment = TargetEnvironment.PRODUCTION
    status: TargetStatus = TargetStatus.ACTIVE
    is_ownership_verified: bool = False
    ownership_verification_token: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AuthorizedAssessmentContract:
    """Value object representing a user's legal consent declaration to scan a registered target.

    Every authorization consent event is persisted as an immutable audit record.
    This ensures regulatory compliance and traceability for security assessment activities.
    """

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    scan_target_id: UUID = field(default_factory=uuid4)
    declared_by: UUID = field(default_factory=uuid4)
    is_authorized: bool = False
    authorization_scope: AuthorizationScope = AuthorizationScope.FULL
    ip_address: Optional[str] = None
    declared_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
