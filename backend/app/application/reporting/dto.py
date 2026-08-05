"""Data Transfer Objects (DTOs) for Executive Security Reporting Engine."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.application.assessment.dto import (
    AttackSurfaceCoverageResponse,
    ExecutiveThreatAlertDTO,
    HistoricalRiskTrendResponse,
    SecurityPostureSummaryDTO,
    VulnerabilitySeverityBreakdownDTO,
)


class CreateExecutiveReportRequest(BaseModel):
    """Payload for requesting on-demand executive security report generation."""

    title: Optional[str] = Field(
        default="CISO Executive Security Posture Report",
        description="Report title string displayed on cover page and headers.",
    )
    timeframe_days: int = Field(
        default=30,
        ge=7,
        le=365,
        description="Historical analysis window in days (7, 30, 90, 365). Defaults to 30.",
    )
    include_sections: Optional[List[str]] = Field(
        default=None,
        description="Optional list of section identifiers to include ('summary', 'posture', 'vulnerabilities', 'attack_surface', 'advisories').",
    )


class ExecutiveReportMetadataResponse(BaseModel):
    """Metadata response DTO for generated executive reports."""

    id: str = Field(description="Unique report identifier UUID string.")
    organization_id: str = Field(description="Tenant organization ID UUID.")
    title: str = Field(description="Report title.")
    generated_at: str = Field(description="ISO-8601 UTC timestamp of report creation.")
    posture_score: float = Field(
        description="Overall platform composite risk posture score (0-100)."
    )
    posture_status: str = Field(
        description="Posture risk classification: SECURE, ELEVATED_RISK, CRITICAL_RISK."
    )
    total_findings: int = Field(description="Total open findings count.")
    critical_findings: int = Field(
        description="Total open critical severity findings count."
    )
    high_findings: int = Field(description="Total open high severity findings count.")
    available_formats: List[str] = Field(
        default_factory=lambda: ["pdf", "html", "json", "csv"],
        description="Supported report export formats.",
    )


class TopVulnerabilityReportDTO(BaseModel):
    """DTO representing a top critical security finding included in executive report."""

    id: str
    title: str
    severity: str
    category: str
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: float = 0.0
    epss_score: float = 0.0
    target_name: Optional[str] = None
    created_at: str


class ExecutiveReportDataPayload(BaseModel):
    """Consolidated payload containing all aggregated security metrics for report rendering."""

    metadata: ExecutiveReportMetadataResponse
    posture_summary: SecurityPostureSummaryDTO
    historical_trends: HistoricalRiskTrendResponse
    attack_surface_coverage: AttackSurfaceCoverageResponse
    vulnerability_breakdown: VulnerabilitySeverityBreakdownDTO
    top_findings: List[TopVulnerabilityReportDTO] = Field(default_factory=list)
    threat_advisories: List[ExecutiveThreatAlertDTO] = Field(default_factory=list)
    data_sources: List[str] = Field(
        default_factory=lambda: [
            "Vulnova Posture Engine",
            "Vulnova Finding Intelligence",
            "Vulnova Threat Advisory Engine",
            "Vulnova Asset Inventory",
        ]
    )
