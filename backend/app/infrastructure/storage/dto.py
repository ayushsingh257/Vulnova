"""Data Transfer Objects (DTOs) for Evidence Antivirus & Malware Protection Pipeline (Phase 12.9)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidenceScanResultDTO(BaseModel):
    """DTO representing evidence malware inspection status and scan details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    evidence_id: UUID
    finding_id: Optional[UUID] = None
    filename: str
    scan_status: str
    clamav_result: Dict[str, Any] = Field(default_factory=dict)
    yara_result: Dict[str, Any] = Field(default_factory=dict)
    detected_family: Optional[str] = None
    severity: Optional[str] = "NONE"
    quarantine_location: Optional[str] = None
    production_location: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MalwareDetectionEventDTO(BaseModel):
    """DTO representing security alerts triggered by ClamAV or YARA rules."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    scan_id: UUID
    rule_name: str
    engine: str
    severity: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class EvidenceUploadResponseDTO(BaseModel):
    """DTO response returned after staging evidence in quarantine and initiating malware scan."""

    evidence_id: UUID
    scan_id: UUID
    filename: str
    status: str
    message: str
    quarantine_path: str


class EvidenceSecurityStatusDTO(BaseModel):
    """DTO returning security verification state, scanner verdicts, and promotion readiness."""

    evidence_id: UUID
    scan_id: UUID
    filename: str
    scan_status: str
    is_clean: bool
    can_promote: bool
    clamav: Dict[str, Any]
    yara: Dict[str, Any]
    detected_family: Optional[str] = None
    severity: str
    quarantine_location: Optional[str] = None
    production_location: Optional[str] = None


class QuarantineDashboardSummaryDTO(BaseModel):
    """DTO summarizing quarantine telemetry metrics for SOC administrator view."""

    total_scanned: int
    clean_count: int
    quarantined_count: int
    malware_detected_count: int
    failed_scan_count: int
    active_threats: List[MalwareDetectionEventDTO] = Field(default_factory=list)
