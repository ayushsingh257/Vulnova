"""Security Policy Validator for Ephemeral Scanner Execution Sandboxes."""

import ipaddress
from typing import Tuple
from urllib.parse import urlparse

from app.core.exceptions import VulnovaException
from app.infrastructure.scanner_sandbox.dto import SandboxSecurityConfigDTO


class SandboxSecurityViolationException(VulnovaException):
    """Raised when scanner sandbox security constraints or egress rules are violated."""

    def __init__(self, detail: str) -> None:
        super().__init__(message=f"Scanner Sandbox Security Policy Violation: {detail}")


class ScannerSecurityPolicy:
    """Enforces zero-trust isolation rules, resource limits, and network blocklists."""

    # Default RFC1918 & Cloud Metadata Networks
    PROHIBITED_NETWORKS = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.169.254/32"),
        ipaddress.ip_network("0.0.0.0/8"),
    ]

    @classmethod
    def validate_security_config(
        cls, config: SandboxSecurityConfigDTO
    ) -> SandboxSecurityConfigDTO:
        """Validate security configuration limits to prevent denial-of-service or privilege escalation."""
        # 1. Non-root user validation
        if config.non_root_uid == 0 or config.non_root_gid == 0:
            raise SandboxSecurityViolationException(
                "Root execution (UID/GID 0) is strictly forbidden in scanner sandboxes."
            )

        # 2. Capabilities check
        if "ALL" not in config.drop_capabilities and len(config.drop_capabilities) < 5:
            raise SandboxSecurityViolationException(
                "Scanner sandbox must drop ALL or major Linux capabilities."
            )

        # 3. CPU Limit parsing & bounds check (Max 2.0 CPUs)
        cpu_val = (
            float(config.cpu_limit.rstrip("m")) / 1000.0
            if "m" in config.cpu_limit
            else float(config.cpu_limit)
        )
        if cpu_val > 2.0 or cpu_val <= 0:
            raise SandboxSecurityViolationException(
                f"Invalid CPU allocation '{config.cpu_limit}'. Must be between 0.1 and 2.0 CPUs."
            )

        # 4. Memory limit bounds check (Max 2048m)
        mem_str = config.memory_limit.lower()
        if mem_str.endswith("g"):
            mem_mb = float(mem_str.rstrip("g")) * 1024
        elif mem_str.endswith("m"):
            mem_mb = float(mem_str.rstrip("m"))
        else:
            mem_mb = float(mem_str) / (1024 * 1024)

        if mem_mb > 2048 or mem_mb < 64:
            raise SandboxSecurityViolationException(
                f"Invalid Memory allocation '{config.memory_limit}'. Must be between 64m and 2048m."
            )

        # 5. Process limit check
        if config.max_processes > 200 or config.max_processes < 10:
            raise SandboxSecurityViolationException(
                "Process limit (max_processes) must be between 10 and 200."
            )

        # 6. Timeout check
        if (
            config.execution_timeout_seconds > 3600
            or config.execution_timeout_seconds < 10
        ):
            raise SandboxSecurityViolationException(
                "Execution timeout must be between 10 and 3600 seconds."
            )

        return config

    @classmethod
    def validate_target_address(cls, target_url: str) -> Tuple[bool, str]:
        """Verify target domain or IP is not pointing to restricted private RFC1918 networks."""
        try:
            parsed = urlparse(target_url)
            hostname = parsed.hostname or target_url
            # Remove port if present in raw target_url string
            if ":" in hostname and not hostname.startswith("["):
                hostname = hostname.split(":")[0]

            # Check if host is a direct IP
            try:
                ip_obj = ipaddress.ip_address(hostname)
                for prohibited in cls.PROHIBITED_NETWORKS:
                    if ip_obj in prohibited:
                        return (
                            False,
                            f"Target IP {hostname} resides in prohibited private network {prohibited}.",
                        )
            except ValueError:
                # Target is a domain name (e.g. example.com, localhost)
                if hostname.lower() in (
                    "localhost",
                    "localhost.localdomain",
                    "127.0.0.1",
                ):
                    return (
                        False,
                        "Scanning localhost or loopback interfaces is prohibited.",
                    )

            return True, "Target address validated successfully."
        except Exception as err:
            return False, f"Target validation failed: {str(err)}"
