from collections import deque

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.config import settings
from ceibo_core.db.models import OrchestrationTrace
from ceibo_core.models.schemas import (
    AgentRole,
    OrchestrationStep,
    OrchestrationTraceRecord,
    TaskRequest,
)

logger = structlog.get_logger()


class OrchestrationService:
    def __init__(self) -> None:
        self._fallback_traces: deque[OrchestrationTraceRecord] = deque(maxlen=120)
        self._keyword_map: dict[AgentRole, tuple[str, ...]] = {
            AgentRole.INFRASTRUCTURE: ("kubernetes", "docker", "deploy", "logs", "cluster"),
            AgentRole.CYBERSECURITY: (
                "security",
                "seguridad",
                "hardening",
                "siem",
                "anomalia",
                "auditoria",
            ),
            AgentRole.RESEARCH: ("investiga", "resume", "busca", "research", "documenta"),
            AgentRole.AUTOMATION: ("automatiza", "script", "workflow", "playwright", "selenium"),
            AgentRole.MEMORY: ("memoria", "rag", "embedding", "recordar", "knowledge"),
            AgentRole.VOICE: ("voz", "whisper", "tts", "wake"),
            AgentRole.SYSTEM_CONTROL: (
                "archivo",
                "terminal",
                "proceso",
                "sistema operativo",
            ),
        }

    def plan(self, request: TaskRequest) -> OrchestrationTraceRecord:
        scores = self._score_goal(request.goal)
        if request.requested_agent:
            primary = request.requested_agent
            reason = f"agente solicitado explicitamente: {primary.value}"
        elif scores:
            primary = max(scores.items(), key=lambda item: item[1])[0]
            reason = f"mejor match por keywords: {primary.value} ({scores[primary]})"
        else:
            primary = AgentRole.CORE_ORCHESTRATOR
            reason = "sin match especializado; queda en planificacion central"

        support_agents = [
            role
            for role, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
            if role != primary and score > 0
        ][:3]
        steps = [
            OrchestrationStep(
                agent=AgentRole.CORE_ORCHESTRATOR,
                action="triage",
                reason="normaliza la meta, calcula afinidad y decide ruta",
                status="completed",
            ),
            OrchestrationStep(
                agent=primary,
                action="execute",
                reason=reason,
                status="planned",
            ),
        ]
        steps.extend(
            OrchestrationStep(
                agent=role,
                action="support",
                reason=f"handoff contextual por afinidad secundaria ({scores[role]})",
                status="planned",
            )
            for role in support_agents
        )
        return OrchestrationTraceRecord(
            user_id=request.user_id,
            goal=request.goal,
            primary_agent=primary,
            route_reason=reason,
            steps=steps,
        )

    async def record(
        self,
        db: AsyncSession | None,
        trace: OrchestrationTraceRecord,
    ) -> OrchestrationTraceRecord:
        self._fallback_traces.appendleft(trace)
        if not settings.persistence_enabled or db is None:
            return trace
        try:
            db.add(
                OrchestrationTrace(
                    id=trace.trace_id,
                    task_id=trace.task_id,
                    user_id=trace.user_id,
                    goal=trace.goal,
                    primary_agent=trace.primary_agent.value,
                    route_reason=trace.route_reason,
                    steps=[step.model_dump(mode="json") for step in trace.steps],
                    created_at=trace.created_at,
                )
            )
            await db.commit()
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.warning("orchestration_trace_record_failed", error=str(exc))
        return trace

    async def recent(
        self,
        db: AsyncSession | None,
        limit: int = 10,
    ) -> list[OrchestrationTraceRecord]:
        if settings.persistence_enabled and db is not None:
            try:
                result = await db.execute(
                    select(OrchestrationTrace)
                    .order_by(OrchestrationTrace.created_at.desc())
                    .limit(limit)
                )
                return [self._from_record(record) for record in result.scalars().all()]
            except SQLAlchemyError as exc:
                logger.warning("orchestration_trace_list_failed", error=str(exc))
        return list(self._fallback_traces)[:limit]

    def _score_goal(self, goal: str) -> dict[AgentRole, int]:
        normalized = goal.lower()
        scores: dict[AgentRole, int] = {}
        for role, keywords in self._keyword_map.items():
            score = sum(1 for keyword in keywords if keyword in normalized)
            if score:
                scores[role] = score
        return scores

    def _from_record(self, record: OrchestrationTrace) -> OrchestrationTraceRecord:
        return OrchestrationTraceRecord(
            trace_id=record.id,
            task_id=record.task_id,
            user_id=record.user_id,
            goal=record.goal,
            primary_agent=AgentRole(record.primary_agent),
            route_reason=record.route_reason,
            steps=[OrchestrationStep(**step) for step in record.steps],
            created_at=record.created_at,
        )


orchestration_service = OrchestrationService()
