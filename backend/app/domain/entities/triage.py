"""Domain entities and value objects for Enterprise Finding Triage & Vulnerability Lifecycle Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class FindingTriageStatus(str, Enum):
    """Lifecycle triage states for security findings."""

    UNREVIEWED = "UNREVIEWED"
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    RISK_ACCEPTED = "RISK_ACCEPTED"
    REMEDIATED = "REMEDIATED"
    REOPENED = "REOPENED"


class SuppressionRuleType(str, Enum):
    """Types of automated finding suppression rules."""

    EXACT_CWE = "EXACT_CWE"
    TARGET_PATTERN = "TARGET_PATTERN"
    PLUGIN_ID = "PLUGIN_ID"
    COMPOSITE = "COMPOSITE"


@dataclass
class FindingTriageRecord:
    """Domain record representing an individual triage decision event."""

    organization_id: UUID
    finding_id: UUID
    new_status: FindingTriageStatus
    id: UUID = field(default_factory=uuid4)
    actor_user_id: Optional[UUID] = None
    previous_status: FindingTriageStatus = FindingTriageStatus.UNREVIEWED
    comment: Optional[str] = None
    risk_accepted_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SuppressionRule:
    """Domain entity representing an automated finding suppression rule."""

    organization_id: UUID
    name: str
    rule_type: SuppressionRuleType
    reason: str
    id: UUID = field(default_factory=uuid4)
    created_by_user_id: Optional[UUID] = None
    plugin_id: Optional[str] = None
    cwe_id: Optional[str] = None
    target_pattern: Optional[str] = None
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
