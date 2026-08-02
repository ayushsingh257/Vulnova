"""Data Transfer Objects (DTOs) for Vulnerability Assessment Engine."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class CreateAssessmentRequest(BaseModel):
    """Payload for triggering a security assessment scan."""

    target_url: HttpUrl = Field(
        description="Target web asset URL to scan (must be HTTP/HTTPS)"
    )
    plugins: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific plugin IDs to execute. If omitted, all applicable registered plugins will run.",
    )


class EvidenceArtifactDTO(BaseModel):
    """DTO representing a proof evidence artifact attached to a finding."""

    id: str
    finding_id: str
    artifact_type: str
    storage_path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checksum: str
    created_at: str


class FindingDTO(BaseModel):
    """DTO representing a security finding/vulnerability."""

    id: str
    assessment_job_id: str
    plugin_id: str
    title: str
    description: str
    severity: str
    category: str
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    remediation: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    cvss: Optional[Dict[str, Any]] = None
    epss: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    business_impact: Optional[str] = None
    confidence: Optional[str] = "HIGH"
    is_duplicate: bool = False
    canonical_finding_id: Optional[str] = None
    fix_sla_hours: Optional[int] = None
    evidence_count: int = 0
    evidence_available: bool = False
    artifacts: List[EvidenceArtifactDTO] = Field(default_factory=list)
    created_at: str


class AssessmentJobResponse(BaseModel):
    """Response model for an assessment job run."""

    id: str
    target_url: str
    status: str
    enabled_plugins: List[str] = Field(default_factory=list)
    total_findings: int = 0
    findings: List[FindingDTO] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: str


class PluginMetadataDTO(BaseModel):
    """DTO describing a registered assessment plugin."""

    id: str
    name: str
    version: str
    description: str
    category: str
    author: str
    supported_asset_types: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
