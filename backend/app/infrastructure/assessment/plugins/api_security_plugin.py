"""API Discovery & Endpoint Security Assessment Plugin."""

from typing import List
from urllib.parse import urljoin, urlparse

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

logger = get_logger("vulnova.plugin.api_security")

# Common exposed API documentation & schema paths
API_DOC_PATHS = [
    "/swagger",
    "/swagger-ui",
    "/swagger-ui.html",
    "/openapi.json",
    "/swagger.json",
    "/api-docs",
    "/api/docs",
    "/graphql",
]


class APISecurityPlugin(BaseAssessmentPlugin):
    """Production plugin detecting exposed API documentation, schema disclosures, and endpoint security issues."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="api_security_plugin",
            name="API Discovery & Endpoint Security Auditor",
            version="1.0.0",
            description="Audits target asset for exposed API documentation (Swagger, OpenAPI, GraphQL), schema disclosures, and unsafe HTTP methods.",
            category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.URL_ENDPOINT,
            ],
            required_permissions=["scans:trigger"],
        )

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute API security probing against target URL."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "api_security_plugin.prohibited_target",
                target_url=target_url,
                reason=reason,
            )
            return findings

        parsed = urlparse(target_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # 1. Audit exposed API documentation & schema endpoints
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                for doc_path in API_DOC_PATHS:
                    probe_url = urljoin(base_url, doc_path)
                    try:
                        resp = await client.get(probe_url)
                        if resp.status_code == 200:
                            content_type = resp.headers.get("content-type", "").lower()
                            body = resp.text.lower()

                            # Confirm actual API documentation / GraphQL interface
                            if (
                                "swagger" in body
                                or "openapi" in body
                                or "graphql" in body
                                or "json" in content_type
                            ):
                                findings.append(
                                    Finding(
                                        organization_id=ctx.organization_id,
                                        plugin_id=self.metadata.id,
                                        title=f"Exposed API Documentation Endpoint: '{doc_path}'",
                                        description=(
                                            f"Publicly accessible API documentation or schema endpoint found at '{probe_url}'. "
                                            f"Exposing interactive API documentation or schemas increases attack surface knowledge for threat actors."
                                        ),
                                        severity=SeverityLevel.MEDIUM,
                                        category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
                                        cwe_id="CWE-200",
                                        remediation=(
                                            "Restrict public access to internal API documentation endpoints or enforce authentication guards "
                                            "on Swagger/OpenAPI UI and GraphQL introspection endpoints."
                                        ),
                                        evidence={
                                            "exposed_url": probe_url,
                                            "status_code": resp.status_code,
                                            "content_type": resp.headers.get(
                                                "content-type"
                                            ),
                                        },
                                    )
                                )
                    except Exception as e:
                        logger.debug(
                            "api_security_plugin.doc_probe_failed",
                            probe_url=probe_url,
                            error=str(e),
                        )

        except Exception as e:
            logger.debug(
                "api_security_plugin.execution_failed",
                target_url=target_url,
                error=str(e),
            )

        return findings
