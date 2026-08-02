"""Network Port and Exposed Administrative Service Assessment Plugin."""

import asyncio
from typing import Dict, List
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.domain.entities.assessment import (
    AssessmentContext,
    BaseAssessmentPlugin,
    Finding,
    PluginMetadata,
    SeverityLevel,
    VulnerabilityCategory,
)
from app.domain.entities.discovery import AssetNodeType
from app.infrastructure.discovery.ssrf_validator import is_safe_target_url

logger = get_logger("vulnova.plugin.network_service")

# High-risk administrative & database ports
DANGEROUS_PORTS: Dict[int, Dict[str, str]] = {
    22: {"service": "SSH", "cwe": "CWE-284", "severity": "MEDIUM"},
    3389: {"service": "RDP", "cwe": "CWE-284", "severity": "HIGH"},
    3306: {"service": "MySQL Database", "cwe": "CWE-200", "severity": "HIGH"},
    5432: {"service": "PostgreSQL Database", "cwe": "CWE-200", "severity": "HIGH"},
    27017: {"service": "MongoDB Database", "cwe": "CWE-200", "severity": "HIGH"},
    6379: {"service": "Redis In-Memory Store", "cwe": "CWE-306", "severity": "HIGH"},
    9200: {"service": "Elasticsearch Engine", "cwe": "CWE-200", "severity": "HIGH"},
    11211: {"service": "Memcached Cache", "cwe": "CWE-306", "severity": "MEDIUM"},
}


class NetworkServicePlugin(BaseAssessmentPlugin):
    """Production plugin detecting exposed high-risk administrative and database ports."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="network_service_plugin",
            name="Port & Exposed Service Auditor",
            version="1.0.0",
            description="Audits host IP addresses for dangerous exposed administrative and database ports (SSH, RDP, MySQL, PostgreSQL, MongoDB, Redis, Elasticsearch).",
            category=VulnerabilityCategory.MISCONFIGURATION,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.IP_ADDRESS,
            ],
            required_permissions=["scans:trigger"],
        )

    async def _check_port(self, host: str, port: int, timeout: float = 2.0) -> bool:
        """Asynchronously check if a TCP port is open."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, OSError):
            return False

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute non-blocking port exposure checks against target host."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "network_service_plugin.prohibited_target",
                target_url=target_url,
                reason=reason,
            )
            return findings

        parsed = urlparse(target_url)
        host = parsed.hostname or parsed.path
        if not host:
            return findings

        # Concurrent non-destructive TCP port checks
        tasks = [self._check_port(host, port) for port in DANGEROUS_PORTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (port, info), is_open in zip(
            DANGEROUS_PORTS.items(), results, strict=False
        ):
            if is_open is True:
                sev_enum = (
                    SeverityLevel.HIGH
                    if info["severity"] == "HIGH"
                    else SeverityLevel.MEDIUM
                )
                findings.append(
                    Finding(
                        organization_id=ctx.organization_id,
                        plugin_id=self.metadata.id,
                        title=f"Exposed {info['service']} Service (Port {port})",
                        description=(
                            f"The port {port} ({info['service']}) on host '{host}' is publicly accessible. "
                            f"Exposing management or database ports directly to the internet invites brute-force and unauthorized access attacks."
                        ),
                        severity=sev_enum,
                        category=VulnerabilityCategory.MISCONFIGURATION,
                        cwe_id=info["cwe"],
                        remediation=(
                            f"Restrict access to port {port} using firewall rules (Security Groups, IPtables). "
                            f"Enforce access strictly through a secure VPN or bastion host."
                        ),
                        evidence={
                            "host": host,
                            "port": port,
                            "service": info["service"],
                            "state": "OPEN",
                        },
                    )
                )

        return findings
