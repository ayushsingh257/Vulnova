"""SSRF Egress Firewall and Target Domain Scope Validator."""

import ipaddress
import socket
from typing import Any, Dict, Set, Tuple
from urllib.parse import urlparse

# Allowed scheme whitelist
ALLOWED_SCHEMES: Set[str] = {"http", "https"}

# Blocked schemes explicit blacklist for audit verification
BLOCKED_SCHEMES: Set[str] = {
    "file",
    "ftp",
    "gopher",
    "javascript",
    "data",
    "mailto",
    "tel",
    "dict",
    "ldap",
}


def is_allowed_scheme(url: str) -> bool:
    """Validate URL scheme is strictly http or https."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    return scheme in ALLOWED_SCHEMES


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address string belongs to a loopback, private, or metadata range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or str(ip) == "0.0.0.0"  # noqa: S104
        )
    except ValueError:
        return True


def classify_ip(ip_str: str) -> Dict[str, Any]:
    """Classify an IP address as PUBLIC, PRIVATE, LOOPBACK, LINK_LOCAL, or RESERVED.

    Preserves internal IP findings for enterprise ASM intelligence while maintaining
    egress safety flags for HTTP scanning.
    """
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        if ip.is_loopback:
            cls = "LOOPBACK"
            is_internal = True
        elif ip.is_private:
            cls = "PRIVATE"
            is_internal = True
        elif ip.is_link_local:
            cls = "LINK_LOCAL"
            is_internal = True
        elif ip.is_reserved or ip.is_multicast:
            cls = "RESERVED"
            is_internal = True
        else:
            cls = "PUBLIC"
            is_internal = False

        return {
            "value": str(ip),
            "classification": cls,
            "is_internal": is_internal,
            "is_egress_safe": not is_internal,
        }
    except ValueError:
        return {
            "value": ip_str,
            "classification": "UNKNOWN",
            "is_internal": False,
            "is_egress_safe": False,
        }


def resolve_hostname(hostname: str) -> Tuple[bool, str]:
    """Resolve a hostname to its IP address and verify it is a public egress target."""
    clean_host = hostname.strip().lower().split(":")[0]

    # Quick check for raw IP string
    try:
        ip = ipaddress.ip_address(clean_host)
        if is_private_ip(str(ip)):
            return False, f"Target IP '{clean_host}' is a private or metadata address"
        return True, str(ip)
    except ValueError:
        pass

    # DNS resolution
    try:
        addr_info = socket.getaddrinfo(clean_host, None)
        for _family, _, _, _, sockaddr in addr_info:
            ip_str = str(sockaddr[0])
            if is_private_ip(ip_str):
                return (
                    False,
                    f"Target host '{clean_host}' resolves to private IP '{ip_str}'",
                )
        return True, "Public IP"
    except socket.gaierror as e:
        return False, f"Failed to resolve host '{clean_host}': {e}"


def is_safe_target_url(url: str) -> Tuple[bool, str]:
    """Comprehensive SSRF check validating scheme and IP resolution safety."""
    if not is_allowed_scheme(url):
        parsed = urlparse(url)
        return (
            False,
            f"URL scheme '{parsed.scheme}' is prohibited. Only HTTP and HTTPS are allowed",
        )

    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid target URL: missing hostname"

    return resolve_hostname(hostname)


def extract_base_domain(url: str) -> str:
    """Extract clean base domain from target URL or domain string (e.g. 'https://app.example.com/login' or 'api.example.com' -> 'example.com')."""
    clean_target = url.strip().lower()
    if not clean_target.startswith(("http://", "https://")):
        clean_target = f"https://{clean_target}"

    parsed = urlparse(clean_target)
    hostname = (parsed.hostname or "").lower().split(":")[0]
    parts = hostname.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return hostname


def is_url_in_scope(url: str, base_domain: str, allow_subdomains: bool = False) -> bool:
    """Check if a URL belongs to the allowed domain target scope."""
    if not is_allowed_scheme(url):
        return False

    parsed = urlparse(url)
    target_host = (parsed.hostname or "").lower()
    clean_base = base_domain.lower()

    if target_host == clean_base or target_host == f"www.{clean_base}":
        return True

    if allow_subdomains and (
        target_host.endswith(f".{clean_base}") or target_host == clean_base
    ):
        return True

    return False
