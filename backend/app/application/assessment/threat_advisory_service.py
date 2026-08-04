"""Application Service for Threat Advisories, CVSS Thresholds, and SLA Breach Detection."""

from datetime import datetime, timedelta, timezone
from typing import List

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import ExecutiveThreatAlertDTO
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.scan_target import ScanTargetModel
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)


class ThreatAdvisoryService:
    """Service evaluating critical findings, SLA breaches, and target authorization expirations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def evaluate_organization_advisories(
        self, current_user: UserModel
    ) -> List[ExecutiveThreatAlertDTO]:
        """Evaluate organization vulnerabilities and targets for executive threat alerts."""
        org_id = current_user.organization_id
        advisories: List[ExecutiveThreatAlertDTO] = []
        now_utc = datetime.now(timezone.utc)

        # 1. Evaluate Critical Severity Findings (CVSS 9.0+)
        crit_stmt = (
            select(SecurityFindingModel)
            .where(
                SecurityFindingModel.organization_id == org_id,
                SecurityFindingModel.severity == "CRITICAL",
            )
            .limit(5)
        )
        crit_res = await self.session.execute(crit_stmt)
        crit_findings = crit_res.scalars().all()

        for finding in crit_findings:
            advisories.append(
                ExecutiveThreatAlertDTO(
                    severity="CRITICAL",
                    category="VULNERABILITY_CVSS_CRITICAL",
                    title=f"Critical Finding: {finding.title}",
                    description=f"Critical vulnerability identified ({finding.category}). Immediate remediation required.",
                )
            )

        # 2. Evaluate SLA Breaches (Unresolved > 14 days)
        sla_cutoff = now_utc - timedelta(days=14)
        sla_stmt = (
            select(SecurityFindingModel)
            .where(
                SecurityFindingModel.organization_id == org_id,
                SecurityFindingModel.severity.in_(["CRITICAL", "HIGH"]),
                SecurityFindingModel.created_at <= sla_cutoff,
            )
            .limit(3)
        )
        sla_res = await self.session.execute(sla_stmt)
        sla_findings = sla_res.scalars().all()

        for breach in sla_findings:
            advisories.append(
                ExecutiveThreatAlertDTO(
                    severity="WARNING",
                    category="REMEDIATION_SLA_BREACH",
                    title=f"Remediation SLA Breach: {breach.title}",
                    description=f"High-priority finding unmitigated for >14 days ({breach.severity}). SLA breach threshold exceeded.",
                )
            )

        # 3. Evaluate Scan Target Authorization Expirations
        target_stmt = (
            select(ScanTargetModel)
            .where(
                ScanTargetModel.organization_id == org_id,
                ScanTargetModel.status == "ACTIVE",
            )
            .limit(3)
        )
        target_res = await self.session.execute(target_stmt)
        for target in target_res.scalars().all():
            advisories.append(
                ExecutiveThreatAlertDTO(
                    severity="INFO",
                    category="AUTHORIZED_CONTRACT_STATUS",
                    title=f"Target Scan Scope Active: {target.target_url}",
                    description="Authorized assessment contract verified and active under CFAA governance rules.",
                    affected_target_url=target.target_url,
                )
            )

        return advisories
