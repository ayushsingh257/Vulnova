"""Cloud Exposure and Storage Bucket Misconfiguration Assessment Plugin."""

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

logger = get_logger("vulnova.plugin.cloud_security")

CLOUD_METADATA_IP = "169.254.169.254"


class CloudSecurityPlugin(BaseAssessmentPlugin):
    """Production plugin auditing Cloud Storage Exposure (AWS S3, Azure Blob, GCP Storage) and Metadata Service Risks."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="cloud_security_plugin",
            name="Cloud Storage & Exposure Auditor",
            version="1.0.0",
            description="Audits public cloud storage exposure (AWS S3, Azure Blob, GCP Cloud Storage) and cloud instance metadata service endpoint references.",
            category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.SUBDOMAIN,
                AssetNodeType.URL_ENDPOINT,
                AssetNodeType.TECHNOLOGY,
            ],
            required_permissions=["scans:trigger"],
        )

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute cloud exposure analysis against target domain/url."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "cloud_security_plugin.prohibited_target",
                target_url=target_url,
                reason=reason,
            )
            return findings

        parsed = urlparse(target_url)
        host = parsed.hostname or parsed.path

        # 1. AWS S3 Bucket Name Pattern Probe
        if host and (host.endswith(".s3.amazonaws.com") or "s3" in host):
            try:
                async with httpx.AsyncClient(
                    timeout=6.0, follow_redirects=True
                ) as client:
                    resp = await client.get(f"https://{host}")
                    body = resp.text.lower()

                    # Public Bucket Listing Enabled
                    if "<listbucketresult>" in body or "<contents>" in body:
                        findings.append(
                            Finding(
                                organization_id=ctx.organization_id,
                                plugin_id=self.metadata.id,
                                title=f"Publicly Accessible AWS S3 Bucket Listing for '{host}'",
                                description=(
                                    f"The AWS S3 bucket '{host}' allows public anonymous bucket listing (<ListBucketResult>). "
                                    f"Anonymous bucket listing exposes sensitive object names, backup files, and internal assets."
                                ),
                                severity=SeverityLevel.HIGH,
                                category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
                                cwe_id="CWE-732",
                                remediation=(
                                    "Enable S3 'Block Public Access' settings at the AWS account and bucket levels. "
                                    "Restrict bucket policy permissions to authorized IAM roles."
                                ),
                                evidence={
                                    "bucket_host": host,
                                    "status_code": resp.status_code,
                                    "provider": "AWS S3",
                                },
                            )
                        )
            except Exception as e:
                logger.debug("cloud_security_plugin.s3_failed", host=host, error=str(e))

        # 2. Azure Blob Storage Exposure Pattern
        if host and host.endswith(".blob.core.windows.net"):
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title=f"Public Azure Blob Storage Endpoint Discovered: '{host}'",
                    description=f"Public Azure Blob Storage endpoint '{host}' identified. Public storage accounts must be verified for strict container access controls.",
                    severity=SeverityLevel.MEDIUM,
                    category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
                    cwe_id="CWE-200",
                    remediation="Disable anonymous public read access for containers and blobs in Azure Portal.",
                    evidence={"storage_host": host, "provider": "Azure Blob Storage"},
                )
            )

        # 3. Check for exposed Cloud Instance Metadata Service References in target URL
        if CLOUD_METADATA_IP in target_url:
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Cloud Instance Metadata Service (IMDS) Reference Detected",
                    description=f"The target URL '{target_url}' references the Cloud Metadata IP (169.254.169.254). Exposing IMDS endpoints to SSRF probes can allow attackers to steal IAM instance profile credentials.",
                    severity=SeverityLevel.CRITICAL,
                    category=VulnerabilityCategory.SSRF,
                    cwe_id="CWE-918",
                    remediation="Block access to 169.254.169.254 via network egress rules and require IMDSv2 with session tokens.",
                    evidence={
                        "target_url": target_url,
                        "metadata_ip": CLOUD_METADATA_IP,
                    },
                )
            )

        return findings
