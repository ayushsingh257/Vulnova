"""Data Transfer Objects (DTOs) for Automated Security Regression Testing Framework."""

from typing import List, Optional

from pydantic import BaseModel, Field


class RegressionCategoryResultDTO(BaseModel):
    """Evaluation result for a single Security Regression category."""

    category_code: str = Field(
        ..., description="Regression category code e.g. REGRESSION1"
    )
    category_name: str = Field(
        ...,
        description="Regression category title e.g. OWASP Web Top 10 Regression Guard",
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
        default=None, description="Platform security area or module evaluated"
    )
    failure_reason: Optional[str] = Field(
        default=None, description="Diagnostic explanation if regression is detected"
    )
    remediation_guidance: str = Field(
        ..., description="Actionable technical steps to fix regression"
    )


class RegressionValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the Automated Security Regression Testing Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_pass_rate: float = Field(
        ...,
        description="Aggregate percentage across all 10 Security Regression categories",
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[RegressionCategoryResultDTO]


class RegressionValidationSummaryDTO(BaseModel):
    """High-level health summary metrics for Security Regression status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_pass_rate: float
    overall_status: str
    passed_categories: int
    failed_categories: int
