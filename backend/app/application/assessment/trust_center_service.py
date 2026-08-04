"""Application Service for Public Trust Center, OWASP ASVS Mappings, and Security Disclosures."""

import json
from datetime import datetime, timezone
from typing import Any, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import (
    SecurityDisclosureResponse,
    SecurityPracticeItemDTO,
    TrustCenterSummaryResponse,
)
from app.domain.entities.trust_center import (
    ASVSCategory,
    SecurityDisclosureInfo,
    SecurityPracticeItem,
    SystemHealthStatus,
)
from app.infrastructure.database.session import check_database_connection

logger = structlog.get_logger()


class TrustCenterService:
    """Service aggregating public platform security controls, uptime health, and RFC 9116 disclosures."""

    def __init__(
        self, session: AsyncSession, redis_client: Optional[Any] = None
    ) -> None:
        self.session = session
        self.redis_client = redis_client

    async def get_system_health_status(self) -> SystemHealthStatus:
        """Determine high-level operational health without exposing internal error stack traces."""
        try:
            db_healthy = await check_database_connection()
            redis_healthy = True
            if self.redis_client is not None:
                try:
                    await self.redis_client.ping()
                except Exception as exc:
                    logger.warning("trust_center.redis_ping_failed", error=str(exc))
                    redis_healthy = False

            if db_healthy and redis_healthy:
                return SystemHealthStatus.OPERATIONAL
            return SystemHealthStatus.DEGRADED_PERFORMANCE
        except Exception as exc:
            logger.error("trust_center.health_check_error", error=str(exc))
            return SystemHealthStatus.DEGRADED_PERFORMANCE

    def get_asvs_practice_grid(self) -> List[SecurityPracticeItemDTO]:
        """Return static OWASP ASVS v4.0 mapped security practices grid."""
        items: List[SecurityPracticeItem] = [
            SecurityPracticeItem(
                category=ASVSCategory.WORKER_SANDBOX_V17,
                title="Container Sandbox Worker Isolation",
                description="Scanner execution workers run inside unprivileged Linux containers with UID 10001, read-only rootfs, dropped capabilities, and strict egress proxy controls.",
                status="ENFORCED",
                asvs_ref="V14.2.1",
            ),
            SecurityPracticeItem(
                category=ASVSCategory.CRYPTOGRAPHY_V6,
                title="Envelope Data Encryption at Rest",
                description="Target contracts, scan configurations, and finding evidence are encrypted using AES-256-GCM envelope encryption with KMS key rotation.",
                status="ENFORCED",
                asvs_ref="V6.2.1",
            ),
            SecurityPracticeItem(
                category=ASVSCategory.ACCESS_CONTROL_V4,
                title="Multi-Tenant Boundary Isolation",
                description="Every SQL aggregation and cache access query strictly enforces tenant organization scoping, preventing cross-tenant data leakage.",
                status="ENFORCED",
                asvs_ref="V4.1.1",
            ),
            SecurityPracticeItem(
                category=ASVSCategory.AUTHENTICATION_V2,
                title="Authorized Assessment Contract Enforcement",
                description="Mandatory target authorization consent workflow blocks scan dispatch against unverified domains, preventing unauthorized scanning.",
                status="ENFORCED",
                asvs_ref="V2.1.2",
            ),
            SecurityPracticeItem(
                category=ASVSCategory.VALIDATION_SANITIZATION_V5,
                title="Input Schema & Output Payload Sanitization",
                description="Strict Pydantic v2 validation enforces type bounds on API boundaries; sensitive headers/cookies are masked before event stream emission.",
                status="ENFORCED",
                asvs_ref="V5.1.1",
            ),
            SecurityPracticeItem(
                category=ASVSCategory.SESSION_MANAGEMENT_V3,
                title="Short-Lived JWT & API Key Scoping",
                description="Analyst sessions use RS256 signed JWTs with 15-minute access token expiry and Argon2id hashed API keys.",
                status="ENFORCED",
                asvs_ref="V3.2.1",
            ),
            SecurityPracticeItem(
                category=ASVSCategory.ARCHITECTURE_V1,
                title="Clean Architecture & Domain Boundaries",
                description="Core vulnerability assessment logic is decoupled from frameworks, ensuring independent auditability and microservice readiness.",
                status="ENFORCED",
                asvs_ref="V1.1.1",
            ),
        ]
        return [
            SecurityPracticeItemDTO(
                category=item.category.value,
                title=item.title,
                description=item.description,
                status=item.status,
                asvs_ref=item.asvs_ref,
            )
            for item in items
        ]

    async def get_public_trust_center_summary(self) -> TrustCenterSummaryResponse:
        """Retrieve public Trust Center summary with 300s Redis caching."""
        cache_key = "trust_center:public_summary"

        if self.redis_client is not None:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    data_dict = json.loads(cached_data)
                    logger.debug("trust_center.cache_hit")
                    return TrustCenterSummaryResponse(**data_dict)
            except Exception as exc:
                logger.warning("trust_center.cache_read_error", error=str(exc))

        health_status = await self.get_system_health_status()
        asvs_grid = self.get_asvs_practice_grid()
        now_str = datetime.now(timezone.utc).isoformat()

        response = TrustCenterSummaryResponse(
            platform_name="Vulnova Enterprise AI Application Security Platform",
            version="1.0.0",
            system_status=health_status.value,
            asvs_alignment="Security Controls Mapped Against OWASP ASVS v4.0",
            encryption_standards={
                "data_at_rest": "AES-256-GCM Envelope Encryption",
                "data_in_transit": "TLS 1.3 / HSTS Preloaded",
                "token_signing": "RS256 / EdDSA",
            },
            sandbox_isolation={
                "execution_user": "UID 10001 (Unprivileged)",
                "filesystem": "read_only_rootfs: true",
                "egress_filtering": "Strict Private Subnet Egress Proxy",
                "capabilities": "CAP_DROP ALL",
            },
            security_practices_grid=asvs_grid,
            cached_at=now_str,
        )

        if self.redis_client is not None:
            try:
                await self.redis_client.setex(
                    cache_key, 300, response.model_dump_json()
                )
            except Exception as exc:
                logger.warning("trust_center.cache_write_error", error=str(exc))

        return response

    def get_security_disclosure_info(self) -> SecurityDisclosureResponse:
        """Return RFC 9116 security disclosure metadata."""
        info = SecurityDisclosureInfo()
        return SecurityDisclosureResponse(
            contact_email=info.contact_email,
            pgp_key_url=info.pgp_key_url,
            policy_url=info.policy_url,
            preferred_languages=info.preferred_languages,
            canonical_url=info.canonical_url,
            expires_at=info.expires_at,
            hiring_url=info.hiring_url,
        )

    def get_security_txt_content(self) -> str:
        """Generate RFC 9116 compliant security.txt plain text format."""
        info = SecurityDisclosureInfo()
        lines = [
            f"Contact: mailto:{info.contact_email}",
            f"Expires: {info.expires_at}",
            f"Encryption: {info.pgp_key_url}",
            f"Preferred-Languages: {info.preferred_languages}",
            f"Canonical: {info.canonical_url}",
            f"Policy: {info.policy_url}",
            f"Hiring: {info.hiring_url}",
            "# Vulnova Responsible Vulnerability Disclosure Policy",
            "# Report security issues directly to security@vulnova.com",
        ]
        return "\n".join(lines) + "\n"
