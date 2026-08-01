from fastapi import APIRouter

from app.api.v1.routers import status

api_v1_router = APIRouter()
api_v1_router.include_router(status.router)
