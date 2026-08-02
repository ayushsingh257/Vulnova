"""Repository for persisting and querying Evidence Artifacts."""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.entities.assessment import EvidenceArtifact
from app.infrastructure.database.models.assessment import EvidenceArtifactModel

logger = get_logger("vulnova.evidence_repository")


class EvidenceRepository:
    """Async repository managing tenant-isolated evidence artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_artifact(
        self, organization_id: UUID, artifact: EvidenceArtifact
    ) -> EvidenceArtifactModel:
        """Persist an evidence artifact record for a finding."""
        model = EvidenceArtifactModel(
            id=artifact.id,
            organization_id=organization_id,
            finding_id=artifact.finding_id,
            artifact_type=artifact.artifact_type.value,
            storage_path=artifact.storage_path,
            metadata_json=artifact.metadata,
            checksum=artifact.checksum,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def list_finding_artifacts(
        self, organization_id: UUID, finding_id: UUID
    ) -> List[EvidenceArtifactModel]:
        """List all evidence artifacts for a specific finding with tenant isolation."""
        stmt = (
            select(EvidenceArtifactModel)
            .where(
                EvidenceArtifactModel.organization_id == organization_id,
                EvidenceArtifactModel.finding_id == finding_id,
            )
            .order_by(EvidenceArtifactModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_artifact(self, organization_id: UUID, artifact_id: UUID) -> bool:
        """Delete an evidence artifact record ensuring tenant isolation."""
        stmt = select(EvidenceArtifactModel).where(
            EvidenceArtifactModel.organization_id == organization_id,
            EvidenceArtifactModel.id == artifact_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.flush()
            return True
        return False
