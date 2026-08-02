"""Client HTTP Request Context Dependency Helper."""

from typing import Optional, Tuple

from fastapi import Request


def get_client_info(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """Extract client IP address (supporting X-Forwarded-For) and User-Agent string from HTTP Request."""
    client_ip: Optional[str] = None

    # Check X-Forwarded-For header first (proxy / load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # First entry in comma-separated chain is the client IP
        client_ip = forwarded_for.split(",")[0].strip()
    elif request.client and request.client.host:
        client_ip = request.client.host

    user_agent = request.headers.get("user-agent")

    return client_ip, user_agent
