from collections import deque
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.config import settings
from ceibo_core.db.models import AgentTask
from ceibo_core.models.schemas import AgentRole, TaskRecord, TaskRequest, TaskResponse, TaskStatus

logger = structlog.get_logger()


class TaskStore:
    def __init__(self) -> None:
        self._fallback_tasks: deque[TaskRecord] = deque(maxlen=80)

    async def append_task(
        self,
        db: AsyncSession,
        request: TaskRequest,
        response: TaskResponse,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = TaskRecord(
            task_id=str(response.task_id),
            goal=request.goal,
            status=response.status,
            assigned_agent=response.assigned_agent,
            priority=request.priority,
            created_at=response.created_at,
        )
        self._fallback_tasks.appendleft(record)
        if not settings.persistence_enabled:
            return
        try:
            db.add(
                AgentTask(
                    id=str(response.task_id),
                    user_id=request.user_id,
                    goal=request.goal,
                    assigned_agent=response.assigned_agent.value,
                    status=response.status.value,
                    priority=request.priority,
                    task_metadata=metadata or request.metadata,
                )
            )
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("task_append_failed", error=str(exc))

    async def recent_tasks(self, db: AsyncSession, limit: int = 10) -> list[TaskRecord]:
        if not settings.persistence_enabled:
            return list(self._fallback_tasks)[:limit]
        try:
            result = await db.execute(
                select(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit)
            )
            tasks = result.scalars().all()
            return [
                TaskRecord(
                    task_id=task.id,
                    goal=task.goal,
                    status=TaskStatus(task.status),
                    assigned_agent=AgentRole(task.assigned_agent),
                    priority=task.priority,
                    created_at=task.created_at,
                )
                for task in tasks
            ]
        except SQLAlchemyError as exc:
            logger.warning("task_list_failed", error=str(exc))
            return list(self._fallback_tasks)[:limit]


task_store = TaskStore()
