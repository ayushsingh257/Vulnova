"""Security Configuration & Infrastructure Validation Suite Runner Service.

Executes in-memory infrastructure security validation assertions across all 10 INFRA
categories without creating database tables or document archival overhead.
"""

from datetime import datetime, timezone
from typing import List, Set
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.infrastructure_validation.dto import (
    InfrastructureValidationCategoryResultDTO,
    InfrastructureValidationSuiteResponse,
    InfrastructureValidationSummaryDTO,
)
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


class InfrastructureSecurityValidationRunnerService:
    """Service executing in-memory Infrastructure Security Validation Suites."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def run_infrastructure_validation(
        self, current_user: UserModel
    ) -> InfrastructureValidationSuiteResponse:
        """Execute automated Infrastructure Security assertion suite for user's organization."""
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
            action="validation.infrastructure_suite_started",
            resource_type="infrastructure_validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={"suite_id": suite_id},
        )

        # Run 10 INFRA category assertion checks
        cat_results: List[InfrastructureValidationCategoryResultDTO] = [
            self.check_infra1_configuration_management(active_findings),
            self.check_infra2_container_security(active_findings),
            self.check_infra3_supply_chain_security(active_findings),
            self.check_infra4_cicd_security(active_findings),
            self.check_infra5_database_security(active_findings),
            self.check_infra6_logging_monitoring(active_findings),
            self.check_infra7_access_control(active_findings),
            self.check_infra8_network_security(active_findings),
            self.check_infra9_cloud_security(active_findings),
            self.check_infra10_operational_security(active_findings),
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
            action="validation.infrastructure_suite_completed",
            resource_type="infrastructure_validation_suite",
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

        return InfrastructureValidationSuiteResponse(
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
    ) -> InfrastructureValidationSummaryDTO:
        """Return high-level Infrastructure security verification summary for tenant."""
        suite = await self.run_infrastructure_validation(current_user)
        return InfrastructureValidationSummaryDTO(
            organization_id=str(current_user.organization_id),
            last_executed_at=suite.executed_at,
            overall_pass_rate=suite.overall_pass_rate,
            overall_status=suite.overall_status,
            passed_categories=suite.passed_categories,
            failed_categories=suite.failed_categories,
        )

    # ── INFRA Assertion Check Implementations ──

    def check_infra1_configuration_management(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA1 - Secure Configuration Management."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "debug mode",
                    "secret leak",
                    "hardcoded secret",
                    "env exposure",
                    "config default",
                    "plaintext credential",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA1",
            category_name="Secure Configuration Management",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Environment & Application Settings (app/core/config.py)",
            failure_reason=(
                f"Found {failed} configuration management findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Disable debug mode (`DEBUG=False`), store API keys in secrets managers, and enforce environment-variable based configuration defaults.",
        )

    def check_infra2_container_security(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA2 - Container Security Validation."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "docker",
                    "container",
                    "root user",
                    "privileged container",
                    "exposed port",
                    "trivy",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA2",
            category_name="Container Security Validation",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Dockerfile & Docker Compose Runtime",
            failure_reason=(
                f"Found {failed} container security findings." if failed > 0 else None
            ),
            remediation_guidance="Enforce non-root execution (`USER appuser`), run containers without `--privileged` flags, scan base images using Trivy, and expose minimum required ports.",
        )

    def check_infra3_supply_chain_security(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA3 - Dependency & Supply Chain Security."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "supply chain",
                    "outdated package",
                    "vulnerable dependency",
                    "cve",
                    "pip",
                    "npm lockfile",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA3",
            category_name="Dependency & Supply Chain Security",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Dependency Lockfiles (pyproject.toml & package-lock.json)",
            failure_reason=(
                f"Found {failed} supply chain security findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Enforce lockfile integrity, integrate VulnerabilityIntelligenceService for CVE correlation, and automate dependency updates.",
        )

    def check_infra4_cicd_security(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA4 - CI/CD Security Validation."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "cicd",
                    "github action",
                    "pipeline secret",
                    "security gate",
                    "sast",
                    "gitleaks",
                    "semgrep",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA4",
            category_name="CI/CD Security Validation",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="GitHub Actions Pipelines (.github/workflows/*)",
            failure_reason=(
                f"Found {failed} CI/CD security findings." if failed > 0 else None
            ),
            remediation_guidance="Pin all CI/CD GitHub Actions to 40-character commit SHAs, enable secret scanning (Gitleaks) & SAST (Semgrep), and enforce build security gates.",
        )

    def check_infra5_database_security(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA5 - Database Security Validation."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "database",
                    "postgres",
                    "sql injection",
                    "connection string",
                    "backup encryption",
                    "alembic",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA5",
            category_name="Database Security Validation",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="PostgreSQL Database & Alembic Migrations",
            failure_reason=(
                f"Found {failed} database security findings." if failed > 0 else None
            ),
            remediation_guidance="Encrypt database connection strings, enforce parameterized ORM queries via SQLAlchemy, isolate tenant DB access, and encrypt daily physical backups.",
        )

    def check_infra6_logging_monitoring(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA6 - Logging & Monitoring Configuration."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "logging",
                    "audit log",
                    "monitoring",
                    "missing log",
                    "untracked action",
                    "alert webhook",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA6",
            category_name="Logging & Monitoring Configuration",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="AuditLogService & Alert Webhooks (Slack/Teams)",
            failure_reason=(
                f"Found {failed} logging and monitoring findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Ensure `AuditLogService` logs all high-risk events with structured JSON, mask sensitive tokens in logs, and configure real-time Slack/Teams alert channels.",
        )

    def check_infra7_access_control(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA7 - Access Control Infrastructure."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "rbac",
                    "access control",
                    "api key hash",
                    "auth bypass",
                    "privilege escalation",
                    "admin restriction",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA7",
            category_name="Access Control Infrastructure",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="RBAC Control Plane & API Key Verification",
            failure_reason=(
                f"Found {failed} access control infrastructure findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Enforce 4-tier role hierarchy (`OWNER` > `ADMIN` > `ANALYST` > `VIEWER`), hash API keys with SHA-256 (`vn_live_`), and mandate `@require_permission` guards.",
        )

    def check_infra8_network_security(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA8 - Network Security Configuration."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "ssrf",
                    "network egress",
                    "private IP",
                    "dns rebinding",
                    "untrusted host",
                    "firewall",
                ]
            )
        ]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        # Direct test of SSRF Validator rules
        test_safe, _ = is_safe_target_url("https://example.com")
        test_unsafe, _ = is_safe_target_url("http://10.0.0.1/admin")

        network_valid = test_safe and (not test_unsafe)

        total = 5
        failed = len(crit_high) + (0 if network_valid else 1)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else ("WARNING" if failed <= 1 else "FAILED")
        reason = (
            f"Discovered {len(crit_high)} active network security findings or SSRF egress firewall check failed."
            if failed > 0
            else None
        )

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA8",
            category_name="Network Security Configuration",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="SSRFValidator & Network Egress Firewall Filter",
            failure_reason=reason,
            remediation_guidance="Enforce `is_safe_target_url` validation blocking private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.1) and DNS rebinding protections.",
        )

    def check_infra9_cloud_security(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA9 - Cloud Security Configuration."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "aws imds",
                    "cloud metadata",
                    "s3 bucket",
                    "iam credential",
                    "cloud exposure",
                    "instance profile",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA9",
            category_name="Cloud Security Configuration",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Cloud Metadata Firewall & Cloud Credentials",
            failure_reason=(
                f"Found {failed} cloud security configuration findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Block AWS IMDS metadata requests (169.254.169.254), enforce IMDSv2 hop limits, and encrypt cloud storage buckets at rest.",
        )

    def check_infra10_operational_security(
        self, active_findings: List[SecurityFindingModel]
    ) -> InfrastructureValidationCategoryResultDTO:
        """INFRA10 - Operational Security Readiness."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "operational security",
                    "incident response",
                    "security documentation",
                    "remediation workflow",
                    "threat model",
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

        return InfrastructureValidationCategoryResultDTO(
            category_code="INFRA10",
            category_name="Operational Security Readiness",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Security Documentation (SECURITY.md & THREAT_MODEL.md)",
            failure_reason=(
                f"Found {failed} operational security readiness findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Maintain up-to-date threat models (`THREAT_MODEL.md`), publish vulnerability disclosure policies (`SECURITY.md`), and maintain incident response runbooks.",
        )
