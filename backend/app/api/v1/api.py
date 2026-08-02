from fastapi import APIRouter

from app.api.v1.routers import api_keys, auth, status

api_v1_router = APIRouter()
api_v1_router.include_router(status.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(api_keys.router)
