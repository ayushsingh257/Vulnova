"""Data Transfer Objects for Security Incident Response, Escalations, Forensics, and PIR."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentSeverity(str, Enum):
    """Incident Severity Classification Tier."""

    SEV_1 = "SEV-1"  # Critical - Active breach, Data compromise
    SEV_2 = "SEV-2"  # High - Major vulnerability, Privilege escalation
    SEV_3 = "SEV-3"  # Medium - Limited impact, Policy violation
    SEV_4 = "SEV-4"  # Low - Informational, Minor anomaly


class IncidentStatus(str, Enum):
    """Incident Lifecycle State."""

    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    CONTAINED = "CONTAINED"
    INVESTIGATING = "INVESTIGATING"
    ERADICATED = "ERADICATED"
    RECOVERED = "RECOVERED"
    CLOSED = "CLOSED"


class IncidentLifecyclePhase(str, Enum):
    """7-Phase Incident Lifecycle."""

    DETECTION = "DETECTION"
    TRIAGE = "TRIAGE"
    CONTAINMENT = "CONTAINMENT"
    INVESTIGATION = "INVESTIGATION"
    ERADICATION = "ERADICATION"
    RECOVERY = "RECOVERY"
    POST_INCIDENT_REVIEW = "POST_INCIDENT_REVIEW"


class IncidentSeverityDTO(BaseModel):
    """Severity breakdown metadata."""

    severity: IncidentSeverity
    description: str
    target_mtta_minutes: int
    target_mttc_minutes: int
    target_mttr_minutes: int
    channels: List[str]


class IncidentTimelineDTO(BaseModel):
    """Timeline event representing lifecycle progression and containment actions."""

    id: UUID
    incident_id: UUID
    phase: str
    action: str
    description: str
    actor_id: Optional[UUID] = None
    audit_log_id: Optional[UUID] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class EscalationEventDTO(BaseModel):
    """Escalation dispatch record for notification channels."""

    id: UUID
    incident_id: UUID
    severity: str
    channels: List[str]
    status: str
    notification_status: Dict[str, Any] = Field(default_factory=dict)
    triggered_by: Optional[UUID] = None
    triggered_at: datetime
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class PostIncidentReviewDTO(BaseModel):
    """Post-Incident Review analysis, root cause, and remediation plan."""

    id: UUID
    incident_id: UUID
    summary: str
    root_cause: str
    impact_assessment: str
    timeline_summary: str
    lessons_learned: List[str] = Field(default_factory=list)
    action_items: List[Dict[str, Any]] = Field(default_factory=list)
    author_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentDurationMetricsDTO(BaseModel):
    """Calculated duration metrics across the incident response lifecycle."""

    mtta_minutes: Optional[float] = None
    mttc_minutes: Optional[float] = None
    mttr_minutes: Optional[float] = None
    total_duration_hours: Optional[float] = None
    sla_met: bool = True


class IncidentResponseDTO(BaseModel):
    """Detailed security incident response payload."""

    id: UUID
    organization_id: UUID
    title: str
    description: str
    severity: str
    status: str
    lead_investigator_id: Optional[UUID] = None
    affected_services: List[str] = Field(default_factory=list)
    indicators_of_compromise: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime
    contained_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    timelines: List[IncidentTimelineDTO] = Field(default_factory=list)
    escalations: List[EscalationEventDTO] = Field(default_factory=list)
    post_incident_review: Optional[PostIncidentReviewDTO] = None
    duration_metrics: Optional[IncidentDurationMetricsDTO] = None

    model_config = {"from_attributes": True}


class IncidentListResponseDTO(BaseModel):
    """Paginated list of security incidents."""

    incidents: List[IncidentResponseDTO]
    total: int
    limit: int
    offset: int


class IncidentStatusDTO(BaseModel):
    """High-level incident response posture status summary."""

    total_active_incidents: int
    sev1_critical_count: int
    sev2_high_count: int
    sev3_medium_count: int
    sev4_low_count: int
    contained_count: int
    mean_time_to_contain_minutes: float
    mean_time_to_resolve_minutes: float
    status: str = "HEALTHY"


class CreateIncidentRequestDTO(BaseModel):
    """Payload for declaring a new security incident."""

    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    severity: IncidentSeverity = Field(default=IncidentSeverity.SEV_3)
    lead_investigator_id: Optional[UUID] = None
    affected_services: List[str] = Field(default_factory=list)
    indicators_of_compromise: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class UpdateIncidentStateRequestDTO(BaseModel):
    """Payload for transitioning incident lifecycle state."""

    status: IncidentStatus
    note: Optional[str] = None
    lead_investigator_id: Optional[UUID] = None
    affected_services: Optional[List[str]] = None
    indicators_of_compromise: Optional[List[str]] = None
    details: Optional[Dict[str, Any]] = None


class TriggerEscalationRequestDTO(BaseModel):
    """Payload for triggering manual or automated alert escalation."""

    channels: Optional[List[str]] = None
    reason: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class CreatePIRRequestDTO(BaseModel):
    """Payload for creating or updating a Post-Incident Review."""

    summary: str = Field(..., min_length=10)
    root_cause: str = Field(..., min_length=10)
    impact_assessment: str = Field(..., min_length=10)
    timeline_summary: str = Field(..., min_length=10)
    lessons_learned: List[str] = Field(default_factory=list)
    action_items: List[Dict[str, Any]] = Field(default_factory=list)


class ForensicCorrelatedEventDTO(BaseModel):
    """Correlated audit event cluster for forensic investigation."""

    correlation_key: str
    event_count: int
    actions: List[str]
    actor_user_ids: List[UUID] = Field(default_factory=list)
    client_ips: List[str] = Field(default_factory=list)
    first_seen: datetime
    last_seen: datetime
    risk_level: str
    description: str


class ForensicInvestigationResultDTO(BaseModel):
    """Complete forensic audit trail package with cryptographic digest."""

    incident_id: UUID
    organization_id: UUID
    investigation_timestamp: datetime
    total_events_analyzed: int
    correlated_clusters: List[ForensicCorrelatedEventDTO]
    suspicious_ips: List[str]
    affected_actors: List[UUID]
    forensic_integrity_sha256: str
    summary: str
