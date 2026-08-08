"""Forensic Investigation Application Service."""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.repositories.incident_repository import (
    IncidentRepository,
)
from app.infrastructure.incident_response.dto import (
    ForensicCorrelatedEventDTO,
    ForensicInvestigationResultDTO,
)

logger = structlog.get_logger(__name__)


class ForensicInvestigationService:
    """Forensic investigation engine for audit trail correlation and timeline preservation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IncidentRepository(session)
        self.audit_service = AuditLogService(session)

    async def query_security_audit_events(
        self,
        organization_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogModel]:
        """Execute granular forensic queries on the immutable audit trail."""
        stmt = select(AuditLogModel).where(
            AuditLogModel.organization_id == organization_id
        )

        if start_time:
            stmt = stmt.where(AuditLogModel.created_at >= start_time)
        if end_time:
            stmt = stmt.where(AuditLogModel.created_at <= end_time)
        if user_id:
            stmt = stmt.where(AuditLogModel.actor_user_id == user_id)
        if action:
            stmt = stmt.where(AuditLogModel.action.ilike(f"%{action}%"))
        if resource_type:
            stmt = stmt.where(AuditLogModel.resource_type == resource_type)

        stmt = (
            stmt.options(selectinload(AuditLogModel.actor_user))
            .order_by(AuditLogModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def correlate_suspicious_activities(
        self,
        organization_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[ForensicCorrelatedEventDTO]:
        """Correlate audit logs into forensic attack clusters and threat indicators."""
        events = await self.query_security_audit_events(
            organization_id=organization_id,
            start_time=start_time,
            end_time=end_time,
            limit=500,
            offset=0,
        )

        # Cluster by Action Categories
        auth_failures: List[AuditLogModel] = []
        privilege_changes: List[AuditLogModel] = []
        token_revocations: List[AuditLogModel] = []
        bulk_exports: List[AuditLogModel] = []
        other_events: List[AuditLogModel] = []

        for e in events:
            act = e.action.lower()
            if "fail" in act or "unauthorized" in act:
                auth_failures.append(e)
            elif "role" in act or "permission" in act or "user.update" in act:
                privilege_changes.append(e)
            elif "revoke" in act or "token" in act or "api_key" in act:
                token_revocations.append(e)
            elif "export" in act or "download" in act:
                bulk_exports.append(e)
            else:
                other_events.append(e)

        clusters: List[ForensicCorrelatedEventDTO] = []

        if auth_failures:
            ips = [e.client_ip for e in auth_failures if e.client_ip is not None]
            actors = [e.actor_user_id for e in auth_failures if e.actor_user_id is not None]
            clusters.append(
                ForensicCorrelatedEventDTO(
                    correlation_key="AUTH_ANOMALIES",
                    event_count=len(auth_failures),
                    actions=[e.action for e in auth_failures[:10]],
                    actor_user_ids=list(set(actors)),
                    client_ips=list(set(ips)),
                    first_seen=auth_failures[-1].created_at,
                    last_seen=auth_failures[0].created_at,
                    risk_level="HIGH" if len(auth_failures) >= 5 else "MEDIUM",
                    description=f"Detected {len(auth_failures)} authentication failure/anomaly events across {len(set(ips))} distinct IPs.",
                )
            )

        if privilege_changes:
            ips = [e.client_ip for e in privilege_changes if e.client_ip is not None]
            actors = [e.actor_user_id for e in privilege_changes if e.actor_user_id is not None]
            clusters.append(
                ForensicCorrelatedEventDTO(
                    correlation_key="PRIVILEGE_ESCALATION",
                    event_count=len(privilege_changes),
                    actions=[e.action for e in privilege_changes[:10]],
                    actor_user_ids=list(set(actors)),
                    client_ips=list(set(ips)),
                    first_seen=privilege_changes[-1].created_at,
                    last_seen=privilege_changes[0].created_at,
                    risk_level="CRITICAL" if len(privilege_changes) >= 3 else "HIGH",
                    description=f"Identified {len(privilege_changes)} role and access governance modifications.",
                )
            )

        if token_revocations:
            ips = [e.client_ip for e in token_revocations if e.client_ip is not None]
            actors = [e.actor_user_id for e in token_revocations if e.actor_user_id is not None]
            clusters.append(
                ForensicCorrelatedEventDTO(
                    correlation_key="CREDENTIAL_ROTATION",
                    event_count=len(token_revocations),
                    actions=[e.action for e in token_revocations[:10]],
                    actor_user_ids=list(set(actors)),
                    client_ips=list(set(ips)),
                    first_seen=token_revocations[-1].created_at,
                    last_seen=token_revocations[0].created_at,
                    risk_level="MEDIUM",
                    description=f"Recorded {len(token_revocations)} credential or session revocation operations.",
                )
            )

        if bulk_exports:
            ips = [e.client_ip for e in bulk_exports if e.client_ip is not None]
            actors = [e.actor_user_id for e in bulk_exports if e.actor_user_id is not None]
            clusters.append(
                ForensicCorrelatedEventDTO(
                    correlation_key="DATA_EXFILTRATION_RISK",
                    event_count=len(bulk_exports),
                    actions=[e.action for e in bulk_exports[:10]],
                    actor_user_ids=list(set(actors)),
                    client_ips=list(set(ips)),
                    first_seen=bulk_exports[-1].created_at,
                    last_seen=bulk_exports[0].created_at,
                    risk_level="HIGH" if len(bulk_exports) >= 5 else "LOW",
                    description=f"Observed {len(bulk_exports)} bulk data export and download actions.",
                )
            )

        return clusters

    async def preserve_investigation_timeline(
        self,
        incident_id: UUID,
        organization_id: UUID,
    ) -> ForensicInvestigationResultDTO:
        """Generate a tamper-evident forensic package with SHA-256 integrity hash."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=True
        )
        if not incident:
            raise ResourceNotFoundException(
                f"Security incident '{incident_id}' not found."
            )

        timelines = incident.timelines or []
        clusters = await self.correlate_suspicious_activities(
            organization_id=organization_id,
            start_time=incident.detected_at,
            end_time=incident.resolved_at or datetime.now(timezone.utc),
        )

        all_ips = list(
            set(
                ip
                for cluster in clusters
                for ip in cluster.client_ips
                if ip is not None
            )
        )
        all_actors = list(
            set(
                actor
                for cluster in clusters
                for actor in cluster.actor_user_ids
                if actor is not None
            )
        )

        # Generate Cryptographic Digest for Evidence Preservation
        payload = {
            "incident_id": str(incident_id),
            "organization_id": str(organization_id),
            "title": incident.title,
            "severity": incident.severity,
            "detected_at": incident.detected_at.isoformat(),
            "timeline_count": len(timelines),
            "cluster_count": len(clusters),
            "suspicious_ips": all_ips,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        summary = (
            f"Forensic investigation package compiled for Incident '{incident.title}' "
            f"[{incident.severity}]. Preserved {len(timelines)} timeline events and "
            f"{len(clusters)} correlated security anomaly clusters across {len(all_ips)} IPs."
        )

        logger.info(
            "forensic_package_preserved",
            incident_id=str(incident_id),
            digest=digest,
            cluster_count=len(clusters),
        )

        return ForensicInvestigationResultDTO(
            incident_id=incident_id,
            organization_id=organization_id,
            investigation_timestamp=datetime.now(timezone.utc),
            total_events_analyzed=len(timelines),
            correlated_clusters=clusters,
            suspicious_ips=all_ips,
            affected_actors=all_actors,
            forensic_integrity_sha256=digest,
            summary=summary,
        )
