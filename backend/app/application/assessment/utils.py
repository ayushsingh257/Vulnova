"""Utility functions for Assessment and Target Masking."""

import re
from urllib.parse import urlparse


def mask_target_url(target_url: str) -> str:
    """Mask target URL domain/hostname to protect infrastructure privacy in list views.

    Example:
        'https://api.staging.example.com' -> 'https://a***.s***.e***.com'
        'http://internal-auth.domain.org:8080' -> 'http://i***.d***.org:8080'
    """
    if not target_url:
        return ""

    try:
        parsed = urlparse(target_url)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc

        # Split host and port if present
        if ":" in netloc:
            host, port = netloc.split(":", 1)
            port_suffix = f":{port}"
        else:
            host = netloc
            port_suffix = ""

        # Mask domain labels
        parts = host.split(".")
        masked_parts = []
        for idx, part in enumerate(parts):
            # Keep top-level domain unmasked if >1 label and last part
            if len(parts) > 1 and idx == len(parts) - 1:
                masked_parts.append(part)
            elif len(part) > 1:
                masked_parts.append(f"{part[0]}***")
            else:
                masked_parts.append(part)

        masked_host = ".".join(masked_parts)
        path = parsed.path if parsed.path and parsed.path != "/" else ""
        return f"{scheme}://{masked_host}{port_suffix}{path}"
    except Exception:
        # Fallback mask for unparseable strings
        return re.sub(r"(?<=://)[^/]+", "m***.target.local", target_url)
