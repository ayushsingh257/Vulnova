"""Application Service for Attack Surface Asset Graph & Relationship Mapping."""

import time
from uuid import UUID

from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.discovery.dto import (
    AssetGraphResponse,
    AssetNodeDTO,
    AssetRelationshipDTO,
    BuildAssetGraphRequest,
    CrawlRequest,
    SubdomainScanRequest,
    TechnologyScanRequest,
)
from app.application.discovery.services import DiscoveryService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.asset_graph_repository import (
    AssetGraphRepository,
)
from app.infrastructure.discovery.ssrf_validator import (
    extract_base_domain,
    is_safe_target_url,
)

logger = get_logger("vulnova.asset_graph_service")


class AssetGraphService:
    """Application Service managing Attack Surface Asset Graph building and querying."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssetGraphRepository(session)
        self.audit_service = AuditLogService(session)
        self.discovery_service = DiscoveryService(session)

    async def build_asset_graph(
        self, req: BuildAssetGraphRequest, current_user: UserModel
    ) -> AssetGraphResponse:
        """Build or update Attack Surface Asset Graph for a target domain."""
        start_time = time.time()
        base_domain = extract_base_domain(req.target_domain)
        org_id = current_user.organization_id

        # 1. Pre-validate SSRF Safety
        target_http_url = f"https://{base_domain}"
        is_safe, reason = is_safe_target_url(target_http_url)
        if not is_safe:
            logger.warning(
                "asset_graph.build_rejected_unsafe_target",
                target_domain=base_domain,
                reason=reason,
                org_id=str(org_id),
            )
            await self.audit_service.record_event(
                organization_id=org_id,
                action="asset_graph.build_rejected",
                resource_type="domain",
                resource_id=base_domain,
                actor_user_id=current_user.id,
                details={"target_domain": base_domain, "reason": reason},
            )
            raise ValidationException(f"Target domain is prohibited: {reason}")

        # 2. Record Build Started Audit Event
        await self.audit_service.record_event(
            organization_id=org_id,
            action="asset_graph.build_started",
            resource_type="domain",
            resource_id=base_domain,
            actor_user_id=current_user.id,
            details={"target_domain": base_domain},
        )

        # 3. Create Root Target Domain Node & Org Node
        domain_node = await self.repo.upsert_node(
            organization_id=org_id,
            node_type="TARGET_DOMAIN",
            name=base_domain,
            value=base_domain,
            metadata={"base_domain": base_domain},
        )

        # 4. Include Subdomain & DNS Intelligence
        if req.include_dns:
            try:
                sub_res = await self.discovery_service.discover_subdomains(
                    SubdomainScanRequest(target_domain=base_domain), current_user
                )
                for sub in sub_res.discovered_subdomains:
                    sub_node = await self.repo.upsert_node(
                        organization_id=org_id,
                        node_type="SUBDOMAIN",
                        name=sub.subdomain,
                        value=sub.subdomain,
                        metadata={"sources": sub.sources},
                    )
                    await self.repo.create_relationship(
                        organization_id=org_id,
                        source_node_id=sub_node.id,
                        target_node_id=domain_node.id,
                        relationship_type="BELONGS_TO",
                    )

                    # IP Address nodes
                    for ip_info in sub.ip_addresses:
                        ip_node = await self.repo.upsert_node(
                            organization_id=org_id,
                            node_type="IP_ADDRESS",
                            name=ip_info.value,
                            value=ip_info.value,
                            metadata={
                                "classification": ip_info.classification,
                                "is_internal": ip_info.is_internal,
                                "is_egress_safe": ip_info.is_egress_safe,
                            },
                        )
                        await self.repo.create_relationship(
                            organization_id=org_id,
                            source_node_id=sub_node.id,
                            target_node_id=ip_node.id,
                            relationship_type="RESOLVES_TO",
                        )
            except Exception as e:
                logger.warning("asset_graph.dns_ingestion_failed", error=str(e))

        # 5. Include Web Crawling Findings
        if req.include_crawls:
            try:
                crawl_req = CrawlRequest(target_url=HttpUrl(target_http_url))
                crawl_res = await self.discovery_service.crawl_target(
                    crawl_req, current_user
                )
                for u in crawl_res.discovered_urls:
                    url_node = await self.repo.upsert_node(
                        organization_id=org_id,
                        node_type="URL_ENDPOINT",
                        name=u.url,
                        value=u.url,
                        metadata={
                            "method": u.method,
                            "depth": u.depth,
                            "title": u.title,
                        },
                    )
                    await self.repo.create_relationship(
                        organization_id=org_id,
                        source_node_id=domain_node.id,
                        target_node_id=url_node.id,
                        relationship_type="HAS_ENDPOINT",
                    )
            except Exception as e:
                logger.warning("asset_graph.crawl_ingestion_failed", error=str(e))

        # 6. Include Technology Fingerprinting Findings
        if req.include_tech:
            try:
                tech_req = TechnologyScanRequest(target_url=HttpUrl(target_http_url))
                tech_res = await self.discovery_service.discover_technologies(
                    tech_req, current_user
                )
                for tech in tech_res.detected_technologies:
                    tech_node = await self.repo.upsert_node(
                        organization_id=org_id,
                        node_type="TECHNOLOGY",
                        name=tech.name,
                        value=f"{tech.name}:{tech.version or 'latest'}",
                        metadata={"category": tech.category, "version": tech.version},
                    )
                    await self.repo.create_relationship(
                        organization_id=org_id,
                        source_node_id=domain_node.id,
                        target_node_id=tech_node.id,
                        relationship_type="RUNS_TECH",
                    )
            except Exception as e:
                logger.warning("asset_graph.tech_ingestion_failed", error=str(e))

        # 7. Query Persisted Graph Nodes and Edges
        nodes, rels = await self.repo.get_graph_by_domain(org_id, base_domain)

        nodes_dto = [
            AssetNodeDTO(
                id=str(n.id),
                node_type=str(n.node_type),
                name=str(n.name),
                value=str(n.value),
                metadata=dict(n.metadata_json or {}),
            )
            for n in nodes
        ]
        rels_dto = [
            AssetRelationshipDTO(
                id=str(r.id),
                source_node_id=str(r.source_node_id),
                target_node_id=str(r.target_node_id),
                relationship_type=str(r.relationship_type),
                metadata=dict(r.metadata_json or {}),
            )
            for r in rels
        ]

        duration = round(time.time() - start_time, 2)

        # 8. Record Build Completed Audit Event
        await self.audit_service.record_event(
            organization_id=org_id,
            action="asset_graph.build_completed",
            resource_type="domain",
            resource_id=base_domain,
            actor_user_id=current_user.id,
            details={
                "target_domain": base_domain,
                "total_nodes": len(nodes_dto),
                "total_relationships": len(rels_dto),
                "duration_seconds": duration,
            },
        )

        return AssetGraphResponse(
            target_domain=base_domain,
            total_nodes=len(nodes_dto),
            total_relationships=len(rels_dto),
            nodes=nodes_dto,
            relationships=rels_dto,
            duration_seconds=duration,
        )

    async def get_node_details(
        self, node_id: UUID, current_user: UserModel
    ) -> AssetNodeDTO:
        """Fetch asset node details enforcing multi-tenant boundaries."""
        node = await self.repo.get_node_by_id(current_user.organization_id, node_id)
        if not node:
            raise ResourceNotFoundException(f"Asset node '{node_id}' not found")

        return AssetNodeDTO(
            id=str(node.id),
            node_type=str(node.node_type),
            name=str(node.name),
            value=str(node.value),
            metadata=dict(node.metadata_json or {}),
        )
