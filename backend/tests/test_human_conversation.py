import pytest

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
