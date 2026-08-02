"""SQL Injection Vulnerability Assessment Plugin (Safe Non-Destructive Probing)."""

import re
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

logger = get_logger("vulnova.plugin.sqli")

# Common SQL Error Signatures across database engines
SQL_ERROR_PATTERNS = [
    r"syntax error at or near",
    r"postgresql.*error",
    r"valid postgresql result",
    r"you have an error in your sql syntax",
    r"mysql_fetch_array",
    r"unclosed quotation mark after the character string",
    r"microsoft OLE DB Provider for SQL Server",
    r"sqlite3::query",
    r"sqlite_error",
    r"ora-[0-9]{5}",
    r"oracle error",
]


class SQLInjectionPlugin(BaseAssessmentPlugin):
    """Production plugin detecting SQL Injection vulnerabilities via safe error-based probes."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="sql_injection_plugin",
            name="SQL Injection (SQLi) Auditor",
            version="1.0.0",
            description="Probes target query parameters with safe non-destructive syntax markers to detect SQL injection vulnerabilities.",
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
        """Execute safe SQL injection probing against query parameters."""
        findings: List[Finding] = []
        target_url = ctx.target_url

        is_safe, reason = is_safe_target_url(target_url)
        if not is_safe:
            logger.warning(
                "sql_injection_plugin.prohibited_target",
                target_url=target_url,
                reason=reason,
            )
            return findings

        parsed = urlparse(target_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        if not params:
            # Inject a test parameter if none present in URL
            params = {"id": ["1"]}

        # Safe non-destructive SQL syntax error probes
        test_payloads = ["'", "''", "' OR '1'='1", "1' ORDER BY 1--"]

        for param_name in params:
            for payload in test_payloads:
                test_params = params.copy()
                test_params[param_name] = [payload]
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

                        for pattern in SQL_ERROR_PATTERNS:
                            if re.search(pattern, body, re.IGNORECASE):
                                findings.append(
                                    Finding(
                                        organization_id=ctx.organization_id,
                                        plugin_id=self.metadata.id,
                                        title=f"SQL Injection Vulnerability in Parameter '{param_name}'",
                                        description=(
                                            f"The target query parameter '{param_name}' returned a database syntax error "
                                            f"when supplied with the safe syntax probe '{payload}'. This indicates unescaped SQL statement concatenation."
                                        ),
                                        severity=SeverityLevel.CRITICAL,
                                        category=VulnerabilityCategory.INJECTION,
                                        cve_id="CVE-2024-SQLI",
                                        cwe_id="CWE-89",
                                        remediation=(
                                            "Use parameterized queries (prepared statements) or Object-Relational Mapping (ORM) "
                                            "abstractions for all database operations. Never concatenate raw user input directly into SQL strings."
                                        ),
                                        evidence={
                                            "probe_url": probe_url,
                                            "vulnerable_parameter": param_name,
                                            "payload_used": payload,
                                            "matched_error_pattern": pattern,
                                        },
                                    )
                                )
                                # One confirmed finding per parameter is sufficient
                                break
                except Exception as e:
                    logger.debug(
                        "sql_injection_plugin.probe_failed",
                        probe_url=probe_url,
                        error=str(e),
                    )

        return findings
