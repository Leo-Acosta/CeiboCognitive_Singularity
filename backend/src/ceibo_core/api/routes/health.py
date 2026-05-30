from fastapi import APIRouter

from ceibo_core.core.config import settings
from ceibo_core.db.session import persistence_health
from ceibo_core.models.schemas import PersistenceHealth

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/health/persistence", response_model=PersistenceHealth)
async def health_persistence() -> PersistenceHealth:
    return await persistence_health()
