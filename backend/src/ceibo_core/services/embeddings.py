import hashlib
import math

import httpx

from ceibo_core.core.config import settings


class EmbeddingService:
    async def embed(self, text: str) -> list[float]:
        provider = settings.embeddings_provider.lower()
        if provider == "openai" and settings.openai_api_key:
            return await self._openai_embedding(text)
        if provider == "ollama":
            return await self._ollama_embedding(text)
        return self._local_embedding(text)

    async def _openai_embedding(self, text: str) -> list[float]:
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        payload = {"model": settings.embedding_model, "input": text}
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return self._resize(self._normalize(data["data"][0]["embedding"]))

    async def _ollama_embedding(self, text: str) -> list[float]:
        payload = {"model": settings.ollama_embedding_model, "prompt": text}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
        return self._resize(self._normalize(data["embedding"]))

    def _local_embedding(self, text: str) -> list[float]:
        dimensions = settings.memory_embedding_dimensions
        vector = [0.0] * dimensions
        tokens = [token.strip().lower() for token in text.split() if token.strip()]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return self._normalize(vector)

    def _resize(self, vector: list[float]) -> list[float]:
        dimensions = settings.memory_embedding_dimensions
        if len(vector) == dimensions:
            return vector
        if len(vector) > dimensions:
            return self._normalize(vector[:dimensions])
        return self._normalize([*vector, *([0.0] * (dimensions - len(vector)))])

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]


embedding_service = EmbeddingService()
