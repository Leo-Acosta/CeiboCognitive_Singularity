from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.agents.registry import agent_registry
from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.core.config import settings
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import CoreStatus, SingularityIndex, SingularitySnapshotRecord
from ceibo_core.services.memory import memory_service
from ceibo_core.services.singularity_index import singularity_index_service

router = APIRouter(prefix="/status", tags=["status"])


@router.get("", response_model=CoreStatus)
async def core_status() -> CoreStatus:
    memory_status = await memory_service.status()
    engine_status = ceibo_engine.status()
    return CoreStatus(
        service=settings.app_name,
        environment=settings.environment,
        agents_online=len(agent_registry),
        persistence_enabled=settings.persistence_enabled,
        event_bus_enabled=settings.event_bus_enabled,
        llm_provider=settings.default_llm_provider,
        default_model=settings.openai_model,
        memory_backend=memory_status.backend,
        vector_memory_enabled=memory_status.vector_enabled,
        embedding_provider=memory_status.embedding_provider,
        engine_model_id=engine_status.model_id,
        engine_mode=engine_status.mode,
        core_directive=engine_status.core_directive,
    )


@router.get("/singularity-index", response_model=SingularityIndex)
async def singularity_index() -> SingularityIndex:
    return await singularity_index_service.calculate()


@router.post("/singularity-index/snapshots", response_model=SingularitySnapshotRecord)
async def capture_singularity_snapshot(
    db: AsyncSession = Depends(get_db),
) -> SingularitySnapshotRecord:
    return await singularity_index_service.capture_snapshot(
        db,
        metadata={"source": "api"},
    )


@router.get("/singularity-index/history", response_model=list[SingularitySnapshotRecord])
async def singularity_index_history(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[SingularitySnapshotRecord]:
    return await singularity_index_service.history(db, limit=limit)
