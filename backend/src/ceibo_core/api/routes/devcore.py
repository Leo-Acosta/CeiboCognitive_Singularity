from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.security import get_auth_context, require_audited_permission
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import (
    AuthContext,
    DevCoreCapabilityPromotionDecision,
    DevCoreCapabilityPromotionRequest,
    DevCoreCapabilityRecord,
    DevCorePlanRequest,
    DevCorePlanResponse,
    DevCoreStatus,
    KnowledgeItemRequest,
    SecurityAction,
)
from ceibo_core.services.audit import audit_trail_service
from ceibo_core.services.devcore import devcore_service
from ceibo_core.services.memory import knowledge_service

router = APIRouter(prefix="/devcore", tags=["devcore"])


@router.get("/status", response_model=DevCoreStatus)
async def devcore_status(auth: AuthContext = Depends(get_auth_context)) -> DevCoreStatus:
    return devcore_service.status()


@router.get("/capabilities", response_model=list[DevCoreCapabilityRecord])
async def devcore_capabilities(
    auth: AuthContext = Depends(get_auth_context),
) -> list[DevCoreCapabilityRecord]:
    return devcore_service.capabilities_overview()


@router.post("/capabilities/promote", response_model=DevCoreCapabilityPromotionDecision)
async def promote_devcore_capability(
    request: DevCoreCapabilityPromotionRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(
        require_audited_permission(SecurityAction.RUN_DEVCORE_PLAN, "ceibo_devcore")
    ),
) -> DevCoreCapabilityPromotionDecision:
    decision = devcore_service.promote_capability(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="devcore.capability_promotion",
        actor="ceibo_devcore",
        action=SecurityAction.RUN_DEVCORE_PLAN,
        allowed=decision.approved,
        payload={
            "capability_id": request.capability_id,
            "approved": decision.approved,
            "checks": [check.model_dump(mode="json") for check in decision.checks],
        },
    )
    return decision


@router.post("/plan", response_model=DevCorePlanResponse)
async def plan_devcore_change(
    request: DevCorePlanRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(
        require_audited_permission(SecurityAction.RUN_DEVCORE_PLAN, "ceibo_devcore")
    ),
) -> DevCorePlanResponse:
    response = devcore_service.plan(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="devcore.plan",
        actor="ceibo_devcore",
        action=SecurityAction.RUN_DEVCORE_PLAN,
        allowed=True,
        payload={
            "plan_id": response.plan_id,
            "goal": request.goal,
            "recommended_agent": response.recommended_agent.value,
        },
    )
    await knowledge_service.add(
        db,
        KnowledgeItemRequest(
            title=f"DevCore plan: {request.goal[:80]}",
            content=response.model_dump_json(),
            source="devcore",
            user_id=auth.user_id,
            tags=["devcore", "plan", response.recommended_agent.value],
            metadata={"plan_id": response.plan_id},
        ),
    )
    return response
