"""Dependency Security Audit & SCA Enforcement Suite Runner Service.

Executes in-memory Software Composition Analysis (SCA) assertions across all 10 SCA
categories without creating database tables or document archival overhead.
"""

from datetime import datetime, timezone
from typing import List, Set
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.sca_validation.dto import (
    SCACategoryResultDTO,
    SCAValidationSuiteResponse,
    SCAValidationSummaryDTO,
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


class SCAValidationRunnerService:
    """Service executing in-memory Software Composition Analysis Suites."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def run_sca_validation(
        self, current_user: UserModel
    ) -> SCAValidationSuiteResponse:
        """Execute automated SCA validation assertion suite for user's organization."""
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
            action="validation.sca_suite_started",
            resource_type="sca_validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={"suite_id": suite_id},
        )

        # Run 10 SCA category assertion checks
        cat_results: List[SCACategoryResultDTO] = [
            self.check_sca1_cve_vulnerabilities(active_findings),
            self.check_sca2_lockfile_integrity(active_findings),
            self.check_sca3_outdated_dependencies(active_findings),
            self.check_sca4_pipeline_enforcement(active_findings),
            self.check_sca5_license_compliance(active_findings),
            self.check_sca6_typosquatting_malicious(active_findings),
            self.check_sca7_transitive_tree_risk(active_findings),
            self.check_sca8_version_pinning(active_findings),
            self.check_sca9_db_engine_dependencies(active_findings),
            self.check_sca10_remediation_sla(active_findings),
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
            action="validation.sca_suite_completed",
            resource_type="sca_validation_suite",
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

        return SCAValidationSuiteResponse(
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
    ) -> SCAValidationSummaryDTO:
        """Return high-level Dependency Security verification summary for tenant."""
        suite = await self.run_sca_validation(current_user)
        return SCAValidationSummaryDTO(
            organization_id=str(current_user.organization_id),
            last_executed_at=suite.executed_at,
            overall_pass_rate=suite.overall_pass_rate,
            overall_status=suite.overall_status,
            passed_categories=suite.passed_categories,
            failed_categories=suite.failed_categories,
        )

    # ── SCA Assertion Check Implementations ──

    def check_sca1_cve_vulnerabilities(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA1 - Known CVE Vulnerability Audit."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "cve",
                    "dependency vulnerability",
                    "vulnerable package",
                    "pip-audit",
                    "npm audit",
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

        return SCACategoryResultDTO(
            category_code="SCA1",
            category_name="Known CVE Vulnerability Audit",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="PyPI & NPM Dependencies (requirements.txt, package.json)",
            failure_reason=(
                f"Found {failed} dependency CVE vulnerability findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Update vulnerable packages to non-vulnerable patch versions identified by VulnerabilityIntelligenceService.",
        )

    def check_sca2_lockfile_integrity(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA2 - Supply Chain Lockfile Integrity."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "lockfile missing",
                    "lockfile integrity",
                    "checksum mismatch",
                    "tampered package",
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

        return SCACategoryResultDTO(
            category_code="SCA2",
            category_name="Supply Chain Lockfile Integrity",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="Dependency Lockfiles (pyproject.toml & package-lock.json)",
            failure_reason=(
                f"Found {failed} lockfile integrity findings." if failed > 0 else None
            ),
            remediation_guidance="Enforce lockfile presence in VCS, verify SHA-256 package hashes during builds, and prohibit unpinned install flags.",
        )

    def check_sca3_outdated_dependencies(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA3 - Outdated Dependency & Deprecation Audit."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "outdated dependency",
                    "deprecated package",
                    "end of life",
                    "eol library",
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

        return SCACategoryResultDTO(
            category_code="SCA3",
            category_name="Outdated Dependency & Deprecation Audit",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="Third-Party Runtime Libraries",
            failure_reason=(
                f"Found {failed} outdated/deprecated dependency findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Establish a quarterly dependency maintenance schedule to upgrade out-of-date major/minor library versions.",
        )

    def check_sca4_pipeline_enforcement(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA4 - Automated SCA Pipeline Enforcement."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "sca gate",
                    "pipeline sca",
                    "missing pip-audit",
                    "missing npm audit",
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

        return SCACategoryResultDTO(
            category_code="SCA4",
            category_name="Automated SCA Pipeline Enforcement",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="GitHub Actions Workflows (.github/workflows/*)",
            failure_reason=(
                f"Found {failed} SCA pipeline enforcement findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Integrate `pip-audit` and `npm audit` steps into CI/CD build gates to block vulnerable pull requests.",
        )

    def check_sca5_license_compliance(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA5 - License Compliance & IP Risk Audit."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "license risk",
                    "gpl violation",
                    "copyleft",
                    "license missing",
                    "agpl",
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

        return SCACategoryResultDTO(
            category_code="SCA5",
            category_name="License Compliance & IP Risk Audit",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="Open-Source Package Licenses (MIT, Apache, GPL)",
            failure_reason=(
                f"Found {failed} license compliance findings." if failed > 0 else None
            ),
            remediation_guidance="Audit third-party package licenses against corporate IP policy and replace restrictively licensed libraries.",
        )

    def check_sca6_typosquatting_malicious(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA6 - Malicious Package & Typosquatting Detection."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "typosquatting",
                    "malicious package",
                    "untrusted registry",
                    "postinstall script",
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

        return SCACategoryResultDTO(
            category_code="SCA6",
            category_name="Malicious Package & Typosquatting Detection",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="Package Registry Index (PyPI / NPM Registry)",
            failure_reason=(
                f"Found {failed} typosquatting/malicious package findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Enforce official package registry mirrors, disable unverified post-install scripts (`npm ignore-scripts`), and verify package names.",
        )

    def check_sca7_transitive_tree_risk(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA7 - Transitive Dependency Tree Risk."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "transitive dependency",
                    "indirect cve",
                    "deep dependency",
                    "nested package",
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

        return SCACategoryResultDTO(
            category_code="SCA7",
            category_name="Transitive Dependency Tree Risk",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="Transitive Dependency Tree",
            failure_reason=(
                f"Found {failed} transitive dependency findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Use dependency resolution overrides (`npm overrides` / `pip` constraints) to patch vulnerable nested transitive packages.",
        )

    def check_sca8_version_pinning(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA8 - Direct Dependency Pinning Guard."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "unpinned version",
                    "wildcard dependency",
                    "loose version",
                    "unrestricted range",
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

        return SCACategoryResultDTO(
            category_code="SCA8",
            category_name="Direct Dependency Pinning Guard",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="Production Manifests (pyproject.toml, package.json)",
            failure_reason=(
                f"Found {failed} version pinning findings." if failed > 0 else None
            ),
            remediation_guidance="Enforce exact version pinning (`==` in Python, exact version strings in NPM) to prevent unexpected breaking updates.",
        )

    def check_sca9_db_engine_dependencies(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA9 - Database & Engine Dependency Security."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "asyncpg",
                    "psycopg",
                    "sqlalchemy",
                    "redis-py",
                    "celery driver",
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

        return SCACategoryResultDTO(
            category_code="SCA9",
            category_name="Database & Engine Dependency Security",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="Core Engine Drivers (SQLAlchemy, AsyncPG, Redis, Celery)",
            failure_reason=(
                f"Found {failed} DB/engine dependency security findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Keep database client drivers and task queue worker libraries updated to patch underlying protocol & socket vulnerabilities.",
        )

    def check_sca10_remediation_sla(
        self, active_findings: List[SecurityFindingModel]
    ) -> SCACategoryResultDTO:
        """SCA10 - Vulnerability Remediation Workflow SLA."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "remediation sla",
                    "overdue cve",
                    "unpatched dependency",
                    "expired sla",
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

        return SCACategoryResultDTO(
            category_code="SCA10",
            category_name="Vulnerability Remediation Workflow SLA",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_package="Vulnerability Remediation Tracker",
            failure_reason=(
                f"Found {failed} overdue dependency CVE SLA findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Enforce 30-day Critical/High CVE remediation SLA policies for all third-party package vulnerabilities.",
        )
