from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from qdrant_client import AsyncQdrantClient, models

from ceibo_core.core.config import settings
from ceibo_core.models.schemas import MemoryHealth, MemoryRecord
from ceibo_core.services.embeddings import embedding_service

logger = structlog.get_logger()


class MemoryService:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(url=settings.qdrant_url)
        self._local_memory: dict[str, deque[tuple[MemoryRecord, list[float]]]] = defaultdict(
            lambda: deque(maxlen=settings.memory_local_limit)
        )
        self._collection_ready = False

    async def health(self) -> bool:
        if not settings.memory_vector_enabled:
            return False
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False

    async def status(self) -> MemoryHealth:
        available = await self.health()
        return MemoryHealth(
            backend="qdrant" if settings.memory_vector_enabled and available else "local",
            available=available,
            vector_enabled=settings.memory_vector_enabled,
            embedding_provider=settings.embeddings_provider,
            collection_name=settings.memory_collection_name,
            local_items=sum(len(items) for items in self._local_memory.values()),
        )

    async def remember(
        self,
        session_id: str,
        text: str,
        user_id: str = "local-user",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        embedding = await embedding_service.embed(text)
        record = MemoryRecord(
            memory_id=str(uuid4()),
            session_id=session_id,
            content=text,
            metadata=metadata or {},
            created_at=datetime.now(UTC),
        )
        self._local_memory[session_id].append((record, embedding))

        if settings.memory_vector_enabled:
            await self._upsert_qdrant(record, embedding, user_id=user_id)
        return record

    async def retrieve(self, session_id: str, query: str, limit: int = 4) -> list[MemoryRecord]:
        query_embedding = await embedding_service.embed(query)
        if settings.memory_vector_enabled and await self.health():
            qdrant_matches = await self._retrieve_qdrant(session_id, query_embedding, limit)
            if qdrant_matches:
                return qdrant_matches
        return self._retrieve_local(session_id, query_embedding, limit)

    async def _ensure_collection(self) -> None:
        if self._collection_ready:
            return
        exists = await self.client.collection_exists(settings.memory_collection_name)
        if not exists:
            await self.client.create_collection(
                collection_name=settings.memory_collection_name,
                vectors_config=models.VectorParams(
                    size=settings.memory_embedding_dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
        self._collection_ready = True

    async def _upsert_qdrant(
        self,
        record: MemoryRecord,
        embedding: list[float],
        user_id: str,
    ) -> None:
        try:
            await self._ensure_collection()
            await self.client.upsert(
                collection_name=settings.memory_collection_name,
                points=[
                    models.PointStruct(
                        id=record.memory_id,
                        vector=embedding,
                        payload={
                            "session_id": record.session_id,
                            "content": record.content,
                            "user_id": user_id,
                            "metadata": record.metadata,
                            "created_at": record.created_at.isoformat(),
                        },
                    )
                ],
            )
        except Exception as exc:  # pragma: no cover - local dev often runs without Qdrant
            logger.warning("memory_qdrant_upsert_failed", error=str(exc))

    async def _retrieve_qdrant(
        self,
        session_id: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[MemoryRecord]:
        try:
            result = await self.client.query_points(
                collection_name=settings.memory_collection_name,
                query=query_embedding,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="session_id",
                            match=models.MatchValue(value=session_id),
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
            )
            points = getattr(result, "points", result)
            records: list[MemoryRecord] = []
            for point in points:
                payload = point.payload or {}
                records.append(
                    MemoryRecord(
                        memory_id=str(point.id),
                        session_id=str(payload.get("session_id", session_id)),
                        content=str(payload.get("content", "")),
                        score=float(point.score) if point.score is not None else None,
                        metadata=dict(payload.get("metadata") or {}),
                    )
                )
            return records
        except Exception as exc:  # pragma: no cover - local dev often runs without Qdrant
            logger.warning("memory_qdrant_search_failed", error=str(exc))
            return []

    def _retrieve_local(
        self,
        session_id: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[MemoryRecord]:
        scored: list[MemoryRecord] = []
        for record, embedding in self._local_memory[session_id]:
            score = self._cosine(query_embedding, embedding)
            if score > 0:
                scored.append(record.model_copy(update={"score": score}))
        scored.sort(key=lambda item: item.score or 0, reverse=True)
        return scored[:limit]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=False))


memory_service = MemoryService()
