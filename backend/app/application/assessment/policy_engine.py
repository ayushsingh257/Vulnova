"""Execution-layer independent Scan Policy Engine.

Designed for current AssessmentService and future Era 6 distributed workers.
"""

from fnmatch import fnmatch
from typing import Dict, List
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.domain.entities.assessment import Finding, ScanPolicy, SeverityLevel

logger = get_logger("vulnova.policy_engine")


class ScanPolicyEngine:
    """Execution-layer independent Policy Engine enforcing scope, auth, rate limit, and safety rules."""

    @staticmethod
    def validate_policy(policy: ScanPolicy) -> ScanPolicy:
        """Sanitize and clamp policy parameters within safe execution boundaries."""
        clamped_concurrency = max(1, min(policy.concurrency_limit, 20))
        clamped_rps = max(1, min(policy.rate_limit_rps, 50))
        clamped_depth = max(1, min(policy.max_crawl_depth, 10))
        clamped_requests = max(10, min(policy.max_requests, 5000))
        clamped_timeout = max(1.0, min(policy.timeout_seconds, 300.0))

        return ScanPolicy(
            concurrency_limit=clamped_concurrency,
            rate_limit_rps=clamped_rps,
            respect_robots_txt=policy.respect_robots_txt,
            scope_include_patterns=policy.scope_include_patterns,
            scope_exclude_patterns=policy.scope_exclude_patterns,
            auth_headers=policy.auth_headers,
            auth_cookies=policy.auth_cookies,
            max_crawl_depth=clamped_depth,
            max_requests=clamped_requests,
            timeout_seconds=clamped_timeout,
            stop_on_critical=policy.stop_on_critical,
        )

    @staticmethod
    def is_url_in_scope(url: str, policy: ScanPolicy) -> bool:
        """Evaluate if a target URL is in-scope according to policy rules."""
        if not url:
            return False

        parsed = urlparse(url)
        path = parsed.path or "/"

        # Check exclude patterns first
        for pattern in policy.scope_exclude_patterns:
            if fnmatch(url, pattern) or fnmatch(path, pattern):
                logger.debug("policy.url_excluded", url=url, pattern=pattern)
                return False

        # If include patterns are specified, must match at least one
        if policy.scope_include_patterns:
            matched = any(
                fnmatch(url, pat) or fnmatch(path, pat)
                for pat in policy.scope_include_patterns
            )
            if not matched:
                logger.debug("policy.url_not_included", url=url)
                return False

        return True

    @staticmethod
    def enrich_request_headers(
        headers: Dict[str, str], policy: ScanPolicy
    ) -> Dict[str, str]:
        """Merge policy custom authentication headers into request headers."""
        merged = dict(headers or {})
        if policy.auth_headers:
            merged.update(policy.auth_headers)
        return merged

    @staticmethod
    def enrich_request_cookies(
        cookies: Dict[str, str], policy: ScanPolicy
    ) -> Dict[str, str]:
        """Merge policy custom session cookies into request cookies."""
        merged = dict(cookies or {})
        if policy.auth_cookies:
            merged.update(policy.auth_cookies)
        return merged

    @staticmethod
    def should_stop_on_critical(findings: List[Finding], policy: ScanPolicy) -> bool:
        """Check if any finding is CRITICAL severity and policy enforces stop_on_critical."""
        if not policy.stop_on_critical:
            return False

        for f in findings:
            if f.severity == SeverityLevel.CRITICAL:
                logger.warning(
                    "policy.critical_finding_stop_triggered",
                    finding_title=f.title,
                    plugin_id=f.plugin_id,
                )
                return True
        return False
