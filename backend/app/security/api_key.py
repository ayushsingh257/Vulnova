"""Vulnova API Key Security Module.

Provides raw API key generation, prefix extraction, SHA-256 hashing,
and constant-time key verification.
"""

import hashlib
import hmac
import secrets
from typing import Tuple

API_KEY_PREFIX = "vn_live_"
PREFIX_LENGTH = 8  # "vn_live_" is 8 characters


def generate_api_key(prefix_label: str = API_KEY_PREFIX) -> Tuple[str, str, str]:
    """Generate a new secure API key payload.

    Key format: prefix_label (8 chars) + 32-byte URL-safe secret token.

    Returns:
        Tuple of (raw_key, key_prefix, key_hash)
        - raw_key: Returned ONLY ONCE to caller. Never stored in DB.
        - key_prefix: First 8 characters stored unhashed for DB lookup.
        - key_hash: SHA-256 hex digest stored in DB.
    """
    secret = secrets.token_urlsafe(32)
    raw_key = f"{prefix_label}{secret}"
    key_prefix = raw_key[:PREFIX_LENGTH]
    key_hash = hash_api_key(raw_key)

    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    """Compute SHA-256 hex digest of a raw API key.

    Args:
        raw_key: The raw API key string.

    Returns:
        64-character SHA-256 hex digest string.
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Verify a raw API key against its SHA-256 hashed digest in constant time.

    Args:
        raw_key: The candidate raw API key string.
        hashed_key: The stored SHA-256 hex digest.

    Returns:
        True if hashes match, False otherwise.
    """
    computed_hash = hash_api_key(raw_key)
    return hmac.compare_digest(computed_hash.lower(), hashed_key.lower())
