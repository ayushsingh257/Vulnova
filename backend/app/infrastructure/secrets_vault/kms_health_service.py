"""KMS Provider Health Diagnosis Service (Phase 12.8)."""

from datetime import datetime, timezone
from typing import List

from app.core.config import settings
from app.infrastructure.secrets_vault.dto import KMSHealthDTO
from app.infrastructure.secrets_vault.provider_registry import (
    kms_registry,
)


class KMSHealthService:
    """Performs live health checks and latency probes on registered KMS providers."""

    @classmethod
    async def check_all_providers(cls) -> List[KMSHealthDTO]:
        """Probe health across all supported KMS providers."""
        results: List[KMSHealthDTO] = []
        now = datetime.now(timezone.utc)
        providers = kms_registry.list_supported_providers()

        for prov_name in providers:
            provider = kms_registry.get_provider(prov_name)
            kek_id = "health_probe_kek"
            try:
                res = await provider.health_check(kek_id)
                results.append(
                    KMSHealthDTO(
                        provider=prov_name,
                        is_healthy=res.get("status") == "healthy",
                        kek_id=res.get("kek_id", kek_id),
                        latency_ms=res.get("latency_ms", 0.0),
                        details=res,
                        checked_at=now,
                    )
                )
            except Exception as exc:
                results.append(
                    KMSHealthDTO(
                        provider=prov_name,
                        is_healthy=False,
                        kek_id=kek_id,
                        latency_ms=0.0,
                        details={"error": str(exc)},
                        checked_at=now,
                    )
                )
        return results

    @classmethod
    async def check_active_provider(cls) -> KMSHealthDTO:
        """Probe health of currently active configured KMS provider."""
        provider = kms_registry.get_provider(settings.kms_provider)
        kek_id = "active_health_probe_kek"
        now = datetime.now(timezone.utc)
        try:
            res = await provider.health_check(kek_id)
            return KMSHealthDTO(
                provider=settings.kms_provider,
                is_healthy=res.get("status") == "healthy",
                kek_id=res.get("kek_id", kek_id),
                latency_ms=res.get("latency_ms", 0.0),
                details=res,
                checked_at=now,
            )
        except Exception as exc:
            return KMSHealthDTO(
                provider=settings.kms_provider,
                is_healthy=False,
                kek_id=kek_id,
                latency_ms=0.0,
                details={"error": str(exc)},
                checked_at=now,
            )
