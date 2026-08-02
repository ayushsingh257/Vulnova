from fastapi import APIRouter

from app.api.v1.routers import (
    api_keys,
    audit_logs,
    auth,
    organizations,
    status,
    users,
)

api_v1_router = APIRouter()
api_v1_router.include_router(status.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(api_keys.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(organizations.router)
api_v1_router.include_router(audit_logs.router)
