"""Domain Entities and Value Objects for Public Trust Center & Security Disclosures."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SystemHealthStatus(str, Enum):
    """Overall operational system health indicator."""

    OPERATIONAL = "OPERATIONAL"
    DEGRADED_PERFORMANCE = "DEGRADED_PERFORMANCE"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"


class ASVSCategory(str, Enum):
    """OWASP Application Security Verification Standard v4.0 Category References."""

    ARCHITECTURE_V1 = "V1_ARCHITECTURE"
    AUTHENTICATION_V2 = "V2_AUTHENTICATION"
    SESSION_MANAGEMENT_V3 = "V3_SESSION_MANAGEMENT"
    ACCESS_CONTROL_V4 = "V4_ACCESS_CONTROL"
    VALIDATION_SANITIZATION_V5 = "V5_VALIDATION_SANITIZATION"
    CRYPTOGRAPHY_V6 = "V6_CRYPTOGRAPHY"
    WORKER_SANDBOX_V17 = "V17_WORKER_SANDBOX"


@dataclass(frozen=True)
class SecurityPracticeItem:
    """Individual security control mapping against OWASP ASVS v4.0."""

    category: ASVSCategory
    title: str
    description: str
    status: str = "ENFORCED"  # ENFORCED, VERIFIED
    asvs_ref: Optional[str] = None


@dataclass(frozen=True)
class SecurityDisclosureInfo:
    """RFC 9116 Security Disclosure & Vulnerability Reporting Policy Metadata."""

    contact_email: str = "security@vulnova.com"
    pgp_key_url: str = "https://vulnova.com/security.asc"
    policy_url: str = "https://vulnova.com/security"
    preferred_languages: str = "en, es"
    canonical_url: str = "https://vulnova.com/.well-known/security.txt"
    expires_at: str = "2027-12-31T23:59:59.000Z"
    hiring_url: str = "https://vulnova.com/careers"
