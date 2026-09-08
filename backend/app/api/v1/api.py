from fastapi import APIRouter

from app.api.v1.endpoints import (
    engineering,
    health,
    history,
    investigations,
    repositories,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(history.router, prefix="/repositories", tags=["history"])
api_router.include_router(engineering.router, prefix="/repositories", tags=["engineering"])
api_router.include_router(investigations.router, prefix="/investigations", tags=["investigations"])
