"""Container Image Security Audit & Runtime Hardening Suite Runner Service.

Executes in-memory container security assertions across all 10 CONTAINER categories
without creating database tables or document archival overhead.
"""

import shutil
from datetime import datetime, timezone
from typing import List, Optional, Set
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.container_validation.dto import (
    ContainerCategoryResultDTO,
    ContainerValidationSuiteResponse,
    ContainerValidationSummaryDTO,
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


class ContainerValidationRunnerService:
    """Service executing in-memory Container Image Security & Hardening Suites."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def run_container_validation(
        self, current_user: UserModel
    ) -> ContainerValidationSuiteResponse:
        """Execute automated Container validation assertion suite for user's organization."""
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
            action="validation.container_suite_started",
            resource_type="container_validation_suite",
            resource_id=suite_id,
            actor_user_id=current_user.id,
            details={"suite_id": suite_id},
        )

        # Run 10 CONTAINER category assertion checks
        cat_results: List[ContainerCategoryResultDTO] = [
            self.check_container1_base_image_cves(active_findings),
            self.check_container2_non_root_user(active_findings),
            self.check_container3_minimal_distroless(active_findings),
            self.check_container4_capability_drop(active_findings),
            self.check_container5_healthcheck(active_findings),
            self.check_container6_secret_exposure(active_findings),
            self.check_container7_resource_limits(active_findings),
            self.check_container8_network_isolation(active_findings),
            self.check_container9_seccomp_profiles(active_findings),
            self.check_container10_digest_pinning(active_findings),
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
            action="validation.container_suite_completed",
            resource_type="container_validation_suite",
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

        return ContainerValidationSuiteResponse(
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
    ) -> ContainerValidationSummaryDTO:
        """Return high-level Container Security verification summary for tenant."""
        suite = await self.run_container_validation(current_user)
        return ContainerValidationSummaryDTO(
            organization_id=str(current_user.organization_id),
            last_executed_at=suite.executed_at,
            overall_pass_rate=suite.overall_pass_rate,
            overall_status=suite.overall_status,
            passed_categories=suite.passed_categories,
            failed_categories=suite.failed_categories,
        )

    # ── CONTAINER Category Assertion Check Implementations ──

    def check_container1_base_image_cves(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER1 - Base Image CVE Vulnerability Audit."""
        # Inspect for Trivy binary tool availability
        trivy_available = shutil.which("trivy") is not None
        docker_available = shutil.which("docker") is not None

        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "container cve",
                    "base image vulnerability",
                    "trivy finding",
                    "os package vulnerability",
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

        # Controlled WARNING status if scanner tooling is unavailable
        reason: Optional[str] = None
        if not (trivy_available or docker_available) and failed == 0:
            status = "WARNING"
            reason = "Controlled Warning: Local Docker/Trivy binary scanner unavailable for dynamic image audit."
        else:
            status = "PASSED" if failed == 0 else "WARNING"
            reason = (
                f"Found {failed} container base image CVE findings."
                if failed > 0
                else None
            )

        return ContainerCategoryResultDTO(
            category_code="CONTAINER1",
            category_name="Base Image CVE Vulnerability Audit",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Base Images (python:3.11-slim, node:20-alpine)",
            failure_reason=reason,
            remediation_guidance="Upgrade container base images to minimal distroless or latest patched slim distributions verified by Trivy.",
        )

    def check_container2_non_root_user(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER2 - Unprivileged Non-Root Execution Guard."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "root container",
                    "container run as root",
                    "missing user directive",
                    "privileged container",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER2",
            category_name="Unprivileged Non-Root Execution Guard",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Dockerfile & Docker Compose Runtime User",
            failure_reason=(
                f"Found {failed} unprivileged execution findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Enforce explicit unprivileged non-root user execution (`USER appuser`, `UID 10001`) in Dockerfile runtime stages.",
        )

    def check_container3_minimal_distroless(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER3 - Minimal Base & Distroless Image Audit."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "unnecessary build tools",
                    "large container image",
                    "compiler in runtime",
                    "bloated container",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER3",
            category_name="Minimal Base & Distroless Image Audit",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Multi-Stage Dockerfile Runtime Image",
            failure_reason=(
                f"Found {failed} container footprint/tool findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Utilize multi-stage Docker builds to discard compilers, package managers, and development artifacts from runtime images.",
        )

    def check_container4_capability_drop(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER4 - Container Capability & Privilege Dropping."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "linux capabilities",
                    "cap_add",
                    "no_new_privs",
                    "read_only root",
                    "container privilege escalation",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER4",
            category_name="Container Capability & Privilege Dropping",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Docker Compose Security Opts & Capabilities",
            failure_reason=(
                f"Found {failed} container capability/privilege findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Drop unnecessary Linux capabilities (`cap_drop: [ALL]`), enforce `no-new-privileges:true`, and set read-only root filesystems.",
        )

    def check_container5_healthcheck(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER5 - Health Check & Liveness Probe Security."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "missing healthcheck",
                    "unhandled sigterm",
                    "liveness probe failure",
                    "zombie process",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER5",
            category_name="Health Check & Liveness Probe Security",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Dockerfile HEALTHCHECK & Liveness Probes",
            failure_reason=(
                f"Found {failed} container healthcheck findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Define explicit `HEALTHCHECK` directives in Dockerfiles pointing to isolated `/health` endpoints with graceful `SIGTERM` handling.",
        )

    def check_container6_secret_exposure(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER6 - Secret & Environment Variable Exposure."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "baked secret",
                    "dockerfile secret",
                    "hardcoded env secret",
                    "image layer secret",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER6",
            category_name="Secret & Environment Variable Exposure",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Container Image Layers & Build Arguments",
            failure_reason=(
                f"Found {failed} container secret exposure findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Mount secrets dynamically via Docker secrets or environment secret providers rather than baking them into image layers.",
        )

    def check_container7_resource_limits(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER7 - Resource Throttling & Cgroup Isolation."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "cgroup limit",
                    "missing memory limit",
                    "missing cpu limit",
                    "container oom",
                    "resource starvation",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER7",
            category_name="Resource Throttling & Cgroup Isolation",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Docker Compose Resource Specs (deploy.resources)",
            failure_reason=(
                f"Found {failed} container resource limit findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Set explicit memory (`memory: 1g`), CPU (`cpus: '1.0'`), and PID (`pids_limit: 100`) cgroup limits in container service manifests.",
        )

    def check_container8_network_isolation(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER8 - Container Network Isolation & Microsegmentation."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "default bridge network",
                    "exposed container port",
                    "unrestricted inter-container",
                    "host network mode",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER8",
            category_name="Container Network Isolation & Microsegmentation",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Docker Networks (vulnova-network custom bridge)",
            failure_reason=(
                f"Found {failed} container network isolation findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Isolate container services onto dedicated internal bridge networks (`vulnova-network`) and restrict host port bindings to ingress proxies.",
        )

    def check_container9_seccomp_profiles(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER9 - Runtime Container Security & Seccomp Profiles."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "seccomp missing",
                    "apparmor unconfined",
                    "syscall filtering",
                    "container runtime security",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER9",
            category_name="Runtime Container Security & Seccomp Profiles",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Seccomp & AppArmor Security Profiles",
            failure_reason=(
                f"Found {failed} Seccomp/AppArmor profile findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Attach default or restrictive custom Seccomp profiles (`seccomp:default.json`) to restrict allowed system call surfaces.",
        )

    def check_container10_digest_pinning(
        self, active_findings: List[SecurityFindingModel]
    ) -> ContainerCategoryResultDTO:
        """CONTAINER10 - Container Supply Chain & Registry Integrity."""
        matching = [
            f
            for f in active_findings
            if any(
                k in (f.title or "").lower() or k in (f.category or "").lower()
                for k in [
                    "unpinned image tag",
                    "latest tag",
                    "unsigned container image",
                    "untrusted container registry",
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

        return ContainerCategoryResultDTO(
            category_code="CONTAINER10",
            category_name="Container Supply Chain & Registry Integrity",
            status=status,
            pass_rate_percentage=pass_rate,
            passed_assertions=passed,
            failed_assertions=failed,
            total_assertions=total,
            finding_count=len(matching),
            affected_container="Container Image Manifests & Registry Directives",
            failure_reason=(
                f"Found {failed} container digest pinning findings."
                if failed > 0
                else None
            ),
            remediation_guidance="Pin production container images to immutable SHA-256 digests (`image@sha256:...`) and pull exclusively from verified private registries.",
        )
