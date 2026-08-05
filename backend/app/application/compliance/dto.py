"""Data Transfer Objects (DTOs) for Compliance Intelligence & Framework Mapping."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ComplianceFindingMappingDTO(BaseModel):
    """Traceable finding reference mapped to a specific compliance control."""

    finding_id: str
    title: str
    severity: str
    category: str
    cwe_id: Optional[str] = None
    cve_id: Optional[str] = None
    status: str
    asset_name: Optional[str] = None
    evidence_checksum: Optional[str] = None
    remediation_summary: Optional[str] = None


class ComplianceControlDTO(BaseModel):
    """Detailed compliance control status and mapped finding evidence."""

    control_id: str
    title: str
    description: str
    status: str = Field(..., description="PASS or FAIL status")
    mapped_findings_count: int = 0
    affected_findings: List[ComplianceFindingMappingDTO] = Field(default_factory=list)
    remediation_guidance: str = ""


class ComplianceFrameworkDTO(BaseModel):
    """Compliance framework metadata."""

    id: str
    name: str
    version: str
    description: str
    total_controls: int


class ComplianceScoreResponse(BaseModel):
    """Computed compliance posture score."""

    framework_id: str
    framework_name: str
    framework_version: str
    total_controls: int
    passed_controls: int
    failed_controls: int
    compliance_percentage: float


class ComplianceOverviewResponse(BaseModel):
    """Full compliance overview payload including score, controls, and top failed controls."""

    framework_id: str
    framework_name: str
    framework_version: str
    score: ComplianceScoreResponse
    controls: List[ComplianceControlDTO]
    failed_controls: List[ComplianceControlDTO]
    top_remediation_priorities: List[Dict[str, Any]] = Field(default_factory=list)
