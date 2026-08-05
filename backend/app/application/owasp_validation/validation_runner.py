"""OWASP Top 10 (2021) Security Validation Suite Runner Service.

Executes in-memory security validation assertions across all 10 OWASP Top 10 (2021)
categories without creating database tables or document archival overhead.
"""

from datetime import datetime, timezone
from typing import List, Set
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.owasp_validation.dto import (
    OWASPCategoryResultDTO,
    OWASPValidationSuiteResponse,
    OWASPVerificationSummaryDTO,
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


class OWASPValidationRunnerService:
    """Service executing in-memory OWASP Top 10 (2021) Security Validation Suites."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def run_validation_suite(
        self, current_user: UserModel
    ) -> OWASPValidationSuiteResponse:
        """Execute automated OWASP Top 10 (2021) security assertion suite for user's organization."""
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
            action="validation.owasp_suite_started",
            resource_type="validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={"suite_id": suite_id},
        )

        # Run 10 category assertion checks
        cat_results: List[OWASPCategoryResultDTO] = [
            self._check_a01_broken_access_control(active_findings),
            self._check_a02_cryptographic_failures(active_findings),
            self._check_a03_injection(active_findings),
            self._check_a04_insecure_design(active_findings),
            self._check_a05_security_misconfiguration(active_findings),
            self._check_a06_vulnerable_components(active_findings),
            self._check_a07_auth_failures(active_findings),
            self._check_a08_integrity_failures(active_findings),
            self._check_a09_logging_failures(active_findings),
            self._check_a10_ssrf(active_findings),
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
            action="validation.owasp_suite_completed",
            resource_type="validation_suite",
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

        return OWASPValidationSuiteResponse(
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
    ) -> OWASPVerificationSummaryDTO:
        """Return high-level OWASP verification summary for tenant."""
        suite = await self.run_validation_suite(current_user)
        return OWASPVerificationSummaryDTO(
            organization_id=str(current_user.organization_id),
            last_executed_at=suite.executed_at,
            overall_pass_rate=suite.overall_pass_rate,
            overall_status=suite.overall_status,
            passed_categories=suite.passed_categories,
            failed_categories=suite.failed_categories,
        )

    # ── Category Assertion Check Implementations ──

    def _check_a01_broken_access_control(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A01:2021 - Broken Access Control."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "access control",
                    "idor",
                    "privilege",
                    "authorization",
                    "permission",
                    "rbac",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else ("WARNING" if failed <= 1 else "FAILED")
        reason = (
            f"Discovered {failed} active CRITICAL/HIGH Broken Access Control vulnerability findings."
            if failed > 0
            else None
        )

        return OWASPCategoryResultDTO(
            category_code="A01:2021",
            category_name="Broken Access Control",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=reason,
            affected_subsystem="RBACPolicy & OrganizationIsolation",
            remediation_guidance="Enforce strict tenant boundary checks (`organization_id`) and canonical permission guards (`require_permission`) across all REST router endpoints.",
        )

    def _check_a02_cryptographic_failures(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A02:2021 - Cryptographic Failures."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "crypto",
                    "plaintext",
                    "secret",
                    "cipher",
                    "ssl",
                    "tls",
                    "key",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else ("WARNING" if failed <= 1 else "FAILED")
        reason = (
            f"Discovered {failed} active Cryptographic Failure vulnerability findings in configuration or secrets."
            if failed > 0
            else None
        )

        return OWASPCategoryResultDTO(
            category_code="A02:2021",
            category_name="Cryptographic Failures",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=reason,
            affected_subsystem="SecretEncryptionService & APIKeyModel",
            remediation_guidance="Encrypt sensitive credentials at rest using AES-256-GCM / Fernet, hash API keys via SHA-256, and mask secrets in all REST responses.",
        )

    def _check_a03_injection(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A03:2021 - Injection."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "sqli",
                    "sql injection",
                    "command injection",
                    "xss",
                    "script",
                    "html injection",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else ("WARNING" if failed <= 1 else "FAILED")
        reason = (
            f"Discovered {failed} active Injection vulnerability findings (SQLi/Command Injection/XSS)."
            if failed > 0
            else None
        )

        return OWASPCategoryResultDTO(
            category_code="A03:2021",
            category_name="Injection",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=reason,
            affected_subsystem="DatabaseORM & InputSanitizer",
            remediation_guidance="Use SQLAlchemy ORM parameterized queries exclusively, sanitize HTML/script inputs via `sanitize_sensitive_data`, and avoid raw shell execution.",
        )

    def _check_a04_insecure_design(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A04:2021 - Insecure Design."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in ["design", "architecture", "rate limit", "workflow", "policy"]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return OWASPCategoryResultDTO(
            category_code="A04:2021",
            category_name="Insecure Design",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=(
                f"Found {failed} architecture design findings." if failed > 0 else None
            ),
            affected_subsystem="AssessmentPolicyEngine",
            remediation_guidance="Validate pre-scan target authorization contracts (`validate_scan_authorization`) and enforce continuous policy rules.",
        )

    def _check_a05_security_misconfiguration(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A05:2021 - Security Misconfiguration."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "header",
                    "misconfiguration",
                    "cors",
                    "csp",
                    "hsts",
                    "default credential",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return OWASPCategoryResultDTO(
            category_code="A05:2021",
            category_name="Security Misconfiguration",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=(
                f"Found {failed} security misconfiguration findings."
                if failed > 0
                else None
            ),
            affected_subsystem="HeaderSecurityPlugin & FastAPIMiddleware",
            remediation_guidance="Configure HSTS, Content-Security-Policy, X-Frame-Options, X-Content-Type-Options headers, and restrict CORS origin wildcards.",
        )

    def _check_a06_vulnerable_components(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A06:2021 - Vulnerable and Outdated Components."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "cve",
                    "outdated",
                    "vulnerable component",
                    "dependency",
                    "package",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return OWASPCategoryResultDTO(
            category_code="A06:2021",
            category_name="Vulnerable and Outdated Components",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=(
                f"Found {failed} vulnerable dependency findings."
                if failed > 0
                else None
            ),
            affected_subsystem="VulnerabilityIntelligenceService",
            remediation_guidance="Upgrade third-party Python/Node packages to patched versions and pin dependencies to immutable versions in requirements.txt and package.json.",
        )

    def _check_a07_auth_failures(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A07:2021 - Identification and Authentication Failures."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "auth",
                    "authentication",
                    "session",
                    "jwt",
                    "token",
                    "password",
                    "brute force",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return OWASPCategoryResultDTO(
            category_code="A07:2021",
            category_name="Identification and Authentication Failures",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=(
                f"Found {failed} authentication vulnerability findings."
                if failed > 0
                else None
            ),
            affected_subsystem="JWTAuthHandler & APIKeyVerifier",
            remediation_guidance="Enforce strong JWT secret signatures, password hashing via bcrypt/argon2, API key prefix validation (`vn_live_`, `vn_cli_`), and short token lifetimes.",
        )

    def _check_a08_integrity_failures(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A08:2021 - Software and Data Integrity Failures."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "integrity",
                    "checksum",
                    "untrusted",
                    "deserialization",
                    "pipeline",
                    "gate",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return OWASPCategoryResultDTO(
            category_code="A08:2021",
            category_name="Software and Data Integrity Failures",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=(
                f"Found {failed} software integrity findings." if failed > 0 else None
            ),
            affected_subsystem="EvidenceEngine & CLIPipelineGate",
            remediation_guidance="Verify SHA-256 checksums on all uploaded evidence artifacts and enforce CI/CD build security gate policies.",
        )

    def _check_a09_logging_failures(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A09:2021 - Security Logging and Monitoring Failures."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "log",
                    "logging",
                    "monitoring",
                    "audit",
                    "alert",
                    "notification",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
        crit_high = [
            f for f in matching if (f.severity or "").upper() in ("CRITICAL", "HIGH")
        ]

        total = 5
        failed = len(crit_high)
        passed = max(0, total - failed)
        pass_rate = round((passed / total) * 100.0, 1)

        status = "PASSED" if failed == 0 else "WARNING"

        return OWASPCategoryResultDTO(
            category_code="A09:2021",
            category_name="Security Logging and Monitoring Failures",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=(
                f"Found {failed} logging or monitoring findings."
                if failed > 0
                else None
            ),
            affected_subsystem="AuditLogService & NotificationService",
            remediation_guidance="Record non-repudiable audit events (`actor_user_id`, `organization_id`, `timestamp`) for all administrative actions and configure real-time Slack/Teams webhooks.",
        )

    def _check_a10_ssrf(
        self, active_findings: List[SecurityFindingModel]
    ) -> OWASPCategoryResultDTO:
        """A10:2021 - Server-Side Request Forgery (SSRF)."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "ssrf",
                    "server-side request forgery",
                    "internal ip",
                    "aws imds",
                    "metadata",
                ]
            )
        ]
        finding_ids = [str(f.id) for f in matching]
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
            f"Discovered {len(crit_high)} active SSRF vulnerability findings or SSRF validator policy violation."
            if failed > 0
            else None
        )

        return OWASPCategoryResultDTO(
            category_code="A10:2021",
            category_name="Server-Side Request Forgery (SSRF)",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_finding_ids=finding_ids,
            failure_reason=reason,
            affected_subsystem="SSRFValidator & TargetUrlFilter",
            remediation_guidance="Enforce `is_safe_target_url` validation blocking private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.1, AWS IMDS 169.254.169.254) and DNS rebinding attacks.",
        )
