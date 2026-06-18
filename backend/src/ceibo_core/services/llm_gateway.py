from __future__ import annotations

import re
import httpx
from typing import List

from ceibo_core.core.config import settings
from ceibo_core.security.ollama_guard import validate_ollama_base_url, UnsafeOllamaHostError
from ceibo_core.ai_engine import ceibo_engine


class LLMGateway:
    """Model-agnostic local gateway for chat-style calls.

    Supports providers: "ollama" and "ceibo_local".
    """

    async def chat(self, messages: List[dict], temperature: float = 0.7, max_tokens: int | None = None) -> str:
        provider = settings.default_llm_provider or "ollama"
        if provider == "ceibo_local":
            # Build a simple system + last user message for the local engine
            system_prompt = "\n".join([m["content"] for m in messages if m.get("role") == "system"]) if messages else ""
            last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
            try:
                result = await ceibo_engine.generate(system_prompt=system_prompt, user_message=last_user, context=[m.get("content") for m in messages if m.get("role") == "assistant"])
                return result.response if hasattr(result, "response") else str(result)
            except Exception:
                return "CEIBO local engine falló al generar respuesta. Por favor revisá el estado del motor local."

        if provider == "ollama":
            base = settings.ollama_base_url or "http://127.0.0.1:11434"
            # Validate host safety
            try:
                if settings.block_non_local_ollama:
                    validate_ollama_base_url(base)
            except UnsafeOllamaHostError as exc:  # translate into friendly message
                return str(exc)

            payload = {
                "model": settings.ollama_chat_model or "qwen3:8b",
                "messages": messages,
                "stream": False,
                "think": bool(settings.ollama_think),
                "options": {"temperature": float(temperature)},
            }
            if settings.ollama_hide_thinking:
                payload["hide_thinking"] = True
            if max_tokens is not None:
                payload["max_tokens"] = int(max_tokens)

            timeout = settings.ollama_timeout_seconds or 300
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(f"{base.rstrip('/')}/api/chat", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.ConnectError:
                return "Ollama no parece estar corriendo en localhost. Verificá que Ollama esté instalado y en ejecución."
            except (httpx.ReadTimeout, httpx.TimeoutException):
                return "Tiempo de espera agotado al comunicarse con Ollama."
            except httpx.HTTPError as exc:
                return f"Error al comunicarse con Ollama: {str(exc)}"

            # Expect data to contain {'response': '...'} or model specific
            if isinstance(data, dict):
                if "response" in data and data["response"]:
                    return self._sanitize_ollama_response(data["response"])
                if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
                    choice = data["choices"][0]
                    if isinstance(choice, dict) and "message" in choice:
                        return self._sanitize_ollama_response(choice["message"].get("content", ""))
            return "Ollama respondió sin contenido útil. Revisá que el modelo esté descargado y funcionando."

        # Fallback
        return "No hay un proveedor de LLM válido configurado."

    def _sanitize_ollama_response(self, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"\s*\[\s*thinking.*?\]\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\s*\(\s*thinking.*?\)\s*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        return cleaned.strip()


llm_gateway = LLMGateway()
