from fastapi import APIRouter

from app.api.v1.endpoints import health, investigations, repositories

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(investigations.router, prefix="/investigations", tags=["investigations"])
