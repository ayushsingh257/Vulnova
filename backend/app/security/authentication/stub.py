from typing import Any, Dict


async def get_current_user() -> Dict[str, Any]:
    """Stub dependency injector for user authentication context."""
    return {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": "admin@vulnova.local",
        "role": "platform_admin",
        "tenant_id": "00000000-0000-0000-0000-000000000000",
    }
