"""TLS/SSL Certificate and Encryption Security Assessment Plugin."""

import datetime
import socket
import ssl
from typing import List
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

logger = get_logger("vulnova.plugin.tls_security")


class TLSSecurityPlugin(BaseAssessmentPlugin):
    """Production plugin auditing TLS/SSL certificate validity, expiration, and cipher protocols."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="tls_security_plugin",
            name="TLS/SSL Security & Certificate Auditor",
            version="1.0.0",
            description="Audits HTTPS endpoints for expired certificates, hostname mismatch, weak TLS versions, and upcoming certificate expirations.",
            category=VulnerabilityCategory.MISCONFIGURATION,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.SUBDOMAIN,
                AssetNodeType.URL_ENDPOINT,
            ],
            required_permissions=["scans:trigger"],
        )

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute SSL/TLS certificate and protocol inspection against target URL."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "tls_security_plugin.prohibited_target",
                target_url=target_url,
                reason=reason,
            )
            return findings

        parsed = urlparse(target_url)
        if parsed.scheme != "https":
            # Only HTTPS targets support SSL/TLS socket inspection
            return findings

        host = parsed.hostname
        if not host:
            return findings
        port = parsed.port or 443

        ssl_ctx = ssl.create_default_context()

        try:
            with socket.create_connection((host, port), timeout=6.0) as sock:
                with ssl_ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher_info = ssock.cipher()
                    cipher_name = cipher_info[0] if cipher_info else "unknown"
                    version = cipher_info[1] if cipher_info else "unknown"

                    # 1. Check Weak TLS Protocol Versions (TLSv1, TLSv1.1)
                    if version in ("TLSv1", "TLSv1.1"):
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title=f"Deprecated TLS Protocol Version Supported: {version}",
                                description=f"The server negotiates connections using deprecated protocol version {version}. Deprecated TLS versions have known cryptographic vulnerabilities.",
                                severity=SeverityLevel.HIGH,
                                category=VulnerabilityCategory.MISCONFIGURATION,
                                cwe_id="CWE-326",
                                remediation="Disable TLS 1.0 and TLS 1.1 on the server. Enforce TLS 1.2 or TLS 1.3 exclusively.",
                                evidence={
                                    "host": host,
                                    "negotiated_version": version,
                                    "cipher": cipher_name,
                                },
                            )
                        )

                    if cert:
                        # 2. Check Certificate Expiration Date
                        raw_not_after = cert.get("notAfter")
                        if isinstance(raw_not_after, str):
                            not_after_str = raw_not_after
                            not_after = datetime.datetime.strptime(
                                not_after_str, "%b %d %H:%M:%S %Y %Z"
                            ).replace(tzinfo=datetime.timezone.utc)
                            now = datetime.datetime.now(datetime.timezone.utc)
                            days_remaining = (not_after - now).days

                            if days_remaining <= 0:
                                findings.append(
                                    Finding(
                                        organization_id=ctx.organization_id,
                                        plugin_id=self.metadata.id,
                                        title=f"Expired SSL/TLS Certificate for '{host}'",
                                        description=f"The SSL/TLS certificate for host '{host}' expired {abs(days_remaining)} days ago ({not_after_str}). Expired certificates breach trust and trigger browser security warnings.",
                                        severity=SeverityLevel.HIGH,
                                        category=VulnerabilityCategory.MISCONFIGURATION,
                                        cwe_id="CWE-295",
                                        remediation="Renew and re-install a valid SSL/TLS certificate immediately.",
                                        evidence={
                                            "host": host,
                                            "not_after": not_after_str,
                                            "days_remaining": days_remaining,
                                        },
                                    )
                                )
                            elif days_remaining <= 14:
                                findings.append(
                                    Finding(
                                        organization_id=ctx.organization_id,
                                        plugin_id=self.metadata.id,
                                        title=f"SSL/TLS Certificate Expiring Soon ({days_remaining} Days Remaining)",
                                        description=f"The SSL/TLS certificate for host '{host}' will expire in {days_remaining} days on {not_after_str}.",
                                        severity=SeverityLevel.MEDIUM,
                                        category=VulnerabilityCategory.MISCONFIGURATION,
                                        cwe_id="CWE-295",
                                        remediation="Renew the SSL/TLS certificate prior to expiration.",
                                        evidence={
                                            "host": host,
                                            "not_after": not_after_str,
                                            "days_remaining": days_remaining,
                                        },
                                    )
                                )
        except ssl.SSLCertVerificationError as e:
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title=f"SSL/TLS Certificate Verification Failed for '{host}'",
                    description=f"The SSL/TLS certificate for '{host}' could not be verified by trust store. Reason: {str(e)}",
                    severity=SeverityLevel.HIGH,
                    category=VulnerabilityCategory.MISCONFIGURATION,
                    cwe_id="CWE-295",
                    remediation="Install a valid SSL/TLS certificate issued by a recognized Certificate Authority (CA) and verify full chain certificate bundle.",
                    evidence={"host": host, "verification_error": str(e)},
                )
            )
        except Exception as e:
            logger.debug("tls_security_plugin.socket_failed", host=host, error=str(e))

        return findings
