"""Recovery Code Management Service for MFA Account Recovery.

Handles generation of 10 single-use recovery codes, cryptographic SHA-256 hashing
before storage, verification against hashed records, and single-use consumption.
"""

import hashlib
import json
import secrets
import string
from typing import List, Tuple

import structlog

logger = structlog.get_logger(__name__)


class RecoveryService:
    """Service handling MFA single-use backup recovery codes."""

    @staticmethod
    def generate_recovery_codes(count: int = 10) -> List[str]:
        """Generate `count` random 10-character formatted recovery codes e.g. 'A1B2-C3D4-E5'."""
        alphabet = string.ascii_uppercase + string.digits
        codes: List[str] = []
        for _ in range(count):
            part1 = "".join(secrets.choice(alphabet) for _ in range(4))
            part2 = "".join(secrets.choice(alphabet) for _ in range(4))
            part3 = "".join(secrets.choice(alphabet) for _ in range(2))
            codes.append(f"{part1}-{part2}-{part3}")
        return codes

    @staticmethod
    def hash_code(code: str) -> str:
        """Hash a single recovery code using SHA-256 for secure storage."""
        code_normalized = code.strip().replace("-", "").upper()
        return hashlib.sha256(code_normalized.encode("utf-8")).hexdigest()

    @classmethod
    def hash_recovery_codes(cls, codes: List[str]) -> List[str]:
        """Hash a list of plaintext recovery codes."""
        return [cls.hash_code(c) for c in codes]

    @classmethod
    def verify_and_consume(
        cls, hashed_codes_json: str, input_code: str
    ) -> Tuple[bool, str, int]:
        """Verify input code against hashed codes list.

        Returns: (is_valid, updated_hashed_codes_json, remaining_count)
        """
        if not hashed_codes_json or not input_code:
            return False, hashed_codes_json or "[]", 0

        try:
            hashed_list: List[str] = json.loads(hashed_codes_json)
        except Exception as err:
            logger.error("parse_backup_codes_json_failed", error=str(err))
            return False, "[]", 0

        target_hash = cls.hash_code(input_code)
        if target_hash in hashed_list:
            hashed_list.remove(target_hash)
            updated_json = json.dumps(hashed_list)
            return True, updated_json, len(hashed_list)

        return False, json.dumps(hashed_list), len(hashed_list)

    @staticmethod
    def get_remaining_count(hashed_codes_json: str) -> int:
        """Get the count of active remaining backup codes."""
        if not hashed_codes_json:
            return 0
        try:
            hashed_list: List[str] = json.loads(hashed_codes_json)
            return len(hashed_list)
        except Exception:
            return 0
