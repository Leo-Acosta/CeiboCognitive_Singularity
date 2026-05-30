from collections import defaultdict, deque
from datetime import UTC, datetime
import re
from typing import Any
from uuid import uuid4

import structlog
from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.config import settings
from ceibo_core.db.models import KnowledgeItem
from ceibo_core.models.schemas import (
    KnowledgeItemRecord,
    KnowledgeItemRequest,
    KnowledgeStatus,
    MemoryHealth,
    MemoryRecord,
)
from ceibo_core.services.embeddings import embedding_service

logger = structlog.get_logger()


SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|jwt)\s*[:=]\s*['\"]?[\w.\-+/=]{8,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{16,}"),
)


def sanitize_memory_text(text: str) -> tuple[str, bool]:
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized, sanitized != text


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
        safe_text, redacted = sanitize_memory_text(text)
        safe_metadata = {**(metadata or {})}
        if redacted:
            safe_metadata["redacted"] = True
        embedding = await embedding_service.embed(safe_text)
        record = MemoryRecord(
            memory_id=str(uuid4()),
            session_id=session_id,
            content=safe_text,
            metadata=safe_metadata,
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


class KnowledgeService:
    def __init__(self) -> None:
        self._fallback_items: deque[KnowledgeItemRecord] = deque(maxlen=settings.memory_local_limit)
        self._sanitized_items = 0

    async def status(self, db: AsyncSession | None = None) -> KnowledgeStatus:
        total_items = len(self._fallback_items)
        backend = "local"
        if settings.persistence_enabled and db is not None:
            backend = "postgres"
            try:
                result = await db.execute(select(KnowledgeItem))
                total_items = len(result.scalars().all())
            except SQLAlchemyError as exc:
                logger.warning("knowledge_status_failed", error=str(exc))
                backend = "local"
        return KnowledgeStatus(
            backend=backend,
            total_items=total_items,
            sanitized_items=self._sanitized_items,
            safety_filters=["credential-redaction", "api-key-redaction", "token-redaction"],
        )

    async def add(
        self,
        db: AsyncSession | None,
        request: KnowledgeItemRequest,
    ) -> KnowledgeItemRecord:
        content, redacted_content = sanitize_memory_text(request.content)
        title, redacted_title = sanitize_memory_text(request.title)
        metadata = {**request.metadata}
        if redacted_content or redacted_title:
            metadata["redacted"] = True
            self._sanitized_items += 1
        record = KnowledgeItemRecord(
            item_id=str(uuid4()),
            title=title,
            content=content,
            source=request.source,
            user_id=request.user_id,
            tags=request.tags,
            metadata=metadata,
            created_at=datetime.now(UTC),
        )
        self._fallback_items.appendleft(record)
        await memory_service.remember(
            session_id="knowledge-base",
            text=f"{record.title}\n{record.content}",
            user_id=record.user_id,
            metadata={"kind": "knowledge", "source": record.source, "tags": record.tags},
        )
        if not settings.persistence_enabled or db is None:
            return record
        try:
            db.add(
                KnowledgeItem(
                    id=record.item_id,
                    user_id=record.user_id,
                    title=record.title,
                    content=record.content,
                    source=record.source,
                    tags=record.tags,
                    item_metadata=record.metadata,
                    created_at=record.created_at,
                )
            )
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("knowledge_add_failed", error=str(exc))
        return record

    async def list_recent(
        self,
        db: AsyncSession | None,
        limit: int = 10,
    ) -> list[KnowledgeItemRecord]:
        if settings.persistence_enabled and db is not None:
            try:
                result = await db.execute(
                    select(KnowledgeItem).order_by(KnowledgeItem.created_at.desc()).limit(limit)
                )
                return [self._from_record(item) for item in result.scalars().all()]
            except SQLAlchemyError as exc:
                logger.warning("knowledge_list_failed", error=str(exc))
        return list(self._fallback_items)[:limit]

    async def search(
        self,
        db: AsyncSession | None,
        query: str,
        limit: int = 5,
    ) -> list[KnowledgeItemRecord]:
        normalized = query.lower()
        if settings.persistence_enabled and db is not None:
            try:
                result = await db.execute(
                    select(KnowledgeItem)
                    .where(or_(KnowledgeItem.title.ilike(f"%{query}%"), KnowledgeItem.content.ilike(f"%{query}%")))
                    .order_by(KnowledgeItem.created_at.desc())
                    .limit(limit)
                )
                return [self._from_record(item) for item in result.scalars().all()]
            except SQLAlchemyError as exc:
                logger.warning("knowledge_search_failed", error=str(exc))
        matches = [
            item
            for item in self._fallback_items
            if normalized in item.title.lower()
            or normalized in item.content.lower()
            or any(normalized in tag.lower() for tag in item.tags)
        ]
        return matches[:limit]

    def _from_record(self, record: KnowledgeItem) -> KnowledgeItemRecord:
        return KnowledgeItemRecord(
            item_id=record.id,
            title=record.title,
            content=record.content,
            source=record.source,
            user_id=record.user_id,
            tags=list(record.tags or []),
            metadata=dict(record.item_metadata or {}),
            created_at=record.created_at,
        )


knowledge_service = KnowledgeService()
