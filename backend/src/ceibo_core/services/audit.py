from collections import deque
from datetime import UTC, datetime
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.config import settings
from ceibo_core.db.models import AuditEvent
from ceibo_core.models.schemas import AuditEventRecord, AuthContext, SecurityAction, UserRole

logger = structlog.get_logger()


class AuditTrailService:
    def __init__(self) -> None:
        self._fallback_events: deque[AuditEventRecord] = deque(maxlen=300)

    async def record(
        self,
        db: AsyncSession | None,
        *,
        auth: AuthContext,
        event_type: str,
        actor: str,
        action: SecurityAction | None = None,
        allowed: bool | None = None,
        payload: dict | None = None,
    ) -> AuditEventRecord:
        event = AuditEventRecord(
            event_id=str(uuid4()),
            user_id=auth.user_id,
            role=auth.role,
            event_type=event_type,
            actor=actor,
            action=action,
            allowed=allowed,
            payload=payload or {},
            created_at=datetime.now(UTC),
        )
        self._fallback_events.appendleft(event)

        if not settings.persistence_enabled or db is None:
            return event

        try:
            db.add(
                AuditEvent(
                    id=event.event_id,
                    user_id=event.user_id,
                    event_type=event.event_type,
                    actor=event.actor,
                    payload={
                        **event.payload,
                        "role": event.role.value if event.role else None,
                        "action": event.action.value if event.action else None,
                        "allowed": event.allowed,
                    },
                    created_at=event.created_at,
                )
            )
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("audit_trail_record_failed", error=str(exc))
        return event

    async def recent(
        self,
        db: AsyncSession | None,
        limit: int = 50,
    ) -> list[AuditEventRecord]:
        if not settings.persistence_enabled or db is None:
            return list(self._fallback_events)[:limit]
        try:
            result = await db.execute(
                select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
            )
            return [self._from_record(record) for record in result.scalars().all()]
        except SQLAlchemyError as exc:
            logger.warning("audit_trail_recent_failed", error=str(exc))
            return list(self._fallback_events)[:limit]

    def _from_record(self, record: AuditEvent) -> AuditEventRecord:
        payload = dict(record.payload or {})
        role = payload.pop("role", None)
        action = payload.pop("action", None)
        allowed = payload.pop("allowed", None)
        return AuditEventRecord(
            event_id=record.id,
            user_id=record.user_id,
            role=UserRole(role) if role else None,
            event_type=record.event_type,
            actor=record.actor,
            action=SecurityAction(action) if action else None,
            allowed=allowed,
            payload=payload,
            created_at=record.created_at,
        )


audit_trail_service = AuditTrailService()
