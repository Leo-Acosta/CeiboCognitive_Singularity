import pytest

from ceibo_core.services.dialogue_orchestrator import DialogueOrchestratorService
from ceibo_core.services.human_conversation import human_conversation_service


@pytest.mark.asyncio
async def test_human_conversation_builds_messages(monkeypatch):
    async def fake_chat(messages, temperature=0.7, max_tokens=None):
        return "respuesta de prueba"

    monkeypatch.setattr("ceibo_core.services.llm_gateway.llm_gateway.chat", fake_chat)

    resp = await human_conversation_service.respond(
        user_message="Hola, contame algo",
        conversation_history=[{"role": "user", "content": "Hola"}],
    )
    assert isinstance(resp, dict)
    assert "response" in resp
    assert resp["dialogue_trace"]["analysis"]["cognitive_route"]


def test_dialogue_orchestrator_detects_technical_cognition_route():
    service = DialogueOrchestratorService()

    analysis = service.analyze("Crea un endpoint FastAPI con tests", safety_class="normal")

    assert analysis.intent == "technical_build"
    assert analysis.cognitive_route == "devcore_reasoning"
    assert analysis.response_style == "precise_actionable"


@pytest.mark.asyncio
async def test_dialogue_orchestrator_uses_fast_tool_router_for_time():
    service = DialogueOrchestratorService()

    result = await service.respond(user_message="que hora es?")

    assert "hora local" in result.response.lower()
    assert result.trace.selected_module == "chat_tool_router"
    assert result.trace.tool_used == "time.local"


@pytest.mark.asyncio
async def test_dialogue_orchestrator_keeps_tool_query_when_message_has_greeting():
    service = DialogueOrchestratorService()

    result = await service.respond(user_message="hola Ceibo, que hora es?")

    assert "hora local" in result.response.lower()
    assert result.trace.selected_module == "chat_tool_router"
    assert result.trace.tool_used == "time.local"


@pytest.mark.asyncio
async def test_dialogue_orchestrator_keeps_human_dialogue_out_of_project_tool():
    service = DialogueOrchestratorService()

    result = await service.respond(
        user_message="hola Ceibo, quiero que conversemos con mas naturalidad e interpretes ironias"
    )

    assert "natural" in result.response.lower()
    assert "ironia" in result.response.lower()
    assert result.trace.analysis.cognitive_route == "human_dialogue"
    assert result.trace.selected_module == "human_dialogue"
    assert result.trace.tool_used is None


@pytest.mark.asyncio
async def test_dialogue_orchestrator_blocks_abuse_before_model():
    service = DialogueOrchestratorService()

    result = await service.respond(user_message="quiero hackear y robar credenciales")

    assert "no puedo ayudar" in result.response.lower()
    assert result.trace.selected_module == "safety_supervisor"
    assert result.trace.analysis.safety_class == "blocked_abuse"
