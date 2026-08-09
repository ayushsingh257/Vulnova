"""Plugin Zero-Trust Security Report Generator Service (Phase 12.7)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.plugin_security import (
    PluginExecutionAuditModel,
    PluginManifestModel,
    PluginSignatureModel,
    PluginTrustedPublisherModel,
)
from app.infrastructure.plugin_security.dto import (
    PluginCapability,
    PluginSecurityReportDTO,
    PublisherTrustStatus,
)


class PluginSecurityReportService:
    """Aggregates cryptographic signatures, capability permissions, and execution metrics into security reports."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_security_report(
        self, plugin_id: str, organization_id: UUID
    ) -> PluginSecurityReportDTO:
        """Generate comprehensive zero-trust security report for a registered plugin."""
        # 1. Fetch Manifest
        m_stmt = select(PluginManifestModel).where(
            PluginManifestModel.organization_id == organization_id,
            PluginManifestModel.plugin_id == plugin_id,
        )
        m_res = await self.session.execute(m_stmt)
        manifest = m_res.scalar_one_or_none()

        name = manifest.name if manifest else plugin_id
        version = manifest.version if manifest else "1.0.0"
        publisher_id = manifest.publisher_id if manifest else "unknown"
        created_at = manifest.created_at if manifest else None

        # Parse capabilities
        capabilities = []
        if manifest and manifest.capabilities_json:
            for cap_str in manifest.capabilities_json:
                try:
                    capabilities.append(PluginCapability(cap_str))
                except ValueError:
                    pass

        # 2. Fetch Publisher Trust
        pub_stmt = select(PluginTrustedPublisherModel).where(
            PluginTrustedPublisherModel.organization_id == organization_id,
            PluginTrustedPublisherModel.publisher_id == publisher_id,
        )
        pub_res = await self.session.execute(pub_stmt)
        publisher = pub_res.scalar_one_or_none()

        publisher_name = publisher.publisher_name if publisher else publisher_id
        trust_status = (
            PublisherTrustStatus(publisher.trust_status)
            if publisher
            else PublisherTrustStatus.UNTRUSTED
        )

        # 3. Fetch Latest Signature
        sig_stmt = (
            select(PluginSignatureModel)
            .where(
                PluginSignatureModel.organization_id == organization_id,
                PluginSignatureModel.plugin_id == plugin_id,
            )
            .order_by(PluginSignatureModel.created_at.desc())
        )
        sig_res = await self.session.execute(sig_stmt)
        sig = sig_res.scalar_one_or_none()

        sig_valid = sig.verification_status == "VERIFIED" if sig else False
        last_verified_at = sig.verified_at if sig else None

        # 4. Fetch Execution Statistics
        total_exec_stmt = select(func.count(PluginExecutionAuditModel.id)).where(
            PluginExecutionAuditModel.organization_id == organization_id,
            PluginExecutionAuditModel.plugin_id == plugin_id,
        )
        total_res = await self.session.execute(total_exec_stmt)
        total_executions = total_res.scalar_one() or 0

        blocked_exec_stmt = select(func.count(PluginExecutionAuditModel.id)).where(
            PluginExecutionAuditModel.organization_id == organization_id,
            PluginExecutionAuditModel.plugin_id == plugin_id,
            PluginExecutionAuditModel.execution_status.in_(
                ["BLOCKED", "PERMISSION_DENIED"]
            ),
        )
        blocked_res = await self.session.execute(blocked_exec_stmt)
        blocked_executions = blocked_res.scalar_one() or 0

        return PluginSecurityReportDTO(
            plugin_id=plugin_id,
            name=name,
            version=version,
            publisher_id=publisher_id,
            publisher_name=publisher_name,
            signature_valid=sig_valid,
            trust_status=trust_status,
            capabilities=capabilities,
            sandbox_enforced=True,
            last_verified_at=last_verified_at,
            total_executions=total_executions,
            blocked_executions=blocked_executions,
            created_at=created_at,
        )
