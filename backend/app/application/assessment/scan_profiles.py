"""Enterprise Scan Profile Registry for Vulnerability Assessment Engine."""

from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.domain.entities.assessment import ScanPolicy, ScanProfile, ScanProfileType
from app.infrastructure.assessment.registry import PluginRegistry

logger = get_logger("vulnova.scan_profiles")


class ScanProfileRegistry:
    """Registry managing enterprise scan profiles.

    References plugin IDs registered in PluginRegistry without duplicating metadata or logic.
    """

    def __init__(self, plugin_registry: Optional[PluginRegistry] = None) -> None:
        self.plugin_registry = plugin_registry or PluginRegistry()
        self._profiles: Dict[str, ScanProfile] = {}
        self._load_default_profiles()

    def _load_default_profiles(self) -> None:
        """Register the 10 standard enterprise scan profiles."""
        defaults = [
            ScanProfile(
                id=ScanProfileType.QUICK_SCAN.value,
                name="Quick Scan",
                description="Fast lightweight passive checks (Headers, API Docs, Port Exposure).",
                plugin_ids=[
                    "security_headers_plugin",
                    "api_security_plugin",
                    "network_service_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=10, max_requests=100
                ),
            ),
            ScanProfile(
                id=ScanProfileType.WEB_SCAN.value,
                name="Web Vulnerability Scan",
                description="Web application assessment (SQLi, XSS, Headers, Auth Cookies).",
                plugin_ids=[
                    "sql_injection_plugin",
                    "xss_plugin",
                    "security_headers_plugin",
                    "auth_security_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=10, max_requests=500
                ),
            ),
            ScanProfile(
                id=ScanProfileType.API_SCAN.value,
                name="API Security Scan",
                description="REST & GraphQL API assessment (Documentation, JWT, CORS).",
                plugin_ids=[
                    "api_security_plugin",
                    "jwt_security_plugin",
                    "cors_security_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=10, max_requests=300
                ),
            ),
            ScanProfile(
                id=ScanProfileType.INFRASTRUCTURE_SCAN.value,
                name="Infrastructure & Cloud Security Scan",
                description="Network ports, TLS/SSL certs, S3/Cloud buckets, IMDS exposure.",
                plugin_ids=[
                    "network_service_plugin",
                    "tls_security_plugin",
                    "cloud_security_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=3, rate_limit_rps=5, max_requests=200
                ),
            ),
            ScanProfile(
                id=ScanProfileType.OWASP_TOP_10.value,
                name="OWASP Top 10 Assessment",
                description="Targeted scan aligned with OWASP Top 10 Web Application Risks.",
                plugin_ids=[
                    "sql_injection_plugin",
                    "xss_plugin",
                    "auth_security_plugin",
                    "security_headers_plugin",
                    "cors_security_plugin",
                    "api_security_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=10, max_requests=600
                ),
            ),
            ScanProfile(
                id=ScanProfileType.OWASP_API_TOP_10.value,
                name="OWASP API Security Top 10",
                description="Targeted scan aligned with OWASP API Security Top 10 Risks.",
                plugin_ids=[
                    "api_security_plugin",
                    "jwt_security_plugin",
                    "cors_security_plugin",
                    "auth_security_plugin",
                    "security_headers_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=10, max_requests=400
                ),
            ),
            ScanProfile(
                id=ScanProfileType.FULL_ASSESSMENT.value,
                name="Full Enterprise Security Assessment",
                description="Comprehensive assessment executing all 10 production security plugins.",
                plugin_ids=[
                    "sql_injection_plugin",
                    "xss_plugin",
                    "security_headers_plugin",
                    "auth_security_plugin",
                    "api_security_plugin",
                    "jwt_security_plugin",
                    "cors_security_plugin",
                    "network_service_plugin",
                    "tls_security_plugin",
                    "cloud_security_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=10, max_requests=1000
                ),
            ),
            ScanProfile(
                id=ScanProfileType.AUTHENTICATED_SCAN.value,
                name="Authenticated Assessment",
                description="Deep authenticated scan using session headers and cookie injection.",
                plugin_ids=[
                    "sql_injection_plugin",
                    "xss_plugin",
                    "auth_security_plugin",
                    "api_security_plugin",
                    "jwt_security_plugin",
                    "cors_security_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=10, max_requests=600
                ),
            ),
            ScanProfile(
                id=ScanProfileType.PASSIVE_SCAN.value,
                name="Passive Security Inspection",
                description="Zero active-probe passive inspection (Headers, API Docs, TLS Certs).",
                plugin_ids=[
                    "security_headers_plugin",
                    "api_security_plugin",
                    "tls_security_plugin",
                ],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=15, max_requests=100
                ),
            ),
            ScanProfile(
                id=ScanProfileType.CUSTOM_SCAN.value,
                name="Custom Profile",
                description="Custom user-configured plugin selection and policy parameters.",
                plugin_ids=[],
                default_policy=ScanPolicy(
                    concurrency_limit=5, rate_limit_rps=10, max_requests=500
                ),
            ),
        ]
        for p in defaults:
            self._profiles[p.id] = p

    def get_profile(self, profile_id: str) -> Optional[ScanProfile]:
        """Retrieve scan profile by ID."""
        return self._profiles.get(profile_id)

    def resolve_plugins_for_profile(
        self, profile_id: str, custom_plugins: Optional[List[str]] = None
    ) -> List[str]:
        """Resolve valid registered plugin IDs for a given scan profile.

        Validates against PluginRegistry as the single source of truth.
        """
        registered_ids = [meta.id for meta in self.plugin_registry.list_plugins()]

        if profile_id == ScanProfileType.CUSTOM_SCAN.value and custom_plugins:
            target_ids = custom_plugins
        else:
            profile = self.get_profile(profile_id)
            if not profile:
                logger.warning(
                    "scan_profiles.profile_not_found_fallback",
                    profile_id=profile_id,
                )
                return registered_ids
            target_ids = profile.plugin_ids

        # Filter against actual registered plugin IDs in PluginRegistry
        resolved = [pid for pid in target_ids if pid in registered_ids]

        # If profile targets all plugins or resolves empty, fallback to registered
        if not resolved and profile_id == ScanProfileType.FULL_ASSESSMENT.value:
            resolved = registered_ids

        return resolved

    def list_profiles(self) -> List[ScanProfile]:
        """List all available enterprise scan profiles."""
        return list(self._profiles.values())
