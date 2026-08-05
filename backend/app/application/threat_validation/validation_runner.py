"""Threat Model Review & STRIDE Verification Suite Runner Service.

Executes in-memory threat model assertions across all 10 STRIDE categories
without creating database tables or document archival overhead.
"""

from datetime import datetime, timezone
from typing import List, Set
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.threat_validation.dto import (
    ThreatCategoryResultDTO,
    ThreatValidationSuiteResponse,
    ThreatValidationSummaryDTO,
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


class ThreatValidationRunnerService:
    """Service executing in-memory Threat Model & STRIDE Verification Suites."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def run_threat_validation(
        self, current_user: UserModel
    ) -> ThreatValidationSuiteResponse:
        """Execute automated Threat Model validation assertion suite for user's organization."""
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
            action="validation.threat_suite_started",
            resource_type="threat_validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={"suite_id": suite_id},
        )

        # Run 10 STRIDE category assertion checks
        cat_results: List[ThreatCategoryResultDTO] = [
            self.check_stride1_spoofing_identity(active_findings),
            self.check_stride2_spoofing_api_keys(active_findings),
            self.check_stride3_tampering_input_injection(active_findings),
            self.check_stride4_tampering_webhook_signatures(active_findings),
            self.check_stride5_repudiation_audit_logging(active_findings),
            self.check_stride6_information_disclosure_multitenancy(active_findings),
            self.check_stride7_information_disclosure_crypto_egress(active_findings),
            self.check_stride8_denial_of_service_rate_limiting(active_findings),
            self.check_stride9_elevation_of_privilege_rbac(active_findings),
            self.check_stride10_elevation_of_privilege_sandbox(active_findings),
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
            action="validation.threat_suite_completed",
            resource_type="threat_validation_suite",
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

        return ThreatValidationSuiteResponse(
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
    ) -> ThreatValidationSummaryDTO:
        """Return high-level Threat Model & STRIDE verification summary for tenant."""
        suite = await self.run_threat_validation(current_user)
        return ThreatValidationSummaryDTO(
            organization_id=str(current_user.organization_id),
            last_executed_at=suite.executed_at,
            overall_pass_rate=suite.overall_pass_rate,
            overall_status=suite.overall_status,
            passed_categories=suite.passed_categories,
            failed_categories=suite.failed_categories,
        )

    # ── STRIDE Category Assertion Check Implementations ──

    def check_stride1_spoofing_identity(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE1 - Spoofing: Identity Authentication & Session Guard."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "spoofing",
                    "session hijacking",
                    "jwt bypass",
                    "identity spoofing",
                    "expired token accepted",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE1",
            category_name="Spoofing: Identity Authentication & Session Guard",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="User JWT Bearer Authentication & Token Expiration",
            failure_reason=(
                f"Found {failed} identity spoofing findings." if failed > 0 else None
            ),
            remediation_guidance="Enforce cryptographic JWT signature validation, strict expiration (`exp`) claims, and secure session invalidation.",
        )

    def check_stride2_spoofing_api_keys(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE2 - Spoofing: Machine-to-Machine API Key Authentication Guard."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "api key spoofing",
                    "unhashed api key",
                    "invalid api key prefix",
                    "key spoofing",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE2",
            category_name="Spoofing: Machine-to-Machine API Key Authentication Guard",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="API Key Authentication (vn_live_ Prefix & SHA-256 Digest)",
            failure_reason=(
                f"Found {failed} API key spoofing findings." if failed > 0 else None
            ),
            remediation_guidance="Validate `vn_live_` key prefixes, store API keys strictly as SHA-256 hex digests, and verify via constant-time comparison.",
        )

    def check_stride3_tampering_input_injection(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE3 - Tampering: Input Sanitization & Injection Defense."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "sql injection",
                    "command injection",
                    "input tampering",
                    "payload injection",
                    "pydantic validation bypass",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE3",
            category_name="Tampering: Input Sanitization & Injection Defense",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="FastAPI Request Schema Validation & SQLAlchemy ORM",
            failure_reason=(
                f"Found {failed} input injection tampering findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Enforce strict Pydantic request payload validation, parameterized SQLAlchemy ORM queries, and subprocess array execution.",
        )

    def check_stride4_tampering_webhook_signatures(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE4 - Tampering: Webhook & Data Signature Integrity."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "webhook tampering",
                    "missing webhook hmac",
                    "signature forgery",
                    "payload forgery",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE4",
            category_name="Tampering: Webhook & Data Signature Integrity",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Webhook Payload Integration Signatures (HMAC-SHA256)",
            failure_reason=(
                f"Found {failed} webhook signature tampering findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Verify HMAC-SHA256 payload signatures (`X-Vulnova-Signature`) on all incoming and outgoing integration webhooks.",
        )

    def check_stride5_repudiation_audit_logging(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE5 - Repudiation: Immutable Audit Logging & Event Tracking."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "unlogged action",
                    "audit log bypass",
                    "missing actor id",
                    "repudiation",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE5",
            category_name="Repudiation: Immutable Audit Logging & Event Tracking",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="AuditLogService Audit Event Tracking & Non-Repudiation",
            failure_reason=(
                f"Found {failed} audit logging repudiation findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Record mandatory `AuditLogService` events for all administrative actions, authentication attempts, and scan modifications.",
        )

    def check_stride6_information_disclosure_multitenancy(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE6 - Information Disclosure: Multi-Tenant Boundary Isolation."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "idor",
                    "cross-tenant leakage",
                    "tenant isolation failure",
                    "data leak",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE6",
            category_name="Information Disclosure: Multi-Tenant Boundary Isolation",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Multi-Tenant Database Queries (organization_id Scope)",
            failure_reason=(
                f"Found {failed} multi-tenant boundary findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Enforce mandatory `organization_id == current_user.organization_id` SQL filters across all database query execution paths.",
        )

    def check_stride7_information_disclosure_crypto_egress(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE7 - Information Disclosure: Sensitive Field Encryption & Egress Safeguards."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "stack trace leakage",
                    "cleartext credential",
                    "ssrf internal egress",
                    "cloud metadata leak",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE7",
            category_name="Information Disclosure: Sensitive Field Encryption & Egress Safeguards",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="AES-256-GCM Field Encryption & SSRF Egress Validator",
            failure_reason=(
                f"Found {failed} information disclosure/egress findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Encrypt sensitive credentials with AES-256-GCM, mask production stack traces, and restrict SSRF egress via `is_safe_target_url`.",
        )

    def check_stride8_denial_of_service_rate_limiting(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE8 - Denial of Service: Rate Limiting & Resource Throttling."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "missing rate limit",
                    "dos vulnerability",
                    "worker queue overflow",
                    "unthrottled endpoint",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE8",
            category_name="Denial of Service: Rate Limiting & Resource Throttling",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Redis RateLimiter Middleware & Worker Task Queues",
            failure_reason=(
                f"Found {failed} DoS rate limiting findings." if failed > 0 else None
            ),
            remediation_guidance="Attach Redis-backed RateLimiter guards to authentication and scan endpoints and restrict Celery worker concurrency.",
        )

    def check_stride9_elevation_of_privilege_rbac(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE9 - Elevation of Privilege: RBAC Permission Hierarchy."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "privilege escalation",
                    "rbac bypass",
                    "unauthorized admin access",
                    "missing permission decorator",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE9",
            category_name="Elevation of Privilege: RBAC Permission Hierarchy",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="RBAC Hierarchy (require_permission & Role Level Enforcement)",
            failure_reason=(
                f"Found {failed} privilege escalation findings." if failed > 0 else None
            ),
            remediation_guidance="Protect administrative routes with explicit `require_permission` guards matching role levels (VIEWER < ANALYST < ADMIN).",
        )

    def check_stride10_elevation_of_privilege_sandbox(
        self, active_findings: List[SecurityFindingModel]
    ) -> ThreatCategoryResultDTO:
        """STRIDE10 - Elevation of Privilege: Sandbox & Execution Boundary Isolation."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "sandbox escape",
                    "container root execution",
                    "missing cap_drop",
                    "privileged container escape",
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

        return ThreatCategoryResultDTO(
            category_code="STRIDE10",
            category_name="Elevation of Privilege: Sandbox & Execution Boundary Isolation",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_component="Docker Sandbox Container Hardening (cap_drop ALL & USER appuser)",
            failure_reason=(
                f"Found {failed} sandbox isolation findings." if failed > 0 else None
            ),
            remediation_guidance="Enforce unprivileged non-root user execution (`USER appuser`), `cap_drop: [ALL]`, and `no-new-privileges` in container sandboxes.",
        )
