"""Dashboard Analytics Service for Phase 7.1 Security Operations Dashboard.

Aggregates security posture metrics, vulnerability distributions, active scan executions,
high-risk target assets, and recurring schedule status.

Extends existing domain repositories and services without introducing duplicate vulnerability engines
or bypassing tenant isolation.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import (
    ActiveScanSummaryDTO,
    DashboardOverviewResponse,
    SchedulesOverviewSummaryDTO,
    SecurityPostureSummaryDTO,
    TopVulnerableAssetDTO,
    VulnerabilitySeverityBreakdownDTO,
)
from app.infrastructure.database.models.assessment import (
    AssessmentJobModel,
    SecurityFindingModel,
)
from app.infrastructure.database.models.scan_schedule import ScanScheduleModel
from app.infrastructure.database.models.scan_target import ScanTargetModel
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)

CACHE_TTL_SECONDS = 30


class DashboardAnalyticsService:
    """Application service for SOC Dashboard telemetry and metric aggregations."""

    def __init__(
        self, session: AsyncSession, redis_client: Optional[Any] = None
    ) -> None:
        self.session = session
        self.redis_client = redis_client

    async def get_dashboard_overview(
        self, current_user: UserModel
    ) -> DashboardOverviewResponse:
        """Fetch or calculate consolidated SOC dashboard metrics for user's organization.

        Strictly enforces tenant isolation (organization_id = current_user.organization_id).
        Uses Redis caching (TTL 30s) when available to prevent database overload.
        """
        org_id = current_user.organization_id
        cache_key = f"dashboard:metrics:{org_id}"

        # 1. Attempt Redis Cache Retrieval
        if self.redis_client is not None:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    data_dict = json.loads(cached_data)
                    logger.debug("dashboard.cache_hit", organization_id=str(org_id))
                    return DashboardOverviewResponse(**data_dict)
            except Exception as exc:
                logger.warning("dashboard.cache_read_error", error=str(exc))

        # 2. Database Aggregations (Enforcing Tenant Isolation)
        now_utc = datetime.now(timezone.utc)

        # Target Counts
        target_stmt = select(func.count(ScanTargetModel.id)).where(
            ScanTargetModel.organization_id == org_id,
            ScanTargetModel.status == "ACTIVE",
        )
        target_count_res = await self.session.execute(target_stmt)
        total_targets = target_count_res.scalar() or 0

        # Vulnerability Severity Breakdown
        finding_stmt = (
            select(SecurityFindingModel.severity, func.count(SecurityFindingModel.id))
            .where(SecurityFindingModel.organization_id == org_id)
            .group_by(SecurityFindingModel.severity)
        )
        finding_res = await self.session.execute(finding_stmt)
        severity_counts: Dict[str, int] = {
            row[0].upper(): row[1] for row in finding_res.all()
        }

        crit_count = severity_counts.get("CRITICAL", 0)
        high_count = severity_counts.get("HIGH", 0)
        med_count = severity_counts.get("MEDIUM", 0)
        low_count = severity_counts.get("LOW", 0)
        info_count = severity_counts.get("INFO", 0)

        total_open_findings = (
            crit_count + high_count + med_count + low_count + info_count
        )

        vulnerability_breakdown = VulnerabilitySeverityBreakdownDTO(
            critical_count=crit_count,
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count,
            info_count=info_count,
        )

        # Composite Risk Score Calculation (0.0 to 100.0)
        # Formula: Weighted severity sum normalized by asset targets
        weighted_score = (
            (crit_count * 25.0)
            + (high_count * 10.0)
            + (med_count * 3.0)
            + (low_count * 1.0)
        )
        base_denom = max(total_targets, 1)
        raw_risk = (weighted_score / base_denom) * 2.0
        composite_risk_score = min(round(raw_risk, 1), 100.0)

        if composite_risk_score >= 75.0 or crit_count > 0:
            posture_status = "CRITICAL_RISK"
        elif composite_risk_score >= 40.0 or high_count > 0:
            posture_status = "ELEVATED_RISK"
        else:
            posture_status = "SECURE"

        posture_summary = SecurityPostureSummaryDTO(
            composite_risk_score=composite_risk_score,
            posture_status=posture_status,
            total_targets_count=total_targets,
            total_open_findings=total_open_findings,
            critical_findings_count=crit_count,
            high_findings_count=high_count,
        )

        # Active Scan Jobs
        active_states = [
            "QUEUED",
            "CRAWLING",
            "ASSESSING",
            "AI_ANALYSIS",
            "RUNNING",
            "PENDING",
        ]
        active_scans_stmt = (
            select(AssessmentJobModel)
            .where(
                AssessmentJobModel.organization_id == org_id,
                AssessmentJobModel.execution_state.in_(active_states),
            )
            .order_by(AssessmentJobModel.created_at.desc())
            .limit(10)
        )
        active_scans_res = await self.session.execute(active_scans_stmt)
        active_scans_list: List[ActiveScanSummaryDTO] = []
        for job in active_scans_res.scalars().all():
            started_str = (
                job.started_at.isoformat()
                if job.started_at
                else job.created_at.isoformat()
            )
            duration = 0
            if job.started_at:
                start_dt = (
                    job.started_at
                    if job.started_at.tzinfo
                    else job.started_at.replace(tzinfo=timezone.utc)
                )
                duration = int((now_utc - start_dt).total_seconds())

            active_scans_list.append(
                ActiveScanSummaryDTO(
                    job_id=str(job.id),
                    target_name=job.target_url.split("//")[-1].split("/")[0],
                    target_url=job.target_url,
                    execution_state=job.execution_state,
                    current_step=job.current_step or job.execution_state,
                    started_at=started_str,
                    running_duration_seconds=max(duration, 0),
                )
            )

        # Top Vulnerable Target Assets
        top_targets_stmt = (
            select(ScanTargetModel)
            .where(
                ScanTargetModel.organization_id == org_id,
                ScanTargetModel.status == "ACTIVE",
            )
            .limit(5)
        )
        top_targets_res = await self.session.execute(top_targets_stmt)
        top_assets: List[TopVulnerableAssetDTO] = []
        for target in top_targets_res.scalars().all():
            # Query finding counts for this target via AssessmentJobModel.target_url
            target_finding_stmt = (
                select(
                    SecurityFindingModel.severity, func.count(SecurityFindingModel.id)
                )
                .join(
                    AssessmentJobModel,
                    SecurityFindingModel.assessment_job_id == AssessmentJobModel.id,
                )
                .where(
                    SecurityFindingModel.organization_id == org_id,
                    AssessmentJobModel.target_url == target.target_url,
                )
                .group_by(SecurityFindingModel.severity)
            )
            target_finding_res = await self.session.execute(target_finding_stmt)
            t_counts: Dict[str, int] = {
                row[0].upper(): row[1] for row in target_finding_res.all()
            }
            t_crit = t_counts.get("CRITICAL", 0)
            t_high = t_counts.get("HIGH", 0)
            t_risk = min(round((t_crit * 30.0) + (t_high * 12.0) + 10.0, 1), 100.0)

            top_assets.append(
                TopVulnerableAssetDTO(
                    target_id=str(target.id),
                    target_url=target.target_url,
                    environment=target.environment,
                    risk_score=t_risk,
                    critical_count=t_crit,
                    high_count=t_high,
                )
            )

        top_assets.sort(key=lambda a: a.risk_score, reverse=True)

        # Schedules Summary
        schedules_stmt = select(
            func.count(ScanScheduleModel.id),
            func.min(ScanScheduleModel.next_run_at),
        ).where(
            ScanScheduleModel.organization_id == org_id,
            ScanScheduleModel.status == "ACTIVE",
        )
        sched_res = await self.session.execute(schedules_stmt)
        sched_row = sched_res.one()
        active_sched_count = sched_row[0] or 0
        next_run_dt = sched_row[1]
        next_run_str = next_run_dt.isoformat() if next_run_dt else None

        schedules_summary = SchedulesOverviewSummaryDTO(
            total_active_schedules=active_sched_count,
            next_scheduled_run_at=next_run_str,
        )

        overview = DashboardOverviewResponse(
            organization_id=str(org_id),
            posture_summary=posture_summary,
            vulnerability_breakdown=vulnerability_breakdown,
            active_scans=active_scans_list,
            top_vulnerable_assets=top_assets,
            schedules_summary=schedules_summary,
            cached_at=now_utc.isoformat(),
        )

        # 3. Populate Redis Cache
        if self.redis_client is not None:
            try:
                await self.redis_client.set(
                    cache_key,
                    json.dumps(overview.model_dump()),
                    ex=CACHE_TTL_SECONDS,
                )
                logger.debug("dashboard.cache_write", organization_id=str(org_id))
            except Exception as exc:
                logger.warning("dashboard.cache_write_error", error=str(exc))

        return overview
