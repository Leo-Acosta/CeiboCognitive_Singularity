from collections import defaultdict, deque
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.config import settings
from ceibo_core.db.models import AuditEvent, ChatMessage, Conversation

logger = structlog.get_logger()


class ConversationStore:
    def __init__(self) -> None:
        self._fallback_messages: dict[str, deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=40))

    async def recent_messages(
        self,
        db: AsyncSession,
        session_id: str,
        limit: int = 8,
    ) -> list[str]:
        if not settings.persistence_enabled:
            return [
                f"{message['role']}: {message['content']}"
                for message in self._fallback_messages[session_id]
            ][-limit:]
        try:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            messages = list(reversed(result.scalars().all()))
            return [f"{message.role}: {message.content}" for message in messages]
        except SQLAlchemyError as exc:
            logger.warning("conversation_recent_messages_failed", error=str(exc))
            return [
                f"{message['role']}: {message['content']}"
                for message in self._fallback_messages[session_id]
            ][-limit:]

    async def append_message(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._fallback_messages[session_id].append({"role": role, "content": content})
        if not settings.persistence_enabled:
            return
        try:
            conversation = await db.get(Conversation, session_id)
            if conversation is None:
                conversation = Conversation(
                    id=session_id,
                    user_id=user_id,
                    title=content[:120] if role == "user" else None,
                )
                db.add(conversation)
            db.add(
                ChatMessage(
                    conversation_id=session_id,
                    user_id=user_id,
                    role=role,
                    content=content,
                    agent=agent,
                    message_metadata=metadata or {},
                )
            )
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("conversation_append_failed", error=str(exc))

    async def audit(
        self,
        db: AsyncSession,
        user_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
    ) -> None:
        if not settings.persistence_enabled:
            return
        try:
            db.add(AuditEvent(user_id=user_id, event_type=event_type, actor=actor, payload=payload))
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("audit_event_failed", error=str(exc))


conversation_store = ConversationStore()
