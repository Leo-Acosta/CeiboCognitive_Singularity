from ceibo_core.agents.base import BaseAgent
from ceibo_core.core.config import settings
from ceibo_core.models.schemas import AgentRole, ChatRequest, ChatResponse, TaskRequest, TaskResponse
from ceibo_core.services.llm import llm_gateway
from ceibo_core.services.orchestration import orchestration_service


class CoreOrchestrator(BaseAgent):
    role = AgentRole.CORE_ORCHESTRATOR
    name = "CORE Orchestrator"
    description = "Coordina agentes, mantiene contexto global y decide el ruteo de tareas."
    capabilities = ["routing", "planning", "context", "tool-coordination", "policy-enforcement"]

    def __init__(self, agents: dict[AgentRole, BaseAgent]) -> None:
        self._agents = agents

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        memory_context = request.metadata.get("memory_context", [])
        context_block = ""
        if memory_context:
            context_block = "\n\nContexto reciente recuperado:\n" + "\n".join(
                f"- {item}" for item in memory_context[-8:]
            )
        system_prompt = (
            "Eres CEIBO CORE, un asistente IA enterprise orientado a agentes, "
            "automatizacion, infraestructura y seguridad defensiva. Responde en forma "
            f"alineada con esta directiva central: {settings.ceibo_core_directive} "
            "clara, profesional y accionable. Usa el contexto recuperado solo si ayuda "
            f"a responder con continuidad.{context_block}"
        )
        response = await llm_gateway.generate(system_prompt=system_prompt, user_message=request.message)
        return ChatResponse(
            response=response,
            agent=self.role,
            session_id=request.session_id,
            memory_context=memory_context,
        )

    async def handle_task(self, request: TaskRequest) -> TaskResponse:
        trace = orchestration_service.plan(request)
        agent = self._agents.get(trace.primary_agent, self)
        if agent.role == self.role:
            return TaskResponse(
                assigned_agent=self.role,
                summary=f"CORE acepto la tarea para planificacion central: {request.goal}",
                orchestration_trace=trace,
            )
        response = await agent.handle_task(request)
        trace.task_id = str(response.task_id)
        trace.steps = [
            step.model_copy(update={"status": "completed"})
            if step.agent in {AgentRole.CORE_ORCHESTRATOR, response.assigned_agent}
            else step
            for step in trace.steps
        ]
        return response.model_copy(update={"orchestration_trace": trace})
