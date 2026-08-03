"""Multi-Source Finding Correlation Engine.

Correlates discovery asset nodes, running technology stacks, and normalized security findings into a unified asset risk posture.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.entities.assessment import AssessmentContext, Finding
from app.infrastructure.database.models.asset_graph import AssetNodeModel
from app.infrastructure.database.repositories.asset_graph_repository import (
    AssetGraphRepository,
)
from app.infrastructure.discovery.ssrf_validator import extract_base_domain

logger = get_logger("vulnova.correlation_engine")


class AssessmentCorrelationEngine:
    """Correlation Engine linking assessment findings to Asset Graph nodes and updating asset risk posture."""

    def __init__(self) -> None:
        pass

    async def correlate_findings(
        self,
        findings: List[Finding],
        context: AssessmentContext,
        session: AsyncSession,
    ) -> List[Finding]:
        """Correlate security findings with tenant Asset Graph nodes and aggregate risk posture.

        Reuses risk scores computed by RiskIntelligenceEngine.
        Does not duplicate findings as graph nodes.
        Preserves asset_node_id as optional for backward compatibility.
        """
        org_id = context.organization_id
        target_str = context.target_url.rstrip("/")
        base_domain = extract_base_domain(target_str)

        graph_repo = AssetGraphRepository(session)

        # 1. Resolve or Create Target Domain Asset Node
        target_node: Optional[AssetNodeModel] = None
        try:
            target_node = await graph_repo.upsert_node(
                organization_id=org_id,
                node_type="TARGET_DOMAIN",
                name=base_domain,
                value=base_domain,
                metadata={"base_domain": base_domain, "target_url": target_str},
            )
        except Exception as e:
            logger.warning(
                "correlation_engine.asset_node_resolution_failed",
                error=str(e),
                target_url=target_str,
            )

        target_node_id: Optional[UUID] = target_node.id if target_node else None

        # 2. Correlate Findings to Asset Node (non-mandatory asset_node_id linkage)
        max_risk_score = 0.0
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}

        for f in findings:
            if not f.asset_node_id and target_node_id:
                f.asset_node_id = target_node_id

            if f.severity:
                sev_str = (
                    f.severity.value
                    if hasattr(f.severity, "value")
                    else str(f.severity)
                )
                if sev_str in severity_counts:
                    severity_counts[sev_str] += 1

            if f.risk and f.risk.composite_risk_score:
                if f.risk.composite_risk_score > max_risk_score:
                    max_risk_score = f.risk.composite_risk_score

        # 3. Aggregate Risk Posture Metadata on Asset Node if resolved
        if target_node and target_node_id:
            try:
                risk_level = "LOW"
                if max_risk_score >= 80.0:
                    risk_level = "CRITICAL"
                elif max_risk_score >= 60.0:
                    risk_level = "HIGH"
                elif max_risk_score >= 30.0:
                    risk_level = "MEDIUM"

                posture_meta = {
                    "composite_risk_score": round(max_risk_score, 2),
                    "max_risk_score": round(max_risk_score, 2),
                    "risk_level": risk_level,
                    "total_findings": len(findings),
                    "findings_by_severity": severity_counts,
                }

                await graph_repo.upsert_node(
                    organization_id=org_id,
                    node_type="TARGET_DOMAIN",
                    name=base_domain,
                    value=base_domain,
                    metadata=posture_meta,
                )

                logger.info(
                    "correlation_engine.asset_posture_updated",
                    asset_node_id=str(target_node_id),
                    risk_score=max_risk_score,
                    total_findings=len(findings),
                )
            except Exception as e:
                logger.error(
                    "correlation_engine.update_posture_failed",
                    error=str(e),
                    asset_node_id=str(target_node_id),
                )

        return findings
