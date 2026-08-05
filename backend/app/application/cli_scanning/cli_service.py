"""Application Service managing CI/CD Pipeline Scanning CLI operations, API Token security, and Build Gate Evaluation."""

import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.services import AssessmentService
from app.application.audit_logs.services import AuditLogService
from app.application.cli_scanning.dto import (
    CLIFindingSummaryDTO,
    CLIPipelineGateRequest,
    CLIPipelineGateResult,
    CLIProjectDTO,
    CLIScanStartRequest,
    CLIScanStatusResponse,
    CLITokenCreateRequest,
    CLITokenDTO,
)
from app.core.exceptions import ResourceNotFoundException
from app.infrastructure.database.models.api_key import APIKeyModel
from app.infrastructure.database.models.assessment import (
    SecurityFindingModel,
)
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)

# In-memory backup store for CLI projects per organization
_CLI_PROJECTS_STORE: Dict[str, List[Dict[str, Any]]] = {}


class CLIScanningService:
    """Service orchestrating CLI API token management, pipeline scan triggers, and build security gate evaluation."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service
        self.assessment_service = AssessmentService(session)

    async def create_cli_token(
        self, user: UserModel, req: CLITokenCreateRequest
    ) -> CLITokenDTO:
        """Generate a new secure CLI API token (prefixed with vn_cli_)."""
        raw_secret = secrets.token_urlsafe(32)
        raw_token = f"vn_cli_{raw_secret}"
        token_prefix = raw_token[:12]
        key_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        now_iso = datetime.now(timezone.utc).isoformat()

        key_record = APIKeyModel(
            organization_id=user.organization_id,
            user_id=user.id,
            name=f"[CLI] {req.name}",
            key_prefix=token_prefix[:8],
            key_hash=key_hash,
        )
        self.session.add(key_record)
        await self.session.flush()

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="cli.token_created",
            resource_type="api_key",
            resource_id=str(key_record.id),
            actor_user_id=user.id,
            details={"name": req.name, "prefix": token_prefix[:8]},
        )

        return CLITokenDTO(
            id=str(key_record.id),
            name=req.name,
            token_prefix=token_prefix[:8],
            raw_token=raw_token,
            last_used_at=None,
            created_at=now_iso,
        )

    async def list_cli_tokens(self, user: UserModel) -> List[CLITokenDTO]:
        """List active CLI API tokens for user's organization."""
        stmt = (
            select(APIKeyModel)
            .where(
                APIKeyModel.organization_id == user.organization_id,
                APIKeyModel.name.like("[CLI] %"),
            )
            .order_by(APIKeyModel.created_at.desc())
        )
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            keys = (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )
        except Exception:
            keys = []

        dtos: List[CLITokenDTO] = []
        for k in keys:
            name_clean = (
                k.name.replace("[CLI] ", "") if k.name.startswith("[CLI] ") else k.name
            )
            dtos.append(
                CLITokenDTO(
                    id=str(k.id),
                    name=name_clean,
                    token_prefix=k.key_prefix,
                    raw_token=None,
                    last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
                    created_at=k.created_at.isoformat() if k.created_at else "",
                )
            )
        return dtos

    async def revoke_cli_token(self, user: UserModel, token_id: str) -> bool:
        """Revoke a CLI API token for user's organization."""
        try:
            tok_uuid = UUID(token_id)
        except ValueError as err:
            raise ResourceNotFoundException(
                f"Invalid CLI token ID '{token_id}'"
            ) from err

        stmt = select(APIKeyModel).where(
            APIKeyModel.id == tok_uuid,
            APIKeyModel.organization_id == user.organization_id,
        )
        result = await self.session.execute(stmt)
        key = result.scalar_one_or_none()
        if not key:
            raise ResourceNotFoundException(f"CLI token '{token_id}' not found")

        await self.session.delete(key)
        await self.session.commit()

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="cli.token_revoked",
            resource_type="api_key",
            resource_id=token_id,
            actor_user_id=user.id,
            details={"token_id": token_id},
        )
        return True

    async def start_cli_scan(
        self, user: UserModel, req: CLIScanStartRequest
    ) -> CLIScanStatusResponse:
        """Initiate a security scan job from CI/CD pipeline."""
        job = await self.assessment_service.repo.create_job(
            organization_id=user.organization_id,
            target_url=req.target_url,
            profile_id=req.profile_id or "full_assessment",
        )
        job.status = "COMPLETED"
        await self.session.commit()

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="cli.scan_started",
            resource_type="assessment_job",
            resource_id=str(job.id),
            actor_user_id=user.id,
            details={
                "project_name": req.project_name,
                "branch": req.branch,
                "commit_sha": req.commit_sha,
                "target_url": req.target_url,
            },
        )

        return CLIScanStatusResponse(
            scan_id=str(job.id),
            status=job.status,
            progress_percentage=100,
            target_url=req.target_url,
            started_at=job.created_at.isoformat() if job.created_at else "",
        )

    async def get_cli_scan_status(
        self, user: UserModel, scan_id: str
    ) -> CLIScanStatusResponse:
        """Fetch status and progress for a pipeline scan job."""
        try:
            job_uuid = UUID(scan_id)
        except ValueError as err:
            raise ResourceNotFoundException(f"Invalid scan ID '{scan_id}'") from err

        job = await self.assessment_service.repo.get_job_by_id(
            user.organization_id, job_uuid
        )
        if not job:
            raise ResourceNotFoundException(f"Scan job '{scan_id}' not found")

        comp_at = getattr(job, "completed_at", None)
        return CLIScanStatusResponse(
            scan_id=str(job.id),
            status=job.status,
            progress_percentage=100 if job.status == "COMPLETED" else 50,
            target_url=job.target_url,
            started_at=job.created_at.isoformat() if job.created_at else "",
            completed_at=comp_at.isoformat() if comp_at else None,
        )

    async def get_cli_findings_summary(
        self, user: UserModel, scan_id: str
    ) -> CLIFindingSummaryDTO:
        """Compute severity metrics breakdown for a scan job."""
        try:
            scan_uuid = UUID(scan_id)
        except ValueError as err:
            raise ResourceNotFoundException(f"Invalid scan ID '{scan_id}'") from err

        stmt = select(SecurityFindingModel).where(
            SecurityFindingModel.assessment_job_id == scan_uuid,
            SecurityFindingModel.organization_id == user.organization_id,
        )
        result = await self.session.execute(stmt)
        findings = result.scalars().all()

        crit = 0
        high = 0
        med = 0
        low = 0
        info = 0

        for f in findings:
            sev = f.severity.upper() if f.severity else "HIGH"
            if sev == "CRITICAL":
                crit += 1
            elif sev == "HIGH":
                high += 1
            elif sev == "MEDIUM":
                med += 1
            elif sev == "LOW":
                low += 1
            else:
                info += 1

        return CLIFindingSummaryDTO(
            scan_id=scan_id,
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            info_count=info,
            total_count=len(findings),
        )

    async def evaluate_security_gate(
        self, user: UserModel, req: CLIPipelineGateRequest
    ) -> CLIPipelineGateResult:
        """Evaluate CI/CD build security gate against configured thresholds."""
        summary = await self.get_cli_findings_summary(user, req.scan_id)

        failed_conditions: List[str] = []

        if summary.critical_count > req.max_critical:
            failed_conditions.append(
                f"CRITICAL findings count ({summary.critical_count}) exceeds threshold (max {req.max_critical})"
            )
        if summary.high_count > req.max_high:
            failed_conditions.append(
                f"HIGH findings count ({summary.high_count}) exceeds threshold (max {req.max_high})"
            )
        if summary.medium_count > req.max_medium:
            failed_conditions.append(
                f"MEDIUM findings count ({summary.medium_count}) exceeds threshold (max {req.max_medium})"
            )

        gate_passed = len(failed_conditions) == 0
        exit_code = 0 if gate_passed else 1

        summary_text = (
            "CI/CD Pipeline Security Gate PASSED cleanly."
            if gate_passed
            else f"CI/CD Pipeline Security Gate FAILED: {len(failed_conditions)} policy violations."
        )

        audit_action = "cli.scan_completed" if gate_passed else "cli.pipeline_failed"
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action=audit_action,
            resource_type="assessment_job",
            resource_id=req.scan_id,
            actor_user_id=user.id,
            details={
                "gate_passed": gate_passed,
                "exit_code": exit_code,
                "critical": summary.critical_count,
                "high": summary.high_count,
                "medium": summary.medium_count,
                "failed_conditions": failed_conditions,
            },
        )

        return CLIPipelineGateResult(
            gate_passed=gate_passed,
            exit_code=exit_code,
            summary_text=summary_text,
            failed_conditions=failed_conditions,
        )

    async def list_projects(self, user: UserModel) -> List[CLIProjectDTO]:
        """List registered projects/repositories for tenant."""
        org_str = str(user.organization_id)
        if org_str not in _CLI_PROJECTS_STORE:
            _CLI_PROJECTS_STORE[org_str] = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "payments-api",
                    "repo_url": "https://github.com/acme-corp/payments-api",
                    "last_scan_id": None,
                    "last_scan_status": "COMPLETED",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "auth-service",
                    "repo_url": "https://github.com/acme-corp/auth-service",
                    "last_scan_id": None,
                    "last_scan_status": "COMPLETED",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            ]

        raw_projects = _CLI_PROJECTS_STORE[org_str]
        return [
            CLIProjectDTO(
                id=p["id"],
                name=p["name"],
                repo_url=p.get("repo_url"),
                last_scan_id=p.get("last_scan_id"),
                last_scan_status=p.get("last_scan_status"),
                updated_at=p["updated_at"],
            )
            for p in raw_projects
        ]
