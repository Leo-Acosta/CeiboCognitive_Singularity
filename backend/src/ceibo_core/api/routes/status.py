from fastapi import APIRouter

from ceibo_core.agents.registry import agent_registry
from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.core.config import settings
from ceibo_core.models.schemas import CoreStatus, SingularityIndex
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
