"""Data Transfer Objects (DTOs) for Secrets & Cryptographic Management Suite."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SecretCategoryResultDTO(BaseModel):
    """Evaluation result for a single Secrets & Cryptographic Management category."""

    category_code: str = Field(..., description="Secret Category code e.g. SECRET1")
    category_name: str = Field(
        ...,
        description="Secret Category title e.g. Hardcoded Secret & Credential Scanning Audit",
    )
    status: str = Field(..., description="PASSED, FAILED, or WARNING")
    pass_rate_percentage: float = Field(
        ..., description="Pass rate percentage 0.0 - 100.0"
    )
    passed_assertions: int
    failed_assertions: int
    total_assertions: int
    finding_count: int = 0
    affected_secret: Optional[str] = Field(
        default=None, description="Sample secret component or policy evaluated"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation if status is FAILED or WARNING",
    )
    remediation_guidance: str = Field(
        ..., description="Actionable technical steps to remediate secret/crypto risk"
    )


class SecretsValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the Secrets & Cryptographic Management Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_pass_rate: float = Field(
        ..., description="Aggregate percentage across all 10 Secrets categories"
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[SecretCategoryResultDTO]


class SecretsValidationSummaryDTO(BaseModel):
    """High-level health summary metrics for Secrets & Cryptography status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_pass_rate: float
    overall_status: str
    passed_categories: int
    failed_categories: int
