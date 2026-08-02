"""Certificate Transparency (CT) Log Passive Discovery Client."""

from typing import List, Set
from urllib.parse import urlparse

import httpx

from app.core.logging import get_logger

logger = get_logger("vulnova.ct_logs")

CRT_SH_API_URL = "https://crt.sh/"
DEFAULT_TIMEOUT_SECONDS = 15.0


class CTLogsClient:
    """Passive Certificate Transparency log client for domain name discovery."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout

    async def search_subdomains(self, base_domain: str) -> List[str]:
        """Query Certificate Transparency logs for subdomains belonging to base domain."""
        clean_domain = base_domain.strip().lower()

        # Strip protocol if user passed URL
        if clean_domain.startswith(("http://", "https://")):
            parsed = urlparse(clean_domain)
            clean_domain = (parsed.hostname or "").lower()

        subdomains: Set[str] = set()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "Vulnova-AppSec-ASM/1.0"},
            ) as client:
                params = {"q": f"%.{clean_domain}", "output": "json"}
                response = await client.get(CRT_SH_API_URL, params=params)

                if response.status_code == 200:
                    data = response.json()
                    for entry in data:
                        name_value = entry.get("name_value", "")
                        for line in name_value.split("\n"):
                            line_clean = line.strip().lower()

                            # Remove wildcard prefix (*.domain.com -> domain.com)
                            if line_clean.startswith("*."):
                                line_clean = line_clean[2:]

                            # Ensure it is a valid subdomain under clean_domain
                            if line_clean == clean_domain or line_clean.endswith(
                                f".{clean_domain}"
                            ):
                                subdomains.add(line_clean)

        except Exception as e:
            logger.warning(
                "ct_logs.query_failed",
                domain=clean_domain,
                error=str(e),
            )

        # Include root domain in discovered list
        subdomains.add(clean_domain)
        result = sorted(list(subdomains))

        logger.info(
            "ct_logs.completed",
            domain=clean_domain,
            discovered_count=len(result),
        )

        return result
