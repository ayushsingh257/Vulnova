"""Evidence Artifact Storage Layer for storing visual, HTTP, and browser proof files."""

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.domain.entities.assessment import EvidenceArtifact, EvidenceType

logger = get_logger("vulnova.evidence_store")


class EvidenceArtifactStorage:
    """Storage provider for persisting and retrieving finding evidence artifacts."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        if base_dir:
            self.base_dir = base_dir
        else:
            # Fallback to local storage root directory
            self.base_dir = Path("uploads/evidence")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA-256 checksum of artifact byte content."""
        return hashlib.sha256(content).hexdigest()

    async def save_artifact(
        self,
        organization_id: UUID,
        finding_id: UUID,
        artifact_type: EvidenceType,
        filename: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceArtifact:
        """Save evidence artifact content bytes to storage and return EvidenceArtifact domain object."""
        checksum = self.calculate_checksum(content)

        # Build folder structure: <base_dir>/<org_id>/<finding_id>/<filename>
        target_dir = self.base_dir / str(organization_id) / str(finding_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / filename
        file_path.write_bytes(content)

        relative_path = str(file_path.relative_to(self.base_dir)).replace("\\", "/")

        artifact = EvidenceArtifact(
            organization_id=organization_id,
            finding_id=finding_id,
            artifact_type=artifact_type,
            storage_path=relative_path,
            metadata=metadata or {},
            checksum=checksum,
        )

        logger.info(
            "evidence_store.artifact_saved",
            organization_id=str(organization_id),
            finding_id=str(finding_id),
            artifact_type=artifact_type.value,
            path=relative_path,
            checksum=checksum[:8],
        )

        return artifact

    async def retrieve_artifact(self, storage_path: str) -> bytes:
        """Retrieve evidence artifact content bytes from storage path."""
        file_path = self.base_dir / storage_path
        if not file_path.exists():
            raise FileNotFoundError(
                f"Evidence artifact not found at path: {storage_path}"
            )
        return file_path.read_bytes()

    async def delete_artifact(self, storage_path: str) -> bool:
        """Delete evidence artifact from storage path."""
        file_path = self.base_dir / storage_path
        if file_path.exists():
            file_path.unlink()
            logger.info("evidence_store.artifact_deleted", path=storage_path)
            return True
        return False
