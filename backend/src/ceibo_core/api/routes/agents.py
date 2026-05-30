from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.agents.registry import agent_registry
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import AgentDescriptor, OrchestrationTraceRecord, TaskRequest
from ceibo_core.services.orchestration import orchestration_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentDescriptor])
async def list_agents() -> list[AgentDescriptor]:
    return [agent.descriptor() for agent in agent_registry.values()]


@router.post("/orchestration/plan", response_model=OrchestrationTraceRecord)
async def plan_orchestration(request: TaskRequest) -> OrchestrationTraceRecord:
    return orchestration_service.plan(request)


@router.get("/orchestration/recent", response_model=list[OrchestrationTraceRecord])
async def recent_orchestration(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[OrchestrationTraceRecord]:
    return await orchestration_service.recent(db, limit=limit)
