"""Cross-Origin Resource Sharing (CORS) Security Assessment Plugin."""

from typing import List

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

logger = get_logger("vulnova.plugin.cors_security")


class CORSPlugin(BaseAssessmentPlugin):
    """Production plugin auditing Cross-Origin Resource Sharing (CORS) misconfigurations."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="cors_security_plugin",
            name="CORS Policy Misconfiguration Auditor",
            version="1.0.0",
            description="Audits Access-Control-Allow-Origin, Access-Control-Allow-Credentials, wildcard origin permissions, and untrusted origin reflection.",
            category=VulnerabilityCategory.MISCONFIGURATION,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.URL_ENDPOINT,
            ],
            required_permissions=["scans:trigger"],
        )

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute CORS security analysis against target endpoint."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "cors_security_plugin.prohibited_target",
                target_url=target_url,
                reason=reason,
            )
            return findings

        test_origin = "https://evil.com"

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                headers = {"Origin": test_origin}
                resp = await client.get(target_url, headers=headers)

                aco = resp.headers.get("access-control-allow-origin")
                acc = resp.headers.get("access-control-allow-credentials")

                if aco:
                    # 1. Wildcard Origin with Credentials Allowed
                    if aco == "*" and str(acc).lower() == "true":
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title="Critical CORS Misconfiguration: Wildcard Origin with Credentials",
                                description="The server specifies 'Access-Control-Allow-Origin: *' along with 'Access-Control-Allow-Credentials: true'. This allows external domains to read sensitive authenticated responses.",
                                severity=SeverityLevel.HIGH,
                                category=VulnerabilityCategory.MISCONFIGURATION,
                                cwe_id="CWE-942",
                                remediation="Never return 'Access-Control-Allow-Credentials: true' when 'Access-Control-Allow-Origin' is set to '*'. Maintain an explicit whitelist of trusted origins.",
                                evidence={
                                    "target_url": target_url,
                                    "access_control_allow_origin": aco,
                                    "access_control_allow_credentials": acc,
                                },
                            )
                        )

                    # 2. Arbitrary Origin Reflection with Credentials
                    elif aco == test_origin and str(acc).lower() == "true":
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title="Overly Permissive CORS Policy: Arbitrary Origin Reflection",
                                description=f"The server dynamically reflects arbitrary request origins ('{test_origin}') in 'Access-Control-Allow-Origin' with credentials allowed.",
                                severity=SeverityLevel.HIGH,
                                category=VulnerabilityCategory.MISCONFIGURATION,
                                cwe_id="CWE-942",
                                remediation="Validate incoming 'Origin' headers against an explicit, strict whitelist of trusted domain origins.",
                                evidence={
                                    "probe_origin": test_origin,
                                    "reflected_origin": aco,
                                    "credentials_allowed": acc,
                                },
                            )
                        )

                    # 3. Generic Wildcard Origin
                    elif aco == "*":
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title="Public CORS Access Allowed ('Access-Control-Allow-Origin: *')",
                                description="The target resource permits read access from any external origin ('*'). If the endpoint returns non-public data, this poses an information disclosure risk.",
                                severity=SeverityLevel.LOW,
                                category=VulnerabilityCategory.MISCONFIGURATION,
                                cwe_id="CWE-942",
                                remediation="If the API endpoint handles sensitive user data, restrict allowed origins to trusted domains.",
                                evidence={
                                    "target_url": target_url,
                                    "access_control_allow_origin": aco,
                                },
                            )
                        )

        except Exception as e:
            logger.debug(
                "cors_security_plugin.probe_failed", target_url=target_url, error=str(e)
            )

        return findings
