from ceibo_core.agents.base import BaseAgent
from ceibo_core.models.schemas import AgentRole, ChatRequest, ChatResponse, TaskRequest, TaskResponse


class StaticCapabilityAgent(BaseAgent):
    def __init__(
        self,
        role: AgentRole,
        name: str,
        description: str,
        capabilities: list[str],
    ) -> None:
        self.role = role
        self.name = name
        self.description = description
        self.capabilities = capabilities

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            response=(
                f"{self.name} recibio el mensaje y esta listo para ejecutar capacidades: "
                f"{', '.join(self.capabilities)}."
            ),
            agent=self.role,
        )

    async def handle_task(self, request: TaskRequest) -> TaskResponse:
        return TaskResponse(
            assigned_agent=self.role,
            summary=f"{self.name} acepto la tarea: {request.goal}",
        )


def build_specialized_agents() -> list[BaseAgent]:
    return [
        StaticCapabilityAgent(
            AgentRole.INFRASTRUCTURE,
            "Infrastructure Agent",
            "Gestiona Docker, Kubernetes, deployments, logs y monitoreo.",
            ["kubernetes", "docker", "deployments", "logs", "monitoring"],
        ),
        StaticCapabilityAgent(
            AgentRole.CYBERSECURITY,
            "Cybersecurity Agent",
            "Analiza logs, postura defensiva, hardening y anomalas.",
            ["defensive-monitoring", "log-analysis", "hardening", "audit"],
        ),
        StaticCapabilityAgent(
            AgentRole.RESEARCH,
            "Research Agent",
            "Investiga, resume y sintetiza informacion tecnica.",
            ["search", "summarization", "technical-analysis", "citations"],
        ),
        StaticCapabilityAgent(
            AgentRole.AUTOMATION,
            "Automation Agent",
            "Ejecuta workflows, scripts y automatizacion web o desktop.",
            ["playwright", "selenium", "scripts", "workflows"],
        ),
        StaticCapabilityAgent(
            AgentRole.MEMORY,
            "Memory Agent",
            "Administra memoria de largo plazo, embeddings y recuperacion contextual.",
            ["rag", "embeddings", "vector-search", "context-retrieval"],
        ),
        StaticCapabilityAgent(
            AgentRole.VOICE,
            "Voice Agent",
            "Procesa STT, TTS, wake word y conversacion natural.",
            ["whisper", "piper-tts", "wake-word", "voice-session"],
        ),
        StaticCapabilityAgent(
            AgentRole.SYSTEM_CONTROL,
            "System Control Agent",
            "Controla archivos, terminal, procesos y recursos locales bajo sandbox.",
            ["filesystem", "terminal", "processes", "sandbox"],
        ),
    ]
