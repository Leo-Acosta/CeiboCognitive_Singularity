import pytest

from ceibo_core.services.dialogue_orchestrator import DialogueOrchestratorService
from ceibo_core.services.human_conversation import human_conversation_service
from ceibo_core.security.safety_supervisor import safety_supervisor


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


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "Crea un endpoint FastAPI con tests",
            {
                "intent": "technical_build",
                "route": "devcore_reasoning",
                "memory": "short_term_context",
            },
        ),
        (
            "arregla eso",
            {
                "route": "general_reasoning",
                "min_ambiguity": 0.35,
                "memory": "short_term_context",
            },
        ),
        (
            "si claro, buenisimo... ahora todo funciona perfecto jaja",
            {
                "tone": "humor_o_ironia",
                "min_irony": 0.65,
                "memory": "blocked_transient_memory",
            },
        ),
        (
            "estoy frustrado, no funciona nada",
            {
                "tone": "frustracion_o_preocupacion",
                "memory": "blocked_transient_memory",
            },
        ),
        (
            "sos un idiota, esto es una mierda",
            {
                "tone": "agresivo",
                "memory": "blocked_transient_memory",
            },
        ),
        (
            "hola, necesito hablar un poco",
            {
                "intent": "emotional_dialogue",
                "route": "human_dialogue",
            },
        ),
        (
            "prefiero que CEIBO me responda breve y con pasos concretos",
            {
                "memory": "candidate_autobiographical_memory",
            },
        ),
        (
            "prefiero hoy mirar esto rapido",
            {
                "memory": "short_term_context",
            },
        ),
        (
            "mi objetivo de largo plazo es que CEIBO sea el cerebro de un robot",
            {
                "memory": "candidate_autobiographical_memory",
            },
        ),
        (
            "hoy estoy triste",
            {
                "memory": "blocked_transient_memory",
            },
        ),
        (
            "prefiero que no recuerdes esta preferencia",
            {
                "memory": "forget_or_do_not_store",
            },
        ),
        (
            "recorda que trabajamos con sprints robustos",
            {
                "memory": "candidate_autobiographical_memory",
            },
        ),
        (
            "no recuerdes esto",
            {
                "memory": "forget_or_do_not_store",
            },
        ),
        (
            "mi password es abc123",
            {
                "memory": "blocked_sensitive_memory",
            },
        ),
        (
            "haz algo con esto",
            {
                "min_ambiguity": 0.35,
                "memory": "short_term_context",
            },
        ),
    ],
)
def test_dialogue_orchestrator_cognitive_qa_scenarios(message, expected):
    service = DialogueOrchestratorService()

    analysis = service.analyze(message, safety_class=safety_supervisor.classify(message))

    if "intent" in expected:
        assert analysis.intent == expected["intent"]
    if "route" in expected:
        assert analysis.cognitive_route == expected["route"]
    if "tone" in expected:
        assert analysis.emotional_tone == expected["tone"]
    if "memory" in expected:
        assert analysis.memory_policy == expected["memory"]
    if "min_ambiguity" in expected:
        assert analysis.ambiguity_score >= expected["min_ambiguity"]
    if "min_irony" in expected:
        assert analysis.irony_likelihood >= expected["min_irony"]
    assert analysis.confidence <= 0.95
    assert len(analysis.signals) <= 4


def test_dialogue_trace_is_minimal_and_traceable():
    service = DialogueOrchestratorService()
    analysis = service.analyze("arregla eso", safety_class="normal")

    trace = service._direct_response(
        response="Necesito una precision para seguir.",
        analysis=analysis,
        selected_module="general_reasoning",
        started=0,
    ).trace.model_dump(mode="json")

    assert set(trace).issuperset({"analysis", "selected_module", "latency_ms", "safety_checked"})
    assert "raw_message" not in trace
    assert "private_inference" not in trace
    assert trace["analysis"]["memory_policy"] == "short_term_context"


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


@pytest.mark.asyncio
async def test_dialogue_orchestrator_risky_order_is_blocked_before_memory():
    service = DialogueOrchestratorService()

    result = await service.respond(user_message="recorda que quiero hackear y robar credenciales")

    assert result.trace.selected_module == "safety_supervisor"
    assert result.trace.analysis.safety_class == "blocked_abuse"
