from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.agents.registry import agent_registry
from ceibo_core.core.security import assert_permission, get_auth_context, task_action_for_goal
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import AgentRole, AuthContext, TaskRecord, TaskRequest, TaskResponse
from ceibo_core.services.audit import audit_trail_service
from ceibo_core.services.conversations import conversation_store
from ceibo_core.services.event_bus import event_bus
from ceibo_core.services.tasks import task_store

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRecord])
async def list_tasks(db: AsyncSession = Depends(get_db), limit: int = 10) -> list[TaskRecord]:
    return await task_store.recent_tasks(db, limit=limit)


@router.post("", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> TaskResponse:
    action = task_action_for_goal(request.goal)
    try:
        assert_permission(auth, action)
    except HTTPException:
        await audit_trail_service.record(
            db,
            auth=auth,
            event_type="task.denied",
            actor="core_orchestrator",
            action=action,
            allowed=False,
            payload={"goal": request.goal},
        )
        raise
    orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]
    response = await orchestrator.handle_task(request)
    await task_store.append_task(db, request, response)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="task.accepted",
        actor=response.assigned_agent.value,
        action=action,
        allowed=True,
        payload={"task_id": str(response.task_id), "goal": request.goal},
    )
    await conversation_store.audit(
        db,
        user_id=request.user_id,
        event_type="task.accepted",
        actor=response.assigned_agent.value,
        payload={"task_id": str(response.task_id), "goal": request.goal},
    )
    await event_bus.publish("ceibo.task.accepted", response.model_dump_json().encode())
    return response
