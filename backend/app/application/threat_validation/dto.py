"""Data Transfer Objects (DTOs) for Threat Model Review & STRIDE Verification Suite."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ThreatCategoryResultDTO(BaseModel):
    """Evaluation result for a single STRIDE Threat Model category."""

    category_code: str = Field(..., description="STRIDE Category code e.g. STRIDE1")
    category_name: str = Field(
        ...,
        description="STRIDE Category title e.g. Spoofing: Identity Authentication & Session Guard",
    )
    status: str = Field(..., description="PASSED, FAILED, or WARNING")
    pass_rate_percentage: float = Field(
        ..., description="Pass rate percentage 0.0 - 100.0"
    )
    passed_assertions: int
    failed_assertions: int
    total_assertions: int
    finding_count: int = 0
    affected_component: Optional[str] = Field(
        default=None, description="Sample architectural component or boundary evaluated"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation if status is FAILED or WARNING",
    )
    remediation_guidance: str = Field(
        ..., description="Actionable technical steps to mitigate STRIDE threat vector"
    )


class ThreatValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the Threat Model Review & STRIDE Verification Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_pass_rate: float = Field(
        ..., description="Aggregate percentage across all 10 STRIDE categories"
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[ThreatCategoryResultDTO]


class ThreatValidationSummaryDTO(BaseModel):
    """High-level health summary metrics for Threat Model & STRIDE status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_pass_rate: float
    overall_status: str
    passed_categories: int
    failed_categories: int
