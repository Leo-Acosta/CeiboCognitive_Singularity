from abc import ABC, abstractmethod

from ceibo_core.models.schemas import AgentDescriptor, AgentRole, ChatRequest, ChatResponse, TaskRequest, TaskResponse


class BaseAgent(ABC):
    role: AgentRole
    name: str
    description: str
    capabilities: list[str]

    def descriptor(self) -> AgentDescriptor:
        return AgentDescriptor(
            role=self.role,
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
        )

    @abstractmethod
    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError

    @abstractmethod
    async def handle_task(self, request: TaskRequest) -> TaskResponse:
        raise NotImplementedError
