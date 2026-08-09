"""SQLAlchemy Repository for Target Verification Challenges."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.target_verification_challenge import (
    TargetVerificationChallengeModel,
)


class TargetVerificationRepository:
    """Repository managing target ownership verification challenges in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_challenge(
        self, challenge: TargetVerificationChallengeModel
    ) -> TargetVerificationChallengeModel:
        """Persist a new target verification challenge."""
        self.session.add(challenge)
        await self.session.flush()
        return challenge

    async def get_challenge_by_id(
        self, challenge_id: UUID, organization_id: UUID
    ) -> Optional[TargetVerificationChallengeModel]:
        """Fetch a specific verification challenge enforcing tenant boundaries."""
        query = select(TargetVerificationChallengeModel).where(
            TargetVerificationChallengeModel.id == challenge_id,
            TargetVerificationChallengeModel.organization_id == organization_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_challenge_for_target(
        self, target_id: UUID, organization_id: UUID
    ) -> Optional[TargetVerificationChallengeModel]:
        """Fetch the most recent verification challenge for a target asset."""
        query = (
            select(TargetVerificationChallengeModel)
            .where(
                TargetVerificationChallengeModel.target_id == target_id,
                TargetVerificationChallengeModel.organization_id == organization_id,
            )
            .order_by(TargetVerificationChallengeModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        challenge_id: UUID,
        status: str,
        verification_metadata: Optional[str] = None,
        verified_at: Optional[datetime] = None,
    ) -> Optional[TargetVerificationChallengeModel]:
        """Update challenge state (VERIFIED, FAILED, EXPIRED)."""
        values: Dict[str, Any] = {
            "status": status,
        }
        if verification_metadata is not None:
            values["verification_metadata"] = verification_metadata
        if verified_at is not None:
            values["verified_at"] = verified_at

        stmt = (
            update(TargetVerificationChallengeModel)
            .where(TargetVerificationChallengeModel.id == challenge_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)
        await self.session.flush()

        query = select(TargetVerificationChallengeModel).where(
            TargetVerificationChallengeModel.id == challenge_id
        )
        res = await self.session.execute(query)
        model = res.scalar_one_or_none()
        if model:
            model.status = status
            if verified_at is not None:
                model.verified_at = verified_at
            if verification_metadata is not None:
                model.verification_metadata = verification_metadata
        return model
