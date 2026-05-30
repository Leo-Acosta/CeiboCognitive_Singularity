import httpx

from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.core.config import settings


class LLMGateway:
    async def generate(self, system_prompt: str, user_message: str) -> str:
        if settings.default_llm_provider == "ceibo_local":
            result = await ceibo_engine.generate(
                system_prompt=system_prompt,
                user_message=user_message,
            )
            return result.response
        if settings.default_llm_provider == "ollama":
            return await self._ollama_generate(system_prompt, user_message)
        if settings.openai_api_key:
            return await self._openai_generate(system_prompt, user_message)
        return (
            "CEIBO CORE esta inicializado con motor local. Mensaje recibido: "
            f"{user_message}"
        )

    async def _openai_generate(self, system_prompt: str, user_message: str) -> str:
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _ollama_generate(self, system_prompt: str, user_message: str) -> str:
        payload = {
            "model": "llama3.1",
            "prompt": f"{system_prompt}\n\nUsuario: {user_message}\nCEIBO:",
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("response", "")


llm_gateway = LLMGateway()
