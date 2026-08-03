"""Application Service managing Enterprise Asset Inventory, Technology Mappings, and Posture Intelligence."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import (
    AssetDetailResponse,
    AssetInventoryDTO,
    AssetInventoryResponse,
    EvidenceArtifactDTO,
    FindingDTO,
)
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.asset_inventory_repository import (
    AssetInventoryRepository,
)
from app.infrastructure.database.repositories.evidence_repository import (
    EvidenceRepository,
)

logger = get_logger("vulnova.asset_inventory_service")


class AssetInventoryService:
    """Application Service orchestrating tenant-isolated asset inventory posture and finding correlation lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssetInventoryRepository(session)
        self.evidence_repo = EvidenceRepository(session)

    async def list_asset_inventory(
        self,
        current_user: UserModel,
        node_type: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> AssetInventoryResponse:
        """List enterprise asset inventory nodes enriched with technology stacks and risk posture."""
        org_id = current_user.organization_id
        offset = (page - 1) * limit

        nodes, total = await self.repo.list_inventory_assets(
            organization_id=org_id,
            node_type=node_type,
            search=search,
            limit=limit,
            offset=offset,
        )

        items: List[AssetInventoryDTO] = []
        for n in nodes:
            meta = n.metadata_json or {}
            risk_score = float(
                meta.get("composite_risk_score", meta.get("risk_score", 0.0))
            )

            if min_risk_score is not None and risk_score < min_risk_score:
                continue

            tech_nodes = await self.repo.list_technologies_by_asset(org_id, n.id)
            tech_names = [t.name for t in tech_nodes]

            findings_count = int(meta.get("total_findings", 0))
            severity_counts = meta.get(
                "findings_by_severity",
                {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0},
            )

            risk_level = meta.get("risk_level", "LOW")

            items.append(
                AssetInventoryDTO(
                    id=str(n.id),
                    node_type=n.node_type,
                    name=n.name,
                    value=n.value,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    total_findings=findings_count,
                    findings_by_severity=severity_counts,
                    technologies=tech_names,
                    created_at=str(n.created_at),
                    updated_at=str(n.updated_at),
                )
            )

        return AssetInventoryResponse(total=len(items), items=items)

    async def get_asset_detail(
        self, current_user: UserModel, asset_id: UUID
    ) -> AssetDetailResponse:
        """Query detailed inventory summary for a single asset node."""
        org_id = current_user.organization_id
        node = await self.repo.get_asset_node_by_id(org_id, asset_id)
        if not node:
            raise ResourceNotFoundException(f"Asset node '{asset_id}' not found")

        tech_nodes = await self.repo.list_technologies_by_asset(org_id, asset_id)
        tech_list = [
            {
                "id": str(t.id),
                "name": t.name,
                "category": (t.metadata_json or {}).get("category", "TECHNOLOGY"),
                "version": (t.metadata_json or {}).get("version"),
            }
            for t in tech_nodes
        ]

        findings_models = await self.repo.list_findings_by_asset(
            org_id, asset_id, target_value=node.value
        )
        finding_dtos: List[FindingDTO] = []
        for f in findings_models:
            art_models = await self.evidence_repo.list_finding_artifacts(org_id, f.id)
            art_dtos = [
                EvidenceArtifactDTO(
                    id=str(a.id),
                    finding_id=str(a.finding_id),
                    artifact_type=a.artifact_type,
                    storage_path=a.storage_path,
                    metadata=a.metadata_json or {},
                    checksum=a.checksum,
                    created_at=str(a.created_at),
                )
                for a in art_models
            ]
            finding_dtos.append(
                FindingDTO(
                    id=str(f.id),
                    assessment_job_id=str(f.assessment_job_id),
                    plugin_id=f.plugin_id,
                    title=f.title,
                    description=f.description,
                    severity=f.severity,
                    category=f.category,
                    cve_id=f.cve_id,
                    cwe_id=f.cwe_id,
                    remediation=f.remediation,
                    evidence=f.evidence_json or {},
                    cvss=f.cvss_json,
                    epss=f.epss_json,
                    risk_score=f.risk_score,
                    confidence=f.confidence,
                    is_duplicate=f.is_duplicate,
                    canonical_finding_id=(
                        str(f.canonical_finding_id) if f.canonical_finding_id else None
                    ),
                    evidence_count=len(art_dtos),
                    evidence_available=len(art_dtos) > 0,
                    artifacts=art_dtos,
                    created_at=str(f.created_at),
                )
            )

        rel_models = await self.repo.list_asset_relationships(org_id, asset_id)
        rel_list = [
            {
                "id": str(r.id),
                "source_node_id": str(r.source_node_id),
                "target_node_id": str(r.target_node_id),
                "relationship_type": r.relationship_type,
                "metadata": r.metadata_json or {},
            }
            for r in rel_models
        ]

        meta = node.metadata_json or {}
        risk_score = float(
            meta.get("composite_risk_score", meta.get("risk_score", 0.0))
        )
        risk_level = meta.get("risk_level", "LOW")

        asset_dto = AssetInventoryDTO(
            id=str(node.id),
            node_type=node.node_type,
            name=node.name,
            value=node.value,
            risk_score=risk_score,
            risk_level=risk_level,
            total_findings=len(finding_dtos),
            findings_by_severity=meta.get("findings_by_severity", {}),
            technologies=[t["name"] for t in tech_list],
            created_at=str(node.created_at),
            updated_at=str(node.updated_at),
        )

        return AssetDetailResponse(
            asset=asset_dto,
            technologies=tech_list,
            findings=finding_dtos,
            relationships=rel_list,
        )

    async def get_asset_findings(
        self, current_user: UserModel, asset_id: UUID
    ) -> List[FindingDTO]:
        """List findings affecting a specific asset node."""
        detail = await self.get_asset_detail(current_user, asset_id)
        return detail.findings

    async def get_asset_technologies(
        self, current_user: UserModel, asset_id: UUID
    ) -> List[Dict[str, Any]]:
        """List technologies running on a specific asset node."""
        detail = await self.get_asset_detail(current_user, asset_id)
        return detail.technologies
