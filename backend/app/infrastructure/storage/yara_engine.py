"""YARA Static Malware Detection Engine for Evidence Artifact Protection (Phase 12.9)."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("vulnova.yara_engine")

try:
    import yara  # type: ignore

    YARA_AVAILABLE = True
except ImportError:
    yara = None
    YARA_AVAILABLE = False


class YARAMatchResult:
    """Represents a YARA static malware match result."""

    def __init__(
        self,
        matched: bool,
        rule_name: Optional[str] = None,
        severity: str = "INFO",
        description: str = "",
        strings_matched: Optional[List[str]] = None,
    ) -> None:
        self.matched = matched
        self.rule_name = rule_name
        self.severity = severity
        self.description = description
        self.strings_matched = strings_matched or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "matched": self.matched,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "description": self.description,
            "strings_matched": self.strings_matched,
        }


class YARAEngine:
    """Static inspection engine executing YARA security rules against evidence file payloads."""

    def __init__(self, rules_dir: Optional[str] = None) -> None:
        self.rules_dir = Path(rules_dir or settings.yara_rules_dir)
        self.compiled_rules = None
        self._load_rules()

    def _load_rules(self) -> None:
        """Load and compile YARA rules from disk, or initialize fallback rules."""
        if YARA_AVAILABLE and self.rules_dir.exists():
            rule_files = list(self.rules_dir.glob("*.yar")) + list(
                self.rules_dir.glob("*.yara")
            )
            if rule_files:
                try:
                    filepaths = {
                        f"rule_{i}": str(f.resolve()) for i, f in enumerate(rule_files)
                    }
                    self.compiled_rules = yara.compile(filepaths=filepaths)
                    logger.info("yara_engine.rules_compiled", count=len(rule_files))
                    return
                except Exception as exc:
                    logger.warning("yara_engine.native_compile_failed", error=str(exc))

        logger.info("yara_engine.using_pure_python_matcher")

    def scan_bytes(self, content: bytes) -> YARAMatchResult:
        """Scan binary file payload bytes against loaded YARA malware signatures."""
        if not content:
            return YARAMatchResult(matched=False)

        # 1. Native YARA scanning if available
        if YARA_AVAILABLE and self.compiled_rules:
            try:
                matches = self.compiled_rules.match(data=content)
                if matches:
                    top_match = matches[0]
                    meta = top_match.meta or {}
                    matched_strings = [str(s[2]) for s in top_match.strings[:5]]
                    return YARAMatchResult(
                        matched=True,
                        rule_name=top_match.rule,
                        severity=meta.get("severity", "HIGH"),
                        description=meta.get(
                            "description", "Malware pattern detected by YARA"
                        ),
                        strings_matched=matched_strings,
                    )
            except Exception as exc:
                logger.error("yara_engine.native_scan_failed", error=str(exc))

        # 2. Pure Python fallback pattern matching
        return self._pure_python_scan(content)

    def _pure_python_scan(self, content: bytes) -> YARAMatchResult:
        """Fallback pattern matcher for YARA rules in pure Python."""
        # Check Test Antivirus Signature
        if b"VULNOVA-MALWARE-TEST-SIGNATURE" in content:
            return YARAMatchResult(
                matched=True,
                rule_name="Vulnova_Test_Antivirus_File",
                severity="CRITICAL",
                description="Standard Anti-Virus Test File Signature",
                strings_matched=["VULNOVA-MALWARE-TEST-SIGNATURE"],
            )

        # Check Disguised Executable (PE MZ / ELF at offset 0)
        if content.startswith(b"MZ"):
            return YARAMatchResult(
                matched=True,
                rule_name="Vulnova_Disguised_Executable",
                severity="CRITICAL",
                description="Detects PE binary headers disguised in evidence attachments",
                strings_matched=["MZ_header_at_offset_0"],
            )
        if content.startswith(b"\x7fELF"):
            return YARAMatchResult(
                matched=True,
                rule_name="Vulnova_Disguised_Executable",
                severity="CRITICAL",
                description="Detects ELF binary headers disguised in evidence attachments",
                strings_matched=["ELF_header_at_offset_0"],
            )

        content_lower = content.lower()

        # Check Webshell Patterns
        php_patterns = [
            b"eval(base64_decode(",
            b"gzinflate(base64_decode(",
            b"shell_exec(",
            b"passthru(",
            b"proc_open(",
            b"system($_get[",
            b"system($_post[",
        ]
        matched_php = [p.decode("utf-8") for p in php_patterns if p in content_lower]
        if matched_php:
            return YARAMatchResult(
                matched=True,
                rule_name="Vulnova_Webshell_PHP",
                severity="HIGH",
                description="Detects malicious PHP webshells and command execution scripts",
                strings_matched=matched_php,
            )

        # Check Credential Harvester Patterns
        cred_patterns = [
            b"-----begin rsa private key-----",
            b"-----begin openssh private key-----",
            b"-----begin pgp private key block-----",
            b"aws_secret_access_key",
            b"root:$6$",
        ]
        matched_creds = [c.decode("utf-8") for c in cred_patterns if c in content_lower]
        if matched_creds:
            return YARAMatchResult(
                matched=True,
                rule_name="Vulnova_Credential_Harvester",
                severity="HIGH",
                description="Detects embedded private keys, shadow files, or cloud credentials in evidence logs",
                strings_matched=matched_creds,
            )

        return YARAMatchResult(matched=False)


# Default singleton instance
yara_engine = YARAEngine()
