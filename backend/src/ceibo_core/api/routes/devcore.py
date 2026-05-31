from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.security import get_auth_context, require_audited_permission
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import (
    AuthContext,
    DevCoreCapabilityPromotionDecision,
    DevCoreCapabilityPromotionRequest,
    DevCoreCapabilityRecord,
    DevCoreExecutionRequest,
    DevCoreExecutionResponse,
    DevCorePatchApplyRequest,
    DevCorePatchApplyResponse,
    DevCoreParseRequest,
    DevCoreParseResponse,
    DevCorePatchPlannerRequest,
    DevCorePatchPlannerResponse,
    DevCorePatchProposeRequest,
    DevCorePatchProposeResponse,
    DevCorePlanRequest,
    DevCorePlanResponse,
    DevCoreSafetyPolicy,
    DevCoreStatus,
    DevCoreTemplateRecord,
    DevCoreTemplateRenderRequest,
    DevCoreTemplateRenderResponse,
    KnowledgeItemRequest,
    SecurityAction,
)
from ceibo_core.services.audit import audit_trail_service
from ceibo_core.services.devcore import devcore_service
from ceibo_core.services.devcore_execution import devcore_execution_sandbox
from ceibo_core.services.devcore_patch_apply import devcore_patch_apply_gate
from ceibo_core.services.devcore_patch_planner import devcore_patch_planner
from ceibo_core.services.devcore_patch_proposer import devcore_patch_proposer
from ceibo_core.services.devcore_safety import devcore_safety_layer
from ceibo_core.services.devcore_templates import devcore_template_engine
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


@router.get("/safety/policy", response_model=DevCoreSafetyPolicy)
async def devcore_safety_policy(
    auth: AuthContext = Depends(get_auth_context),
) -> DevCoreSafetyPolicy:
    return devcore_safety_layer.policy()


@router.get("/templates", response_model=list[DevCoreTemplateRecord])
async def devcore_templates(
    auth: AuthContext = Depends(get_auth_context),
) -> list[DevCoreTemplateRecord]:
    return devcore_template_engine.list_templates()


@router.post("/templates/render", response_model=DevCoreTemplateRenderResponse)
async def render_devcore_template(
    request: DevCoreTemplateRenderRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(
        require_audited_permission(SecurityAction.RUN_DEVCORE_PLAN, "ceibo_devcore")
    ),
) -> DevCoreTemplateRenderResponse:
    response = devcore_template_engine.render(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="devcore.template_render",
        actor="ceibo_devcore",
        action=SecurityAction.RUN_DEVCORE_PLAN,
        allowed=not any(issue.severity == "error" for issue in response.validation_issues),
        payload={
            "render_id": response.render_id,
            "template_id": response.template_id,
            "language": response.language,
            "safe_to_execute": response.safe_to_execute,
            "requires_review": response.requires_review,
        },
    )
    return response


@router.post("/execute", response_model=DevCoreExecutionResponse)
async def execute_devcore_sandbox(
    request: DevCoreExecutionRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(
        require_audited_permission(SecurityAction.RUN_DEVCORE_PLAN, "ceibo_devcore")
    ),
) -> DevCoreExecutionResponse:
    response = devcore_execution_sandbox.run(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="devcore.sandbox_execution",
        actor="ceibo_devcore",
        action=SecurityAction.RUN_DEVCORE_PLAN,
        allowed=response.status in {"completed", "failed"},
        payload={
            "execution_id": response.execution_id,
            "status": response.status,
            "command": response.command,
            "working_directory": response.working_directory,
            "risk_level": response.risk_level,
            "cyber_category": response.cyber_category,
            "policy_action": response.policy_action,
        },
    )
    return response


@router.post("/patch-plan", response_model=DevCorePatchPlannerResponse)
async def plan_devcore_patch(
    request: DevCorePatchPlannerRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(
        require_audited_permission(SecurityAction.RUN_DEVCORE_PLAN, "ceibo_devcore")
    ),
) -> DevCorePatchPlannerResponse:
    response = devcore_patch_planner.plan(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="devcore.patch_plan",
        actor="ceibo_devcore",
        action=SecurityAction.RUN_DEVCORE_PLAN,
        allowed=response.policy_action != "block",
        payload={
            "patch_plan_id": response.patch_plan_id,
            "goal": response.goal,
            "intent": response.intent,
            "risk_level": response.risk_level,
            "policy_action": response.policy_action,
            "applies_changes": response.applies_changes,
        },
    )
    return response


@router.post("/patch-apply", response_model=DevCorePatchApplyResponse)
async def apply_devcore_patch(
    request: DevCorePatchApplyRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(
        require_audited_permission(SecurityAction.RUN_DEVCORE_PLAN, "ceibo_devcore")
    ),
) -> DevCorePatchApplyResponse:
    response = devcore_patch_apply_gate.apply(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="devcore.patch_apply",
        actor="ceibo_devcore",
        action=SecurityAction.RUN_DEVCORE_PLAN,
        allowed=response.status == "applied",
        payload={
            "apply_id": response.apply_id,
            "patch_plan_id": response.patch_plan_id,
            "status": response.status,
            "applied_files": response.applied_files,
            "applies_changes": response.applies_changes,
        },
    )
    return response


@router.post("/patch-propose", response_model=DevCorePatchProposeResponse)
async def propose_devcore_patch(
    request: DevCorePatchProposeRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(
        require_audited_permission(SecurityAction.RUN_DEVCORE_PLAN, "ceibo_devcore")
    ),
) -> DevCorePatchProposeResponse:
    response = devcore_patch_proposer.propose(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="devcore.patch_propose",
        actor="ceibo_devcore",
        action=SecurityAction.RUN_DEVCORE_PLAN,
        allowed=not any(issue.severity == "error" for issue in response.validation_issues),
        payload={
            "proposal_id": response.proposal_id,
            "patch_plan_id": response.patch_plan_id,
            "change_count": len(response.proposed_changes),
            "applies_changes": response.applies_changes,
        },
    )
    return response


@router.post("/parse", response_model=DevCoreParseResponse)
async def parse_devcore_language(
    request: DevCoreParseRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> DevCoreParseResponse:
    response = devcore_service.parse(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="devcore.parse",
        actor="ceibo_devcore",
        action=SecurityAction.READ_STATUS,
        allowed=response.risk_level != "blocked",
        payload={
            "parse_id": response.parse_id,
            "intent": response.intent,
            "risk_level": response.risk_level,
            "requires_confirmation": response.requires_confirmation,
        },
    )
    return response


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
