"""File Upload Magic Byte Security Inspection Middleware (Phase 12.9)."""

from typing import Tuple

from fastapi import HTTPException, status


class UploadSecurityValidator:
    """Validates uploaded evidence payloads via raw binary magic byte header inspection."""

    # Disallowed binary executable headers
    DISALLOWED_HEADERS = [
        (b"MZ", "Windows PE Executable / DLL"),
        (b"\x7fELF", "Linux ELF Executable / Shared Object"),
        (b"\xca\xfe\xba\xbe", "Java Class File / Mach-O Binary"),
        (b"\xfe\xed\xfa\xce", "Mach-O Binary"),
        (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit Binary"),
    ]

    # Valid magic byte signatures
    MAGIC_SIGNATURES = {
        "pdf": [b"%PDF-"],
        "png": [b"\x89PNG\r\n\x1a\n"],
        "jpeg": [b"\xff\xd8\xff"],
        "gif": [b"GIF87a", b"GIF89a"],
        "zip": [b"PK\x03\x04", b"PK\x05\x06"],
        "gz": [b"\x1f\x8b"],
        "pcap": [b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x0a\x0d\x0d\x0a"],
    }

    @classmethod
    def validate_payload(cls, filename: str, content: bytes) -> Tuple[bool, str, str]:
        """Inspect raw byte header to ensure payload is authentic and not a disguised binary executable.

        Returns (is_valid, detected_mime, description).
        Raises HTTPException(400) if validation fails.
        """
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty evidence file payload.",
            )

        # 1. Reject Disallowed Binary Executables Immediately
        for header, desc in cls.DISALLOWED_HEADERS:
            if content.startswith(header):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security violation: Executable payload detected ({desc}). Binary uploads are forbidden.",
                )

        # 2. Check WEBP Special Case (RIFF....WEBP)
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return True, "image/webp", "WebP Image"

        # 3. Match Standard Magic Byte Signatures
        for file_type, sigs in cls.MAGIC_SIGNATURES.items():
            for sig in sigs:
                if content.startswith(sig):
                    mime = f"application/{file_type}"
                    if file_type in ("png", "jpeg", "gif"):
                        mime = f"image/{file_type}"
                    return True, mime, f"Validated {file_type.upper()} file"

        # 4. Text / Log File Validation (Ensure plain text, non-binary)
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext in ("log", "txt", "json", "csv", "xml", "html"):
            # Check non-printable ratio to verify text file authenticity
            sample = content[:2048]
            non_printable = sum(1 for b in sample if b < 9 or (b > 13 and b < 32))
            if len(sample) > 0 and (non_printable / len(sample)) > 0.1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Text/Log file contains excessive non-printable binary characters.",
                )
            return True, "text/plain", "Validated Plain Text / Log file"

        # 5. Allow standard safe file types if binary executable checks passed
        return True, "application/octet-stream", "Generic Evidence File"
