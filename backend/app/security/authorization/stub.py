from typing import Any, Callable, Coroutine, Dict


def require_permission(
    permission: str,
) -> Callable[..., Coroutine[Any, Any, Dict[str, Any]]]:
    """Stub dependency factory enforcing RBAC permission checks."""

    async def permission_checker() -> Dict[str, Any]:
        return {"permission": permission, "granted": True}

    return permission_checker
