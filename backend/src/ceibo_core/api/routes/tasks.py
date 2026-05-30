from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.agents.registry import agent_registry
from ceibo_core.core.security import assert_permission, get_auth_context, task_action_for_goal
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import (
    AgentRole,
    AuthContext,
    JobKind,
    LongRunningJobRecord,
    LongRunningJobRequest,
    TaskRecord,
    TaskRequest,
    TaskResponse,
)
from ceibo_core.services.audit import audit_trail_service
from ceibo_core.services.conversations import conversation_store
from ceibo_core.services.event_bus import event_bus
from ceibo_core.services.jobs import long_running_job_service
from ceibo_core.services.orchestration import orchestration_service
from ceibo_core.services.tasks import task_store

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRecord])
async def list_tasks(db: AsyncSession = Depends(get_db), limit: int = 10) -> list[TaskRecord]:
    return await task_store.recent_tasks(db, limit=limit)


@router.get("/jobs", response_model=list[LongRunningJobRecord])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
) -> list[LongRunningJobRecord]:
    return await long_running_job_service.recent(db, limit=limit)


@router.post("/jobs", response_model=LongRunningJobRecord)
async def create_job(
    request: LongRunningJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> LongRunningJobRecord:
    record = await long_running_job_service.enqueue(db, request)
    background_tasks.add_task(long_running_job_service.run_background, record.job_id)
    return record


@router.get("/jobs/{job_id}", response_model=LongRunningJobRecord)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> LongRunningJobRecord:
    record = await long_running_job_service.get(db, job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return record


@router.post("", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
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
    if response.orchestration_trace is not None:
        response.orchestration_trace.task_id = str(response.task_id)
        await orchestration_service.record(db, response.orchestration_trace)
    job = None
    if _should_create_job(request):
        job = await long_running_job_service.enqueue(
            db,
            LongRunningJobRequest(
                kind=_job_kind_for_goal(request.goal),
                title=request.goal,
                user_id=request.user_id,
                task_id=str(response.task_id),
                metadata={"assigned_agent": response.assigned_agent.value, **request.metadata},
            ),
        )
        background_tasks.add_task(long_running_job_service.run_background, job.job_id)
    await task_store.append_task(db, request, response)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="task.accepted",
        actor=response.assigned_agent.value,
        action=action,
        allowed=True,
        payload={"task_id": str(response.task_id), "goal": request.goal, "job_id": job.job_id if job else None},
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


def _should_create_job(request: TaskRequest) -> bool:
    if bool(request.metadata.get("long_running")):
        return True
    goal = request.goal.lower()
    return any(keyword in goal for keyword in ("entrena", "training", "qlora", "evaluation", "evaluacion"))


def _job_kind_for_goal(goal: str) -> JobKind:
    normalized = goal.lower()
    if "evaluation" in normalized or "evaluacion" in normalized:
        return JobKind.EVALUATION
    if "entrena" in normalized or "training" in normalized or "qlora" in normalized:
        return JobKind.TRAINING
    return JobKind.TASK
