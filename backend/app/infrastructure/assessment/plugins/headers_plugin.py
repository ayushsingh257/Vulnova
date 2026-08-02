"""Reference Security Assessment Plugin: Security Headers Auditor."""

from typing import List, Optional

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

logger = get_logger("vulnova.plugin.headers")


class SecurityHeadersPlugin(BaseAssessmentPlugin):
    """Reference security plugin auditing HTTP Security Headers compliance."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="security_headers_plugin",
            name="HTTP Security Headers Auditor",
            version="1.0.0",
            description="Audits target web assets for HSTS, CSP, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy compliance.",
            category=VulnerabilityCategory.SECURITY_HEADER,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.URL_ENDPOINT,
            ],
            required_permissions=["scans:trigger"],
        )

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Probe target URL and return standardized Finding objects for missing security headers."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "security_headers_plugin.prohibited_target",
                target_url=target_url,
                reason=reason,
            )
            return findings

        headers: Optional[httpx.Headers] = None
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(target_url)
                headers = resp.headers
        except Exception as e:
            logger.warning(
                "security_headers_plugin.request_failed",
                target_url=target_url,
                error=str(e),
            )
            return findings

        if not headers:
            return findings

        lower_headers = {k.lower(): v for k, v in headers.items()}

        # 1. HSTS Audit
        if "strict-transport-security" not in lower_headers:
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Missing HTTP Strict Transport Security (HSTS) Header",
                    description="The server does not enforce HTTPS via the Strict-Transport-Security header, leaving connections vulnerable to man-in-the-middle SSL stripping attacks.",
                    severity=SeverityLevel.HIGH,
                    category=VulnerabilityCategory.SECURITY_HEADER,
                    cwe_id="CWE-523",
                    remediation="Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' to all HTTPS responses.",
                    evidence={
                        "target_url": target_url,
                        "header_checked": "Strict-Transport-Security",
                    },
                )
            )

        # 2. CSP Audit
        if "content-security-policy" not in lower_headers:
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Missing Content Security Policy (CSP) Header",
                    description="The application does not specify a Content-Security-Policy header, increasing risk of Cross-Site Scripting (XSS) and data injection attacks.",
                    severity=SeverityLevel.MEDIUM,
                    category=VulnerabilityCategory.SECURITY_HEADER,
                    cwe_id="CWE-1021",
                    remediation="Define a strict Content-Security-Policy header restricting script and resource origin locations.",
                    evidence={
                        "target_url": target_url,
                        "header_checked": "Content-Security-Policy",
                    },
                )
            )

        # 3. X-Frame-Options Audit
        if "x-frame-options" not in lower_headers:
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Missing X-Frame-Options Clickjacking Defense",
                    description="The web page does not restrict framing via X-Frame-Options, making it susceptible to Clickjacking attacks.",
                    severity=SeverityLevel.MEDIUM,
                    category=VulnerabilityCategory.SECURITY_HEADER,
                    cwe_id="CWE-1021",
                    remediation="Set 'X-Frame-Options: DENY' or 'SAMEORIGIN' on all HTTP responses.",
                    evidence={
                        "target_url": target_url,
                        "header_checked": "X-Frame-Options",
                    },
                )
            )

        # 4. X-Content-Type-Options Audit
        if "x-content-type-options" not in lower_headers:
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Missing X-Content-Type-Options MIME Sniffing Defense",
                    description="The response lacks 'X-Content-Type-Options: nosniff', enabling browser MIME-type sniffing vulnerabilities.",
                    severity=SeverityLevel.LOW,
                    category=VulnerabilityCategory.SECURITY_HEADER,
                    cwe_id="CWE-116",
                    remediation="Set 'X-Content-Type-Options: nosniff' header.",
                    evidence={
                        "target_url": target_url,
                        "header_checked": "X-Content-Type-Options",
                    },
                )
            )

        return findings
