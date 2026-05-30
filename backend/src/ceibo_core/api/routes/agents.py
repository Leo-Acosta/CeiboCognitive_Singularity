from fastapi import APIRouter

from ceibo_core.agents.registry import agent_registry
from ceibo_core.models.schemas import AgentDescriptor

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentDescriptor])
async def list_agents() -> list[AgentDescriptor]:
    return [agent.descriptor() for agent in agent_registry.values()]
