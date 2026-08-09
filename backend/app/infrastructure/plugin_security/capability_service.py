"""Plugin Capability Manifest & Permission Governance Service (Phase 12.7)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ValidationException
from app.core.logging import get_logger
from app.infrastructure.database.models.plugin_security import PluginManifestModel
from app.infrastructure.plugin_security.dto import (
    PluginCapability,
    PluginManifestDTO,
)

logger = get_logger("vulnova.plugin_capability_service")


class PluginCapabilityService:
    """Validates plugin manifests, registers capability sets, and enforces runtime permissions."""

    ALL_CAPABILITIES: Set[PluginCapability] = {
        PluginCapability.NETWORK_HTTP,
        PluginCapability.NETWORK_DNS,
        PluginCapability.NETWORK_TCP,
        PluginCapability.FILESYSTEM_READ,
        PluginCapability.FILESYSTEM_WRITE,
        PluginCapability.PROCESS_EXECUTE,
    }

    # Highly sensitive capabilities requiring elevated scrutiny
    SENSITIVE_CAPABILITIES: Set[PluginCapability] = {
        PluginCapability.FILESYSTEM_WRITE,
        PluginCapability.PROCESS_EXECUTE,
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditLogService(session)

    def parse_and_validate_manifest(
        self, manifest_dict: Dict[str, Any]
    ) -> PluginManifestDTO:
        """Parse raw manifest JSON dictionary into validated PluginManifestDTO."""
        try:
            # Parse declared capabilities
            raw_caps = manifest_dict.get("capabilities", [])
            parsed_caps: List[PluginCapability] = []
            for cap_str in raw_caps:
                try:
                    parsed_caps.append(PluginCapability(cap_str))
                except ValueError as err:
                    raise ValidationException(
                        f"Unsupported plugin capability declared: '{cap_str}'. Supported: {[c.value for c in self.ALL_CAPABILITIES]}"
                    ) from err

            manifest = PluginManifestDTO(
                plugin_id=manifest_dict.get("plugin_id")
                or manifest_dict.get("name", ""),
                name=manifest_dict.get("name", ""),
                version=manifest_dict.get("version", "1.0.0"),
                publisher_id=manifest_dict.get("publisher_id")
                or manifest_dict.get("publisher", ""),
                description=manifest_dict.get("description", ""),
                entrypoint=manifest_dict.get("entrypoint", ""),
                capabilities=parsed_caps,
                package_hash=manifest_dict.get("package_hash", ""),
                min_platform_version=manifest_dict.get("min_platform_version"),
                signature=manifest_dict.get("signature"),
            )

            if (
                not manifest.plugin_id
                or not manifest.publisher_id
                or not manifest.package_hash
            ):
                raise ValidationException(
                    "Manifest must contain plugin_id, publisher_id, and package_hash."
                )

            return manifest
        except ValidationException:
            raise
        except Exception as exc:
            raise ValidationException(
                f"Invalid plugin manifest format: {str(exc)}"
            ) from exc

    async def register_manifest(
        self,
        manifest: PluginManifestDTO,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> PluginManifestDTO:
        """Persist or update plugin capability manifest in database."""
        now = datetime.now(timezone.utc)
        stmt = select(PluginManifestModel).where(
            PluginManifestModel.organization_id == organization_id,
            PluginManifestModel.plugin_id == manifest.plugin_id,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        caps_json = [c.value for c in manifest.capabilities]

        if existing:
            existing.name = manifest.name
            existing.version = manifest.version
            existing.publisher_id = manifest.publisher_id
            existing.description = manifest.description
            existing.entrypoint = manifest.entrypoint
            existing.capabilities_json = caps_json
            existing.package_hash = manifest.package_hash
            existing.min_platform_version = manifest.min_platform_version
        else:
            model = PluginManifestModel(
                id=uuid4(),
                organization_id=organization_id,
                plugin_id=manifest.plugin_id,
                name=manifest.name,
                version=manifest.version,
                publisher_id=manifest.publisher_id,
                description=manifest.description,
                entrypoint=manifest.entrypoint,
                capabilities_json=caps_json,
                package_hash=manifest.package_hash,
                min_platform_version=manifest.min_platform_version,
                created_at=now,
            )
            self.session.add(model)

        await self.session.flush()

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="plugin.manifest_registered",
            resource_type="plugin_manifest",
            resource_id=manifest.plugin_id,
            actor_user_id=actor_user_id,
            details={
                "name": manifest.name,
                "version": manifest.version,
                "publisher_id": manifest.publisher_id,
                "capabilities": caps_json,
            },
        )

        return manifest

    async def get_manifest(
        self, plugin_id: str, organization_id: UUID
    ) -> Optional[PluginManifestDTO]:
        """Fetch a registered plugin manifest by plugin_id."""
        stmt = select(PluginManifestModel).where(
            PluginManifestModel.organization_id == organization_id,
            PluginManifestModel.plugin_id == plugin_id,
        )
        res = await self.session.execute(stmt)
        m = res.scalar_one_or_none()
        if not m:
            return None

        caps = [
            PluginCapability(c)
            for c in m.capabilities_json
            if c in [x.value for x in self.ALL_CAPABILITIES]
        ]
        return PluginManifestDTO(
            plugin_id=m.plugin_id,
            name=m.name,
            version=m.version,
            publisher_id=m.publisher_id,
            description=m.description,
            entrypoint=m.entrypoint,
            capabilities=caps,
            package_hash=m.package_hash,
            min_platform_version=m.min_platform_version,
        )

    def enforce_runtime_permissions(
        self,
        plugin_id: str,
        declared_capabilities: List[PluginCapability],
        required_capabilities: List[PluginCapability],
    ) -> None:
        """Enforce that runtime operations only execute capabilities declared in the verified manifest."""
        declared_set = set(declared_capabilities)
        undeclared = [c for c in required_capabilities if c not in declared_set]

        if undeclared:
            undeclared_str = ", ".join(c.value for c in undeclared)
            logger.warning(
                "plugin_capability.permission_denied",
                plugin_id=plugin_id,
                undeclared=undeclared_str,
            )
            raise ValidationException(
                f"Permission Denied: Plugin '{plugin_id}' attempted to execute undeclared capabilities [{undeclared_str}]."
            )
