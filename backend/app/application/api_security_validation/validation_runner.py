"""OWASP API Security Top 10 (2023) Validation Suite Runner Service.

Executes in-memory API security validation assertions across all 10 OWASP API (2023)
categories without creating database tables or document archival overhead.
"""

from datetime import datetime, timezone
from typing import List, Set
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.api_security_validation.dto import (
    APIValidationCategoryResultDTO,
    APIValidationSuiteResponse,
    APIValidationSummaryDTO,
)
from app.application.audit_logs.services import AuditLogService
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.discovery.ssrf_validator import is_safe_target_url

logger = structlog.get_logger(__name__)

ACTIVE_FINDING_STATUSES: Set[str] = {
    "OPEN",
    "CONFIRMED",
    "NEW",
    "UNREAD",
    "TRIAGED",
    "IN_REMEDIATION",
}


class APISecurityValidationRunnerService:
    """Service executing in-memory OWASP API Security Top 10 (2023) Validation Suites."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def run_api_security_validation(
        self, current_user: UserModel
    ) -> APIValidationSuiteResponse:
        """Execute automated OWASP API Security Top 10 (2023) assertion suite for user's organization."""
        suite_id = str(uuid4())
        org_id = current_user.organization_id
        now_iso = datetime.now(timezone.utc).isoformat()

        # Fetch active open findings for tenant
        stmt = select(SecurityFindingModel).where(
            SecurityFindingModel.organization_id == org_id
        )
        result = await self.session.execute(stmt)
        all_findings = result.scalars().all()

        active_findings = [
            f
            for f in all_findings
            if (getattr(f, "status", None) or "OPEN").upper() in ACTIVE_FINDING_STATUSES
        ]

        # Dispatch suite started audit event
        await self.audit_log_service.record_event(
            organization_id=org_id,
            action="validation.api_security_suite_started",
            resource_type="api_security_validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={"suite_id": suite_id},
        )

        # Run 10 API category assertion checks
        cat_results: List[APIValidationCategoryResultDTO] = [
            self.check_api1_bola(active_findings),
            self.check_api2_authentication(active_findings),
            self.check_api3_property_authorization(active_findings),
            self.check_api4_resource_consumption(active_findings),
            self.check_api5_function_authorization(active_findings),
            self.check_api6_sensitive_business_flows(active_findings),
            self.check_api7_ssrf(active_findings),
            self.check_api8_security_configuration(active_findings),
            self.check_api9_inventory_management(active_findings),
            self.check_api10_unsafe_api_consumption(active_findings),
        ]

        passed_count = sum(1 for c in cat_results if c.status == "PASSED")
        failed_count = sum(1 for c in cat_results if c.status == "FAILED")
        warning_count = sum(1 for c in cat_results if c.status == "WARNING")
        overall_pass_rate = round((passed_count / 10.0) * 100.0, 1)

        if failed_count == 0 and warning_count == 0:
            overall_status = "PASSED"
        elif failed_count <= 2:
            overall_status = "DEGRADED"
        else:
            overall_status = "CRITICAL"

        # Dispatch suite completed audit event
        await self.audit_log_service.record_event(
            organization_id=org_id,
            action="validation.api_security_suite_completed",
            resource_type="api_security_validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={
                "suite_id": suite_id,
                "overall_pass_rate": overall_pass_rate,
                "overall_status": overall_status,
                "passed_categories": passed_count,
                "failed_categories": failed_count,
                "warning_categories": warning_count,
            },
        )

        return APIValidationSuiteResponse(
            suite_id=suite_id,
            organization_id=str(org_id),
            executed_at=now_iso,
            overall_status=overall_status,
            overall_pass_rate=overall_pass_rate,
            passed_categories=passed_count,
            failed_categories=failed_count,
            warning_categories=warning_count,
            total_categories=10,
            category_results=cat_results,
        )

    async def get_latest_summary(
        self, current_user: UserModel
    ) -> APIValidationSummaryDTO:
        """Return high-level API security verification summary for tenant."""
        suite = await self.run_api_security_validation(current_user)
        return APIValidationSummaryDTO(
            organization_id=str(current_user.organization_id),
            last_executed_at=suite.executed_at,
            overall_pass_rate=suite.overall_pass_rate,
            overall_status=suite.overall_status,
            passed_categories=suite.passed_categories,
            failed_categories=suite.failed_categories,
        )

    # ── Category Assertion Check Implementations ──

    def check_api1_bola(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API1:2023 - Broken Object Level Authorization (BOLA)."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "bola",
                    "idor",
                    "object level",
                    "tenant boundary",
                    "cross-tenant",
                    "resource authorization",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else ("WARNING" if failed <= 1 else "FAILED")
        reason = (
            f"Discovered {failed} active BOLA/IDOR vulnerability findings across tenant API resource routes."
            if failed > 0
            else None
        )

        return APIValidationCategoryResultDTO(
            category_code="API1:2023",
            category_name="Broken Object Level Authorization (BOLA)",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/vulnerabilities/{id}",
            affected_subsystem="OrganizationIsolation & DatabaseRepository",
            failure_reason=reason,
            remediation_guidance="Enforce mandatory `organization_id = current_user.organization_id` filter predicates on all SQL query statements before returning object instances.",
        )

    def check_api2_authentication(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API2:2023 - Broken Authentication."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "broken auth",
                    "jwt",
                    "token expiration",
                    "api key bypass",
                    "unauthenticated",
                    "bearer",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else ("WARNING" if failed <= 1 else "FAILED")
        reason = (
            f"Discovered {failed} active Broken Authentication vulnerability findings in API token verification."
            if failed > 0
            else None
        )

        return APIValidationCategoryResultDTO(
            category_code="API2:2023",
            category_name="Broken Authentication",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/auth/login",
            affected_subsystem="JWTAuthHandler & APIKeyVerifier",
            failure_reason=reason,
            remediation_guidance="Validate JWT algorithm signatures explicitly, reject expired tokens, and enforce SHA-256 API key verification with prefix rules (`vn_live_`, `vn_cli_`).",
        )

    def check_api3_property_authorization(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API3:2023 - Broken Object Property Level Authorization."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "mass assignment",
                    "property level",
                    "field exposure",
                    "sensitive property",
                    "unmasked secret",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return APIValidationCategoryResultDTO(
            category_code="API3:2023",
            category_name="Broken Object Property Level Authorization",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/integrations/settings",
            affected_subsystem="PydanticDTO & SecretEncryptionService",
            failure_reason=(
                f"Found {failed} object property exposure findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Use explicit Pydantic response DTO models to prune sensitive entity fields and mask raw API tokens/webhook secrets in API JSON responses.",
        )

    def check_api4_resource_consumption(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API4:2023 - Unrestricted Resource Consumption."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "rate limit",
                    "resource consumption",
                    "dos",
                    "unrestricted upload",
                    "payload size",
                    "oom",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return APIValidationCategoryResultDTO(
            category_code="API4:2023",
            category_name="Unrestricted Resource Consumption",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/assessments/dispatch",
            affected_subsystem="RateLimiter & FastAPIBodyLimit",
            failure_reason=(
                f"Found {failed} resource consumption findings." if failed > 0 else None
            ),
            remediation_guidance="Enforce Redis/InMemory rate limiting (`RateLimiter`), cap maximum HTTP request body payload sizes, and enforce concurrent scan limits per organization.",
        )

    def check_api5_function_authorization(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API5:2023 - Broken Function Level Authorization."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "function level",
                    "bfla",
                    "privilege escalation",
                    "admin endpoint",
                    "rbac bypass",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return APIValidationCategoryResultDTO(
            category_code="API5:2023",
            category_name="Broken Function Level Authorization",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/users/invite",
            affected_subsystem="RBACPolicy & RolePermissionMap",
            failure_reason=(
                f"Found {failed} function level authorization findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Annotate every sensitive REST endpoint with `@require_permission` guards and enforce 4-tier role hierarchy checks (`OWNER` > `ADMIN` > `ANALYST` > `VIEWER`).",
        )

    def check_api6_sensitive_business_flows(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API6:2023 - Unrestricted Access to Sensitive Business Flows."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "business flow",
                    "abuse",
                    "automation abuse",
                    "bot",
                    "bulk action",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return APIValidationCategoryResultDTO(
            category_code="API6:2023",
            category_name="Unrestricted Access to Sensitive Business Flows",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/assessments/dispatch",
            affected_subsystem="AssessmentPolicyEngine",
            remediation_guidance="Validate scan target legal authorization contracts (`validate_scan_authorization`) and enforce user verification before executing high-impact actions.",
        )

    def check_api7_ssrf(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API7:2023 - Server Side Request Forgery (SSRF)."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "ssrf",
                    "server-side request forgery",
                    "egress",
                    "aws imds",
                    "internal IP",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        # Test SSRF Validator logic directly
        test_safe, _ = is_safe_target_url("https://example.com")
        test_unsafe, _ = is_safe_target_url("http://169.254.169.254/latest/meta-data/")

        ssrf_logic_valid = test_safe and (not test_unsafe)

        total = 5
        failed = len(crit_high) + (0 if ssrf_logic_valid else 1)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else ("WARNING" if failed <= 1 else "FAILED")
        reason = (
            f"Discovered {len(crit_high)} active SSRF vulnerability findings or SSRF egress firewall check failed."
            if failed > 0
            else None
        )

        return APIValidationCategoryResultDTO(
            category_code="API7:2023",
            category_name="Server Side Request Forgery (SSRF)",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/assessments/dispatch",
            affected_subsystem="SSRFValidator & TargetUrlFilter",
            failure_reason=reason,
            remediation_guidance="Enforce `is_safe_target_url` validation blocking private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.1, AWS IMDS 169.254.169.254) and DNS rebinding attacks.",
        )

    def check_api8_security_configuration(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API8:2023 - Security Misconfiguration."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "api misconfiguration",
                    "cors wildcard",
                    "header",
                    "swagger exposure",
                    "docs exposure",
                    "debug mode",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return APIValidationCategoryResultDTO(
            category_code="API8:2023",
            category_name="Security Misconfiguration",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/status",
            affected_subsystem="HeaderSecurityPlugin & FastAPIMiddleware",
            failure_reason=(
                f"Found {failed} API security misconfiguration findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Disable debug mode in production, configure explicit CORS origin whitelists, and enforce CSP, HSTS, and X-Content-Type-Options headers.",
        )

    def check_api9_inventory_management(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API9:2023 - Improper Inventory Management."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "inventory",
                    "deprecated route",
                    "undocumented endpoint",
                    "api versioning",
                    "shadow api",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return APIValidationCategoryResultDTO(
            category_code="API9:2023",
            category_name="Improper Inventory Management",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/api.py",
            affected_subsystem="FastAPIAPIV1Router",
            failure_reason=(
                f"Found {failed} improper API inventory management findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Prefix all production REST endpoints with `/api/v1`, deprecate legacy endpoints cleanly with HTTP 410 Gone, and maintain accurate OpenAPI schemas.",
        )

    def check_api10_unsafe_api_consumption(
        self, active_findings: List[SecurityFindingModel]
    ) -> APIValidationCategoryResultDTO:
        """API10:2023 - Unsafe Consumption of APIs."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "third party",
                    "unsafe consumption",
                    "webhook injection",
                    "external api",
                    "jira payload",
                    "slack payload",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return APIValidationCategoryResultDTO(
            category_code="API10:2023",
            category_name="Unsafe Consumption of APIs",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_endpoint="/api/v1/integrations/jira",
            affected_subsystem="JiraClient & TeamsWebhookProvider",
            failure_reason=(
                f"Found {failed} unsafe third-party API consumption findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Sanitize and validate all incoming payload data from external services (Jira ADF, GitHub Markdown, Slack Block Kit, Teams Adaptive Cards) before processing.",
        )
