"""Cross-Site Scripting (XSS) Vulnerability Assessment Plugin."""

import uuid
from typing import List
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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

logger = get_logger("vulnova.plugin.xss")


class XSSPlugin(BaseAssessmentPlugin):
    """Production plugin detecting Reflected Cross-Site Scripting (XSS) via safe marker probes."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="xss_plugin",
            name="Reflected Cross-Site Scripting (XSS) Auditor",
            version="1.0.0",
            description="Probes target query parameters with safe marker payloads to detect unescaped HTML reflection.",
            category=VulnerabilityCategory.INJECTION,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.URL_ENDPOINT,
                AssetNodeType.FORM,
            ],
            required_permissions=["scans:trigger"],
        )

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute safe XSS reflection probing against query parameters."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "xss_plugin.prohibited_target", target_url=target_url, reason=reason
            )
            return findings

        parsed = urlparse(target_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        if not params:
            params = {"q": ["test"]}

        # Safe non-executing marker payload
        marker_id = uuid.uuid4().hex[:8]
        test_payload = f'"><vlnv_xss_probe_{marker_id}>'

        for param_name in params:
            test_params = params.copy()
            test_params[param_name] = [test_payload]
            new_query = urlencode(test_params, doseq=True)
            probe_url = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment,
                )
            )

            try:
                async with httpx.AsyncClient(
                    timeout=8.0, follow_redirects=True
                ) as client:
                    resp = await client.get(probe_url)
                    body = resp.text

                    # Check if unescaped marker tag is reflected in response body
                    if test_payload in body:
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title=f"Reflected Cross-Site Scripting (XSS) in Parameter '{param_name}'",
                                description=(
                                    f"The parameter '{param_name}' reflected unescaped HTML syntax when supplied with "
                                    f"the marker probe '{test_payload}'. This indicates a lack of output encoding, allowing script injection."
                                ),
                                severity=SeverityLevel.HIGH,
                                category=VulnerabilityCategory.INJECTION,
                                cve_id="CVE-2024-XSS",
                                cwe_id="CWE-79",
                                remediation=(
                                    "Contextually encode all user-supplied output rendered in HTML templates (e.g. HTML entity encoding). "
                                    "Implement a strict Content-Security-Policy header."
                                ),
                                evidence={
                                    "probe_url": probe_url,
                                    "vulnerable_parameter": param_name,
                                    "reflected_payload": test_payload,
                                },
                            )
                        )
            except Exception as e:
                logger.debug(
                    "xss_plugin.probe_failed", probe_url=probe_url, error=str(e)
                )

        return findings
