"""Continuous Attack Surface Monitoring & Change Detection Engine."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import (
    AssetChangeEventDTO,
    AssetSnapshotDTO,
    PostureTimelineResponse,
    RiskTrajectoryResponse,
)
from app.core.logging import get_logger
from app.domain.entities.assessment import AssessmentContext, Finding
from app.infrastructure.database.models.trend import AssetSnapshotModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.asset_inventory_repository import (
    AssetInventoryRepository,
)
from app.infrastructure.database.repositories.asset_trend_repository import (
    AssetTrendRepository,
)

logger = get_logger("vulnova.continuous_monitoring")


class ChangeDetectionEngine:
    """Detects attack surface asset, technology, and vulnerability state changes across assessment runs."""

    def analyze_finding_lifecycle(
        self,
        current_findings: List[Finding],
        previous_finding_titles: set[str],
    ) -> List[Tuple[str, str, str]]:
        """Identify vulnerability lifecycle state shifts (NEW, RESOLVED, REOPENED).

        Returns list of (change_type, title, description).
        """
        changes: List[Tuple[str, str, str]] = []
        current_titles = {f.title for f in current_findings}

        # 1. Detect NEW findings
        for f in current_findings:
            if f.title not in previous_finding_titles:
                changes.append(
                    (
                        "FINDING_NEW",
                        f"New Vulnerability: {f.title}",
                        f.description or f"Newly detected {f.severity.value} finding.",
                    )
                )

        # 2. Detect RESOLVED findings
        for prev_title in previous_finding_titles:
            if prev_title not in current_titles:
                changes.append(
                    (
                        "FINDING_RESOLVED",
                        f"Resolved Vulnerability: {prev_title}",
                        f"Vulnerability '{prev_title}' was resolved in the latest assessment run.",
                    )
                )

        return changes


class ContinuousMonitoringService:
    """Application service for attack surface posture snapshotting, change detection, and trend analytics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trend_repo = AssetTrendRepository(session)
        self.inventory_repo = AssetInventoryRepository(session)
        self.change_engine = ChangeDetectionEngine()

    async def process_scan_run(
        self,
        organization_id: UUID,
        assessment_job_id: UUID,
        findings: List[Finding],
        context: AssessmentContext,
    ) -> Tuple[AssetSnapshotDTO, List[AssetChangeEventDTO]]:
        """Process an assessment run: calculate posture metrics, detect state changes, and persist snapshot linked to job_id."""
        # 1. Fetch previous snapshot for change detection baseline
        prev_snapshot = await self.trend_repo.get_latest_snapshot(organization_id)

        # 2. Compute posture metrics using RiskIntelligenceEngine composite scores
        total_findings = len(findings)
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        risk_scores: List[float] = []

        for f in findings:
            if f.severity:
                sev_str = (
                    f.severity.value
                    if hasattr(f.severity, "value")
                    else str(f.severity)
                )
                if sev_str in severity_counts:
                    severity_counts[sev_str] += 1
            if f.risk and f.risk.composite_risk_score is not None:
                risk_scores.append(f.risk.composite_risk_score)

        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
        max_risk = max(risk_scores) if risk_scores else 0.0

        # Query total assets count for tenant
        assets_list, total_assets = await self.inventory_repo.list_inventory_assets(
            organization_id, limit=1000
        )

        # 3. Create & Persist Posture Snapshot (Organization isolated, assessment linked, timestamped)
        snapshot_model = await self.trend_repo.create_snapshot(
            organization_id=organization_id,
            assessment_job_id=assessment_job_id,
            total_assets=total_assets,
            total_findings=total_findings,
            critical_findings=severity_counts["CRITICAL"],
            high_findings=severity_counts["HIGH"],
            medium_findings=severity_counts["MEDIUM"],
            low_findings=severity_counts["LOW"],
            info_findings=severity_counts["INFO"],
            avg_risk_score=avg_risk,
            max_risk_score=max_risk,
            metadata={"target_url": context.target_url},
        )

        # 4. Perform Change Detection against baseline
        prev_titles: set[str] = set()
        if (
            prev_snapshot
            and isinstance(prev_snapshot, AssetSnapshotModel)
            and prev_snapshot.metadata_json
        ):
            prev_titles = set(prev_snapshot.metadata_json.get("finding_titles", []))

        # Store finding titles in snapshot metadata for future delta checks
        snapshot_model.metadata_json = {
            "target_url": context.target_url,
            "finding_titles": [f.title for f in findings],
        }
        await self.session.flush()

        detected_changes = self.change_engine.analyze_finding_lifecycle(
            findings, prev_titles
        )

        event_dtos: List[AssetChangeEventDTO] = []
        for ctype, title, desc in detected_changes:
            ev_model = await self.trend_repo.record_change_event(
                organization_id=organization_id,
                change_type=ctype,
                title=title,
                description=desc,
                assessment_job_id=assessment_job_id,
            )
            event_dtos.append(
                AssetChangeEventDTO(
                    id=str(ev_model.id),
                    assessment_job_id=str(assessment_job_id),
                    change_type=ev_model.change_type,
                    title=ev_model.title,
                    description=ev_model.description,
                    details=ev_model.details_json or {},
                    created_at=str(ev_model.created_at),
                )
            )

        snap_dto = AssetSnapshotDTO(
            id=str(snapshot_model.id),
            assessment_job_id=str(assessment_job_id),
            total_assets=snapshot_model.total_assets,
            total_findings=snapshot_model.total_findings,
            critical_findings=snapshot_model.critical_findings,
            high_findings=snapshot_model.high_findings,
            medium_findings=snapshot_model.medium_findings,
            low_findings=snapshot_model.low_findings,
            info_findings=snapshot_model.info_findings,
            avg_risk_score=snapshot_model.avg_risk_score,
            max_risk_score=snapshot_model.max_risk_score,
            created_at=str(snapshot_model.created_at),
        )

        logger.info(
            "continuous_monitoring.snapshot_created",
            snapshot_id=str(snapshot_model.id),
            job_id=str(assessment_job_id),
            total_findings=total_findings,
            changes_detected=len(event_dtos),
        )

        return snap_dto, event_dtos

    async def get_posture_trajectory(
        self, current_user: UserModel, limit: int = 30
    ) -> RiskTrajectoryResponse:
        """Query historical risk score trajectory and net risk delta for a tenant organization."""
        org_id = current_user.organization_id
        models = await self.trend_repo.list_snapshots(org_id, limit=limit)

        dtos: List[AssetSnapshotDTO] = [
            AssetSnapshotDTO(
                id=str(s.id),
                assessment_job_id=(
                    str(s.assessment_job_id) if s.assessment_job_id else None
                ),
                total_assets=s.total_assets,
                total_findings=s.total_findings,
                critical_findings=s.critical_findings,
                high_findings=s.high_findings,
                medium_findings=s.medium_findings,
                low_findings=s.low_findings,
                info_findings=s.info_findings,
                avg_risk_score=s.avg_risk_score,
                max_risk_score=s.max_risk_score,
                created_at=str(s.created_at),
            )
            for s in models
        ]

        cur_avg = dtos[0].avg_risk_score if dtos else 0.0
        prev_avg = dtos[1].avg_risk_score if len(dtos) > 1 else cur_avg
        net_delta = round(cur_avg - prev_avg, 2)

        direction = "STABLE"
        if net_delta > 0.5:
            direction = "INCREASING"
        elif net_delta < -0.5:
            direction = "DECREASING"

        return RiskTrajectoryResponse(
            current_avg_risk_score=cur_avg,
            previous_avg_risk_score=prev_avg,
            net_risk_delta=net_delta,
            risk_trend_direction=direction,
            total_snapshots=len(dtos),
            snapshots=dtos,
        )

    async def get_posture_timeline(
        self,
        current_user: UserModel,
        asset_node_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> PostureTimelineResponse:
        """Query aggregated security posture change event timeline for a tenant."""
        org_id = current_user.organization_id
        events = await self.trend_repo.list_change_events(
            org_id, asset_node_id=asset_node_id, limit=limit
        )

        dtos = [
            AssetChangeEventDTO(
                id=str(e.id),
                asset_node_id=str(e.asset_node_id) if e.asset_node_id else None,
                assessment_job_id=(
                    str(e.assessment_job_id) if e.assessment_job_id else None
                ),
                change_type=e.change_type,
                title=e.title,
                description=e.description,
                details=e.details_json or {},
                created_at=str(e.created_at),
            )
            for e in events
        ]

        return PostureTimelineResponse(total_events=len(dtos), events=dtos)
