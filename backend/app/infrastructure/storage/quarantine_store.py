"""MinIO Quarantine Storage Pipeline & Artifact Promotion Infrastructure (Phase 12.9)."""

import hashlib
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("vulnova.quarantine_store")


class QuarantineStorageService:
    """Manages dual-stage object lifecycle between quarantine staging bucket and production evidence storage."""

    def __init__(
        self,
        quarantine_dir: Optional[Path] = None,
        production_dir: Optional[Path] = None,
    ) -> None:
        self.quarantine_dir = quarantine_dir or Path("uploads/quarantine")
        self.production_dir = production_dir or Path("uploads/evidence")

        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.production_dir.mkdir(parents=True, exist_ok=True)

        self.quarantine_bucket = settings.minio_quarantine_bucket
        self.production_bucket = settings.minio_production_bucket

    def calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA-256 checksum of payload bytes."""
        return hashlib.sha256(content).hexdigest()

    async def stage_in_quarantine(
        self,
        organization_id: UUID,
        evidence_id: UUID,
        filename: str,
        content: bytes,
    ) -> str:
        """Stage newly uploaded unverified evidence file in quarantine bucket."""
        target_dir = self.quarantine_dir / str(organization_id) / str(evidence_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / filename
        file_path.write_bytes(content)

        relative_path = str(file_path.relative_to(self.quarantine_dir)).replace(
            "\\", "/"
        )

        logger.info(
            "evidence.quarantined.staged",
            organization_id=str(organization_id),
            evidence_id=str(evidence_id),
            path=relative_path,
            bucket=self.quarantine_bucket,
            size_bytes=len(content),
        )

        return relative_path

    async def read_quarantine_payload(self, relative_path: str) -> bytes:
        """Retrieve byte payload of evidence file held in quarantine storage."""
        file_path = self.quarantine_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(
                f"Quarantined evidence not found at path: {relative_path}"
            )
        return file_path.read_bytes()

    async def promote_to_production(
        self,
        relative_quarantine_path: str,
        organization_id: UUID,
        finding_id: UUID,
        filename: str,
    ) -> str:
        """Promote clean, verified evidence artifact from quarantine bucket to production storage."""
        src_path = self.quarantine_dir / relative_quarantine_path
        if not src_path.exists():
            raise FileNotFoundError(
                f"Source quarantine file missing: {relative_quarantine_path}"
            )

        target_dir = self.production_dir / str(organization_id) / str(finding_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        dest_path = target_dir / filename
        shutil.move(str(src_path), str(dest_path))

        prod_relative_path = str(dest_path.relative_to(self.production_dir)).replace(
            "\\", "/"
        )

        logger.info(
            "evidence.promoted",
            organization_id=str(organization_id),
            finding_id=str(finding_id),
            src=relative_quarantine_path,
            dest=prod_relative_path,
            bucket=self.production_bucket,
        )

        return prod_relative_path

    async def delete_quarantined_artifact(self, relative_quarantine_path: str) -> bool:
        """Permanently delete malicious or failed evidence from quarantine storage."""
        file_path = self.quarantine_dir / relative_quarantine_path
        if file_path.exists():
            file_path.unlink()
            logger.info("evidence.quarantine.deleted", path=relative_quarantine_path)
            return True
        return False
