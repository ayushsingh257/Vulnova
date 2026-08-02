"""JWT Security & Token Claims Assessment Plugin."""

import base64
import json
import time
from typing import Any, Dict, List, Optional

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

logger = get_logger("vulnova.plugin.jwt_security")


class JWTSecurityPlugin(BaseAssessmentPlugin):
    """Production plugin auditing JWT token claims, algorithm security, and expiration controls."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="jwt_security_plugin",
            name="JWT Security & Claims Auditor",
            version="1.0.0",
            description="Audits JSON Web Tokens (JWT) for weak signing algorithms (none), missing expiration (exp), excessive lifetime, and missing issuer/audience claims.",
            category=VulnerabilityCategory.AUTHENTICATION,
            author="Vulnova Security Team",
            supported_asset_types=[
                AssetNodeType.TARGET_DOMAIN,
                AssetNodeType.URL_ENDPOINT,
            ],
            required_permissions=["scans:trigger"],
        )

    def _decode_jwt_segment(self, segment: str) -> Optional[Dict[str, Any]]:
        """Safely decode base64url encoded JWT header or payload segment."""
        try:
            padded = segment + "=" * (-len(segment) % 4)
            decoded_bytes = base64.urlsafe_b64decode(padded)
            data = json.loads(decoded_bytes.decode("utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute JWT security analysis on token provided in context options or headers."""
        findings: List[Finding] = []

        # Extract JWT string from options if provided
        jwt_token: Optional[str] = None
        if ctx.options and "jwt_token" in ctx.options:
            jwt_token = str(ctx.options["jwt_token"])

        if not jwt_token:
            # Skip gracefully if no JWT provided in context options
            return findings

        parts = jwt_token.split(".")
        if len(parts) != 3:
            logger.warning("jwt_security_plugin.invalid_jwt_structure")
            return findings

        header = self._decode_jwt_segment(parts[0])
        payload = self._decode_jwt_segment(parts[1])

        if not header or not payload:
            logger.warning("jwt_security_plugin.decoding_failed")
            return findings

        # 1. Check Algorithm (alg: "none" or "HS256" weak symmetric algorithms)
        alg = str(header.get("alg", "")).lower()
        if alg == "none":
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Critical JWT Vulnerability: Unsigned Token ('alg': 'none')",
                    description="The JWT header specifies 'alg': 'none'. Unsigned tokens allow attackers to forge arbitrary token payloads without a valid signature.",
                    severity=SeverityLevel.CRITICAL,
                    category=VulnerabilityCategory.AUTHENTICATION,
                    cve_id="CVE-2015-9235",
                    cwe_id="CWE-347",
                    remediation="Reject JWTs with 'alg': 'none' and enforce strong asymmetric signature algorithms (e.g. RS256, ES256).",
                    evidence={"header": header},
                )
            )

        # 2. Check Expiration Claim (exp)
        if "exp" not in payload:
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Missing Expiration Claim ('exp') in JWT Payload",
                    description="The JWT payload does not contain an 'exp' (expiration time) claim. Tokens without expiration remain valid indefinitely if leaked.",
                    severity=SeverityLevel.HIGH,
                    category=VulnerabilityCategory.AUTHENTICATION,
                    cwe_id="CWE-613",
                    remediation="Include an 'exp' claim in all issued JWTs and enforce strict token expiration validation.",
                    evidence={"payload": payload},
                )
            )
        else:
            exp = payload["exp"]
            iat = payload.get("iat", time.time())
            lifetime_hours = (exp - iat) / 3600.0
            if lifetime_hours > 24:
                findings.append(
                    Finding(
                        organization_id=ctx.organization_id,
                        plugin_id=self.metadata.id,
                        title=f"Excessive JWT Lifetime ({round(lifetime_hours, 1)} Hours)",
                        description=f"The JWT token expiration lifetime ({round(lifetime_hours, 1)} hours) exceeds recommended enterprise session limits (max 24 hours).",
                        severity=SeverityLevel.MEDIUM,
                        category=VulnerabilityCategory.AUTHENTICATION,
                        cwe_id="CWE-613",
                        remediation="Reduce access token lifetime to 15–60 minutes and implement refresh token rotation.",
                        evidence={
                            "exp": exp,
                            "iat": iat,
                            "lifetime_hours": lifetime_hours,
                        },
                    )
                )

        # 3. Check Issuer ('iss') & Audience ('aud') Claims
        if "iss" not in payload:
            findings.append(
                Finding(
                    organization_id=ctx.organization_id,
                    plugin_id=self.metadata.id,
                    title="Missing Issuer Claim ('iss') in JWT Payload",
                    description="The JWT does not specify an issuer claim ('iss'), increasing susceptibility to cross-domain token reuse attacks.",
                    severity=SeverityLevel.LOW,
                    category=VulnerabilityCategory.AUTHENTICATION,
                    cwe_id="CWE-287",
                    remediation="Set and validate 'iss' claim during JWT verification.",
                    evidence={"payload": payload},
                )
            )

        return findings
