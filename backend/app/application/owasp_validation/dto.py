"""Data Transfer Objects (DTOs) for OWASP Top 10 (2021) Security Validation Suite."""

from typing import List, Optional

from pydantic import BaseModel, Field


class OWASPCategoryResultDTO(BaseModel):
    """Evaluation result for a single OWASP Top 10 (2021) category."""

    category_code: str = Field(..., description="OWASP Category code e.g. A01:2021")
    category_name: str = Field(
        ..., description="OWASP Category title e.g. Broken Access Control"
    )
    status: str = Field(..., description="PASSED, FAILED, or WARNING")
    pass_rate_percentage: float = Field(
        ..., description="Pass rate percentage 0.0 - 100.0"
    )
    passed_assertions: int
    failed_assertions: int
    total_assertions: int
    finding_count: int
    affected_finding_ids: List[str] = Field(default_factory=list)
    failure_reason: Optional[str] = Field(
        default=None,
        description="Clear diagnostic explanation if status is FAILED or WARNING",
    )
    affected_subsystem: Optional[str] = Field(
        default=None, description="Impacted system component or architectural layer"
    )
    remediation_guidance: str = Field(
        ..., description="Actionable technical steps to resolve violations"
    )


class OWASPValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the OWASP Top 10 (2021) Security Validation Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_pass_rate: float = Field(
        ..., description="Aggregate percentage across all 10 categories"
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[OWASPCategoryResultDTO]


class OWASPVerificationSummaryDTO(BaseModel):
    """High-level health summary metrics for OWASP validation status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_pass_rate: float
    overall_status: str
    passed_categories: int
    failed_categories: int
