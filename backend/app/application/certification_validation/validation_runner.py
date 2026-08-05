"""Security Control Plane Final Certification Runner Service.

Executes in-memory security certification assertions across all 10 Security Control Plane
domains completed during Era 10 without creating database tables or document archival overhead.
"""

from datetime import datetime, timezone
from typing import List, Set
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.certification_validation.dto import (
    CertificationCategoryResultDTO,
    CertificationValidationSuiteResponse,
    CertificationValidationSummaryDTO,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)

ACTIVE_FINDING_STATUSES: Set[str] = {
    "OPEN",
    "CONFIRMED",
    "NEW",
    "UNREAD",
    "TRIAGED",
    "IN_REMEDIATION",
}


class CertificationValidationRunnerService:
    """Service executing in-memory Security Control Plane Final Certification Suites."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def run_certification_validation(
        self, current_user: UserModel
    ) -> CertificationValidationSuiteResponse:
        """Execute automated Security Control Plane Final Certification suite for user's organization."""
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
            action="validation.certification_suite_started",
            resource_type="certification_validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={"suite_id": suite_id},
        )

        # Run 10 Security Control Plane certification assertion checks
        cat_results: List[CertificationCategoryResultDTO] = [
            self.check_certification1_owasp_controls(active_findings),
            self.check_certification2_infrastructure_controls(active_findings),
            self.check_certification3_pentest_readiness(active_findings),
            self.check_certification4_supply_chain_controls(active_findings),
            self.check_certification5_container_controls(active_findings),
            self.check_certification6_crypto_controls(active_findings),
            self.check_certification7_stride_controls(active_findings),
            self.check_certification8_regression_controls(active_findings),
            self.check_certification9_governance_controls(active_findings),
            self.check_certification10_compliance_readiness(active_findings),
        ]

        passed_count = sum(1 for c in cat_results if c.status == "PASSED")
        failed_count = sum(1 for c in cat_results if c.status == "FAILED")
        warning_count = sum(1 for c in cat_results if c.status == "WARNING")
        overall_score = round((passed_count / 10.0) * 100.0, 1)

        if failed_count == 0 and warning_count == 0:
            overall_status = "PASSED"
        elif failed_count <= 2:
            overall_status = "DEGRADED"
        else:
            overall_status = "CRITICAL"

        # Dispatch suite completed audit event
        await self.audit_log_service.record_event(
            organization_id=org_id,
            action="validation.certification_suite_completed",
            resource_type="certification_validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={
                "suite_id": suite_id,
                "overall_certification_score": overall_score,
                "overall_status": overall_status,
                "passed_categories": passed_count,
                "failed_categories": failed_count,
                "warning_categories": warning_count,
            },
        )

        return CertificationValidationSuiteResponse(
            suite_id=suite_id,
            organization_id=str(org_id),
            executed_at=now_iso,
            overall_status=overall_status,
            overall_certification_score=overall_score,
            passed_categories=passed_count,
            failed_categories=failed_count,
            warning_categories=warning_count,
            total_categories=10,
            category_results=cat_results,
        )

    async def get_latest_summary(
        self, current_user: UserModel
    ) -> CertificationValidationSummaryDTO:
        """Return high-level Security Certification summary for tenant."""
        suite = await self.run_certification_validation(current_user)
        return CertificationValidationSummaryDTO(
            organization_id=str(current_user.organization_id),
            last_executed_at=suite.executed_at,
            overall_certification_score=suite.overall_certification_score,
            overall_status=suite.overall_status,
            passed_categories=suite.passed_categories,
            failed_categories=suite.failed_categories,
        )

    # ── Security Control Plane Certification Check Implementations ──

    def check_certification1_owasp_controls(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION1 - OWASP Security Control Plane Certification."""
        unresolved_crit = [
            f
            for f in active_findings
            if (f.severity or "").upper() == "CRITICAL"
            and any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in ["owasp", "sqli", "xss", "ssrf", "bola", "bfla"]
            )
        ]

        total = 5
        failed = len(unresolved_crit)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION1",
            category_name="OWASP Security Control Plane Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="OWASP Web Top 10 & API Security Top 10 Validation Engines",
            failure_reason=(
                f"Found {failed} unresolved critical OWASP vulnerabilities blocking certification."
                if failed > 0
                else None
            ),
            remediation_guidance="Resolve all active critical OWASP Web and API findings and verify OWASPValidationRunnerService execution status.",
        )

    def check_certification2_infrastructure_controls(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION2 - Infrastructure & Configuration Certification."""
        infra_failures = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower()
                for k in [
                    "missing security header",
                    "cors wildcard",
                    "debug mode",
                    "exposed admin port",
                ]
            )
        ]

        total = 5
        failed = len(infra_failures)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION2",
            category_name="Infrastructure & Configuration Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="Security Middleware, Response Headers & Deployment Hardening",
            failure_reason=(
                f"Found {failed} infrastructure configuration issues blocking certification."
                if failed > 0
                else None
            ),
            remediation_guidance="Verify strict HSTS/CSP headers, restrict CORS origins to whitelisted domains, and ensure `DEBUG=False` in production.",
        )

    def check_certification3_pentest_readiness(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION3 - Penetration Testing Readiness Certification."""
        exploit_issues = [
            f
            for f in active_findings
            if (f.severity or "").upper() in ("CRITICAL", "HIGH")
            and any(
                k in (f.title or "").lower()
                for k in [
                    "exploit",
                    "path traversal",
                    "command injection",
                    "unauthorized access",
                ]
            )
        ]

        total = 5
        failed = len(exploit_issues)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION3",
            category_name="Penetration Testing Readiness Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="Exploit Verification Engine & Attack Surface Validation Suite",
            failure_reason=(
                f"Found {failed} exploitable security findings affecting penetration test readiness."
                if failed > 0
                else None
            ),
            remediation_guidance="Execute `PenTestValidationRunnerService` to verify all simulated exploit vectors remain blocked.",
        )

    def check_certification4_supply_chain_controls(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION4 - Dependency & Supply Chain Certification."""
        cve_findings = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in ["cve-", "vulnerable package", "license violation", "lockfile"]
            )
        ]

        total = 5
        failed = len(cve_findings)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION4",
            category_name="Dependency & Supply Chain Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="SCA Package Scanner, Lockfile Integrity & License Policy",
            failure_reason=(
                f"Found {failed} active supply chain dependency vulnerabilities."
                if failed > 0
                else None
            ),
            remediation_guidance="Update vulnerable third-party packages, verify cryptographic pins (`==`) in lockfiles, and run `SCAValidationRunnerService`.",
        )

    def check_certification5_container_controls(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION5 - Container Security Certification."""
        container_issues = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower()
                for k in [
                    "root container",
                    "privileged mode",
                    "missing cap_drop",
                    "container escape",
                ]
            )
        ]

        total = 5
        failed = len(container_issues)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION5",
            category_name="Container Security Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="Container Hardening, Unprivileged Execution & Capability Dropping",
            failure_reason=(
                f"Found {failed} container runtime hardening defects."
                if failed > 0
                else None
            ),
            remediation_guidance="Set `USER appuser` in Dockerfiles, apply `cap_drop: [ALL]`, enforce resource limits, and pin base image digests.",
        )

    def check_certification6_crypto_controls(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION6 - Secrets & Cryptographic Certification."""
        crypto_issues = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower()
                for k in [
                    "hardcoded secret",
                    "weak jwt",
                    "unencrypted field",
                    "weak key",
                ]
            )
        ]

        total = 5
        failed = len(crypto_issues)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION6",
            category_name="Secrets & Cryptographic Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="CryptoService AES-256-GCM Envelope Encryption & SHA-256 Key Hashing",
            failure_reason=(
                f"Found {failed} cryptographic security or secrets scanning defects."
                if failed > 0
                else None
            ),
            remediation_guidance="Scrutinize codebase with Gitleaks, ensure 256-bit JWT secret entropy, and verify `CryptoService` AES-256-GCM field encryption.",
        )

    def check_certification7_stride_controls(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION7 - Threat Model & STRIDE Certification."""
        stride_issues = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower()
                for k in [
                    "spoofing",
                    "tampering",
                    "information disclosure",
                    "denial of service",
                    "elevation of privilege",
                ]
            )
        ]

        total = 5
        failed = len(stride_issues)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION7",
            category_name="Threat Model & STRIDE Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="STRIDE Threat Matrix & Multi-Tenant Boundary Isolation",
            failure_reason=(
                f"Found {failed} active threat model control gaps."
                if failed > 0
                else None
            ),
            remediation_guidance="Verify identity guards, payload sanitization, audit logging, multi-tenant boundaries, rate limiting, and RBAC hierarchy.",
        )

    def check_certification8_regression_controls(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION8 - Security Regression Certification."""
        reintroduced_issues = [
            f
            for f in active_findings
            if (getattr(f, "status", None) or "").upper() == "REOPENED"
            or "regression" in (f.title or "").lower()
        ]

        total = 5
        failed = len(reintroduced_issues)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION8",
            category_name="Security Regression Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="Automated Security Regression Framework & Protection Matrix",
            failure_reason=(
                f"Found {failed} reopened or regressed security vulnerabilities."
                if failed > 0
                else None
            ),
            remediation_guidance="Execute `RegressionValidationRunnerService` to verify all 10 security regression guards remain intact.",
        )

    def check_certification9_governance_controls(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION9 - Governance & Access Control Certification."""
        rbac_issues = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower()
                for k in [
                    "rbac",
                    "privilege escalation",
                    "tenant isolation",
                    "unauthenticated access",
                ]
            )
        ]

        total = 5
        failed = len(rbac_issues)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION9",
            category_name="Governance & Access Control Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="RBAC Hierarchy (require_permission) & Multi-Tenant Access Boundaries",
            failure_reason=(
                f"Found {failed} governance or RBAC access control violations."
                if failed > 0
                else None
            ),
            remediation_guidance="Enforce RBAC role levels (`VIEWER` < `SECURITY_ANALYST` < `ADMIN`), decorate endpoints with `require_permission`, and verify `organization_id` scoping.",
        )

    def check_certification10_compliance_readiness(
        self, active_findings: List[SecurityFindingModel]
    ) -> CertificationCategoryResultDTO:
        """CERTIFICATION10 - Enterprise Compliance Readiness Certification."""
        critical_high = [
            f
            for f in active_findings
            if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(critical_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "FAILED"

        return CertificationCategoryResultDTO(
            category_code="CERTIFICATION10",
            category_name="Enterprise Compliance Readiness Certification",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            affected_control="Enterprise Production Security Posture & Compliance Engine",
            failure_reason=(
                f"Found {failed} unmitigated critical/high findings blocking enterprise compliance readiness."
                if failed > 0
                else None
            ),
            remediation_guidance="Attain 100% pass rates across all 10 Era 10 Security Control Plane validation suites for full production readiness.",
        )
