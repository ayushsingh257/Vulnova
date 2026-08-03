"""Data Transfer Objects (DTOs) for Vulnerability Assessment Engine."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ScanPolicyDTO(BaseModel):
    """DTO representing an execution policy configuration."""

    concurrency_limit: int = 5
    rate_limit_rps: int = 10
    respect_robots_txt: bool = True
    scope_include_patterns: List[str] = Field(default_factory=list)
    scope_exclude_patterns: List[str] = Field(default_factory=list)
    max_crawl_depth: int = 3
    max_requests: int = 500
    timeout_seconds: float = 30.0
    stop_on_critical: bool = False


class ScanProfileDTO(BaseModel):
    """DTO describing an enterprise scan profile."""

    id: str
    name: str
    description: str
    plugin_ids: List[str] = Field(default_factory=list)
    default_policy: ScanPolicyDTO


class CreateAssessmentRequest(BaseModel):
    """Payload for triggering a security assessment scan."""

    target_url: HttpUrl = Field(
        description="Target web asset URL to scan (must be HTTP/HTTPS)"
    )
    profile_id: Optional[str] = Field(
        default="full_assessment",
        description="Enterprise scan profile ID (e.g. 'web_scan', 'api_scan', 'full_assessment'). Defaults to 'full_assessment'.",
    )
    plugins: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific plugin IDs to execute. Used when profile_id is 'custom_scan' or to override profile default plugins.",
    )
    policy_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional execution policy overrides (concurrency_limit, rate_limit_rps, auth_headers, auth_cookies, scope_exclude_patterns, etc.)",
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
    profile_id: str = "full_assessment"
    enabled_plugins: List[str] = Field(default_factory=list)
    policy: Optional[ScanPolicyDTO] = None
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


class AssetInventoryDTO(BaseModel):
    """DTO representing high-level enterprise asset inventory posture."""

    id: str
    node_type: str
    name: str
    value: str
    risk_score: float = 0.0
    risk_level: str = "LOW"
    total_findings: int = 0
    findings_by_severity: Dict[str, int] = Field(default_factory=dict)
    technologies: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class AssetInventoryResponse(BaseModel):
    """Paginated response model for enterprise asset inventory posture."""

    total: int
    items: List[AssetInventoryDTO] = Field(default_factory=list)


class AssetDetailResponse(BaseModel):
    """Detailed response model for a single enterprise asset."""

    asset: AssetInventoryDTO
    technologies: List[Dict[str, Any]] = Field(default_factory=list)
    findings: List[FindingDTO] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
