from ceibo_core.agents.base import BaseAgent
from ceibo_core.agents.orchestrator import CoreOrchestrator
from ceibo_core.agents.specialized import build_specialized_agents
from ceibo_core.models.schemas import AgentRole


def build_agent_registry() -> dict[AgentRole, BaseAgent]:
    specialized = {agent.role: agent for agent in build_specialized_agents()}
    orchestrator = CoreOrchestrator(specialized)
    return {AgentRole.CORE_ORCHESTRATOR: orchestrator, **specialized}


agent_registry = build_agent_registry()
