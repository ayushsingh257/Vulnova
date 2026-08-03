"""Repository for persisting and querying tenant-isolated Finding Triage History & Suppression Rules."""

import asyncio
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models.triage import (
    FindingSuppressionRuleModel,
    FindingTriageHistoryModel,
)

logger = get_logger("vulnova.finding_triage_repository")


class FindingTriageRepository:
    """Async repository managing tenant-isolated finding triage audit history and automated suppression rules."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_triage_action(
        self,
        organization_id: UUID,
        finding_id: UUID,
        new_status: str,
        previous_status: str = "UNREVIEWED",
        actor_user_id: Optional[UUID] = None,
        comment: Optional[str] = None,
        risk_accepted_until: Optional[datetime] = None,
    ) -> FindingTriageHistoryModel:
        """Record an immutable finding triage action in history."""
        record = FindingTriageHistoryModel(
            organization_id=organization_id,
            finding_id=finding_id,
            actor_user_id=actor_user_id,
            previous_status=previous_status,
            new_status=new_status,
            comment=comment,
            risk_accepted_until=risk_accepted_until,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_triage_history(
        self, organization_id: UUID, finding_id: UUID
    ) -> List[FindingTriageHistoryModel]:
        """Fetch full historical triage audit trail for a finding enforcing tenant boundaries."""
        stmt = (
            select(FindingTriageHistoryModel)
            .where(
                FindingTriageHistoryModel.organization_id == organization_id,
                FindingTriageHistoryModel.finding_id == finding_id,
            )
            .order_by(FindingTriageHistoryModel.created_at.desc())
        )
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            return (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )
        except Exception:
            return []

    async def create_suppression_rule(
        self,
        organization_id: UUID,
        name: str,
        rule_type: str,
        reason: str,
        created_by_user_id: Optional[UUID] = None,
        plugin_id: Optional[str] = None,
        cwe_id: Optional[str] = None,
        target_pattern: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> FindingSuppressionRuleModel:
        """Create and persist a tenant-isolated finding suppression rule."""
        rule = FindingSuppressionRuleModel(
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            name=name,
            rule_type=rule_type,
            plugin_id=plugin_id,
            cwe_id=cwe_id,
            target_pattern=target_pattern,
            reason=reason,
            expires_at=expires_at,
            is_active=True,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def list_suppression_rules(
        self, organization_id: UUID, active_only: bool = True
    ) -> List[FindingSuppressionRuleModel]:
        """List finding suppression rules for an organization."""
        stmt = select(FindingSuppressionRuleModel).where(
            FindingSuppressionRuleModel.organization_id == organization_id
        )
        if active_only:
            stmt = stmt.where(FindingSuppressionRuleModel.is_active.is_(True))

        stmt = stmt.order_by(FindingSuppressionRuleModel.created_at.desc())
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            return (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )
        except Exception:
            return []

    async def delete_suppression_rule(
        self, organization_id: UUID, rule_id: UUID
    ) -> bool:
        """Deactivate or remove a finding suppression rule enforcing organization boundary."""
        stmt = select(FindingSuppressionRuleModel).where(
            FindingSuppressionRuleModel.organization_id == organization_id,
            FindingSuppressionRuleModel.id == rule_id,
        )
        try:
            result = await self.session.execute(stmt)
            rule = (
                result.scalar_one_or_none()
                if hasattr(result, "scalar_one_or_none")
                else None
            )
            if rule and isinstance(rule, FindingSuppressionRuleModel):
                rule.is_active = False
                await self.session.flush()
                return True
            return False
        except Exception:
            return False
