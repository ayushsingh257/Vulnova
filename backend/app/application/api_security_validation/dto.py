"""Data Transfer Objects (DTOs) for OWASP API Security Top 10 (2023) Validation Suite."""

from typing import List, Optional

from pydantic import BaseModel, Field


class APIValidationCategoryResultDTO(BaseModel):
    """Evaluation result for a single OWASP API Security Top 10 (2023) category."""

    category_code: str = Field(
        ..., description="OWASP API Category code e.g. API1:2023"
    )
    category_name: str = Field(
        ...,
        description="OWASP API Category title e.g. Broken Object Level Authorization",
    )
    status: str = Field(..., description="PASSED, FAILED, or WARNING")
    pass_rate_percentage: float = Field(
        ..., description="Pass rate percentage 0.0 - 100.0"
    )
    passed_assertions: int
    failed_assertions: int
    total_assertions: int
    finding_count: int
    affected_endpoint: Optional[str] = Field(
        default=None,
        description="Sample API route impacted by security policy violation",
    )
    affected_subsystem: Optional[str] = Field(
        default=None, description="Impacted system component or security layer"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation if status is FAILED or WARNING",
    )
    remediation_guidance: str = Field(
        ..., description="Actionable technical steps to resolve API security risk"
    )


class APIValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the OWASP API Security Top 10 (2023) Validation Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_pass_rate: float = Field(
        ..., description="Aggregate percentage across all 10 API categories"
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[APIValidationCategoryResultDTO]


class APIValidationSummaryDTO(BaseModel):
    """High-level health summary metrics for API Security validation status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_pass_rate: float
    overall_status: str
    passed_categories: int
    failed_categories: int
