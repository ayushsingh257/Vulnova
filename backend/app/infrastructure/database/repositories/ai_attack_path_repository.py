"""Repository managing tenant-isolated AI Attack Paths and Steps persistence."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.infrastructure.database.models.ai_attack_path import (
    AIAttackPathModel,
    AIAttackPathStepModel,
)

logger = get_logger("vulnova.ai_attack_path_repository")


class AIAttackPathRepository:
    """Async repository for tenant-isolated AI Attack Path and Step persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_attack_path(
        self,
        organization_id: UUID,
        root_finding_id: UUID,
        title: str,
        attack_summary: str,
        composite_risk_score: float,
        model_used: str,
        provider_used: str,
        prompt_version: int,
        confidence_score: float = 1.0,
        source_asset_id: Optional[UUID] = None,
        target_asset_id: Optional[UUID] = None,
        status: str = "GENERATED",
        error_message: Optional[str] = None,
        steps_data: Optional[List[Dict[str, Any]]] = None,
    ) -> AIAttackPathModel:
        """Create and persist an AI Attack Path with child step models."""
        path_model = AIAttackPathModel(
            organization_id=organization_id,
            root_finding_id=root_finding_id,
            source_asset_id=source_asset_id,
            target_asset_id=target_asset_id,
            title=title,
            attack_summary=attack_summary,
            composite_risk_score=composite_risk_score,
            confidence_score=confidence_score,
            model_used=model_used,
            provider_used=provider_used,
            prompt_version=prompt_version,
            status=status,
            error_message=error_message,
        )
        self.session.add(path_model)
        await self.session.flush()

        if steps_data:
            for sdata in steps_data:
                step_model = AIAttackPathStepModel(
                    attack_path_id=path_model.id,
                    sequence_number=sdata.get("sequence_number", 1),
                    step_type=sdata.get("step_type", "INITIAL_ACCESS"),
                    asset_node_id=sdata.get("asset_node_id"),
                    finding_id=sdata.get("finding_id"),
                    title=sdata.get("title", ""),
                    description=sdata.get("description", ""),
                    mitre_tactic=sdata.get("mitre_tactic", ""),
                    mitre_technique_id=sdata.get("mitre_technique_id", ""),
                    mitre_technique_name=sdata.get("mitre_technique_name", ""),
                    attacker_action=sdata.get("attacker_action", ""),
                    required_privilege=sdata.get("required_privilege", ""),
                    evidence_reference=sdata.get("evidence_reference"),
                    confidence_score=sdata.get("confidence_score", 1.0),
                )
                self.session.add(step_model)
            await self.session.flush()

        # Reload with steps eagerly loaded
        return await self.get_attack_path_by_id(organization_id, path_model.id)  # type: ignore[return-value]

    async def get_attack_path_by_id(
        self, organization_id: UUID, path_id: UUID
    ) -> Optional[AIAttackPathModel]:
        """Retrieve a single attack path by ID with child steps (tenant-isolated)."""
        stmt = (
            select(AIAttackPathModel)
            .options(selectinload(AIAttackPathModel.steps))
            .where(
                AIAttackPathModel.id == path_id,
                AIAttackPathModel.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_attack_paths_by_finding(
        self, organization_id: UUID, finding_id: UUID
    ) -> List[AIAttackPathModel]:
        """List attack paths associated with a root finding (tenant-isolated)."""
        stmt = (
            select(AIAttackPathModel)
            .options(selectinload(AIAttackPathModel.steps))
            .where(
                AIAttackPathModel.organization_id == organization_id,
                AIAttackPathModel.root_finding_id == finding_id,
            )
            .order_by(AIAttackPathModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_attack_paths(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIAttackPathModel]:
        """List attack paths for an organization with pagination."""
        stmt = (
            select(AIAttackPathModel)
            .options(selectinload(AIAttackPathModel.steps))
            .where(
                AIAttackPathModel.organization_id == organization_id,
            )
            .order_by(AIAttackPathModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_review_status(
        self,
        organization_id: UUID,
        path_id: UUID,
        status: str,
        reviewer_id: UUID,
        review_notes: Optional[str] = None,
    ) -> Optional[AIAttackPathModel]:
        """Update analyst review status and feedback notes on an attack path."""
        model = await self.get_attack_path_by_id(organization_id, path_id)
        if not model:
            return None

        model.status = status
        model.reviewed_by = reviewer_id
        model.review_notes = review_notes
        model.reviewed_at = datetime.utcnow()
        await self.session.flush()
        return model
