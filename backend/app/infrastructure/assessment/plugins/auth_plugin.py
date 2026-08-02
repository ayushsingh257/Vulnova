"""Authentication Security & Cookie Policy Assessment Plugin."""

from typing import List
from urllib.parse import urlparse

import httpx

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

logger = get_logger("vulnova.plugin.auth")


class AuthSecurityPlugin(BaseAssessmentPlugin):
    """Production plugin auditing Authentication Security & Cookie Flags."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="auth_security_plugin",
            name="Authentication Security & Cookie Auditor",
            version="1.0.0",
            description="Audits authentication endpoints, cookie security flags (HttpOnly, Secure, SameSite), and unencrypted credential transmission risks.",
            category=VulnerabilityCategory.AUTHENTICATION,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.URL_ENDPOINT,
            ],
            required_permissions=["scans:trigger"],
        )

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute authentication security analysis against target asset."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "auth_security_plugin.prohibited_target",
                target_url=target_url,
                reason=reason,
            )
            return findings

        parsed = urlparse(target_url)

        # 1. Unencrypted HTTP Authentication Transmission Risk
        if parsed.scheme == "http":
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Unencrypted HTTP Communication for Target Asset",
                    description=f"The target asset '{target_url}' uses unencrypted HTTP. Authentication credentials and session tokens transmitted over plaintext HTTP can be intercepted via Network Sniffing.",
                    severity=SeverityLevel.HIGH,
                    category=VulnerabilityCategory.AUTHENTICATION,
                    cwe_id="CWE-319",
                    remediation="Enforce HTTPS across all application endpoints and configure HTTP-to-HTTPS redirection.",
                    evidence={"target_url": target_url, "scheme": parsed.scheme},
                )
            )

        # 2. Probe Response and Audit Set-Cookie Security Flags
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(target_url)

                # Check Set-Cookie Headers
                cookie_headers = resp.headers.get_list("set-cookie")
                for cookie_str in cookie_headers:
                    cookie_lower = cookie_str.lower()
                    cookie_name = cookie_str.split("=")[0].strip()

                    # Missing HttpOnly Flag
                    if "httponly" not in cookie_lower:
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title=f"Missing HttpOnly Flag on Cookie '{cookie_name}'",
                                description=f"The cookie '{cookie_name}' is set without the HttpOnly attribute, allowing client-side scripts to access token data via document.cookie.",
                                severity=SeverityLevel.MEDIUM,
                                category=VulnerabilityCategory.AUTHENTICATION,
                                cwe_id="CWE-1004",
                                remediation=f"Set 'HttpOnly' flag on response header for cookie '{cookie_name}'.",
                                evidence={"cookie": cookie_str},
                            )
                        )

                    # Missing Secure Flag
                    if "secure" not in cookie_lower and parsed.scheme == "https":
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title=f"Missing Secure Flag on Cookie '{cookie_name}'",
                                description=f"The cookie '{cookie_name}' is set without the Secure attribute, allowing browsers to send it over unencrypted HTTP connections.",
                                severity=SeverityLevel.MEDIUM,
                                category=VulnerabilityCategory.AUTHENTICATION,
                                cwe_id="CWE-614",
                                remediation=f"Set 'Secure' flag on response header for cookie '{cookie_name}'.",
                                evidence={"cookie": cookie_str},
                            )
                        )

                    # Missing SameSite Attribute
                    if "samesite" not in cookie_lower:
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title=f"Missing SameSite Protection on Cookie '{cookie_name}'",
                                description=f"The cookie '{cookie_name}' does not specify a SameSite attribute (Lax or Strict), increasing vulnerability to Cross-Site Request Forgery (CSRF).",
                                severity=SeverityLevel.LOW,
                                category=VulnerabilityCategory.AUTHENTICATION,
                                cwe_id="CWE-352",
                                remediation=f"Set 'SameSite=Lax' or 'SameSite=Strict' on response header for cookie '{cookie_name}'.",
                                evidence={"cookie": cookie_str},
                            )
                        )
        except Exception as e:
            logger.debug(
                "auth_security_plugin.request_failed",
                target_url=target_url,
                error=str(e),
            )

        return findings
