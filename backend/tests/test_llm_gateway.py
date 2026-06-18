import asyncio

import pytest

from ceibo_core.services.llm_gateway import llm_gateway
from ceibo_core.core.config import settings


@pytest.mark.asyncio
async def test_llm_gateway_handles_ollama_down(monkeypatch):
    settings.default_llm_provider = "ollama"
    settings.ollama_base_url = "http://127.0.0.1:59999"
    resp = await llm_gateway.chat(messages=[{"role": "user", "content": "hola"}])
    assert isinstance(resp, str)
    assert "Ollama" in resp or "no parece" in resp or "Tiempo" in resp


@pytest.mark.asyncio
async def test_llm_gateway_sends_ollama_chat_payload(monkeypatch):
    settings.default_llm_provider = "ollama"
    settings.ollama_base_url = "http://127.0.0.1:11434"
    settings.ollama_chat_model = "qwen3:8b"
    settings.ollama_think = False
    settings.ollama_hide_thinking = True
    settings.ollama_timeout_seconds = 300

    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "Hola!"}

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return DummyResponse()

    monkeypatch.setattr("ceibo_core.services.llm_gateway.httpx.AsyncClient", DummyAsyncClient)

    resp = await llm_gateway.chat(messages=[{"role": "user", "content": "hola"}], temperature=0.7)
    assert resp == "Hola!"
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["json"]["model"] == "qwen3:8b"
    assert captured["json"]["stream"] is False
    assert captured["json"]["think"] is False
    assert captured["json"]["hide_thinking"] is True
    assert captured["json"]["options"]["temperature"] == 0.7
