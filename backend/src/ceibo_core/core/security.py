from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.config import settings
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import AuthContext, SecurityAction, SecurityPolicyStatus, UserRole
from ceibo_core.services.audit import audit_trail_service


ROLE_PERMISSIONS: dict[UserRole, set[SecurityAction]] = {
    UserRole.ADMIN: set(SecurityAction),
    UserRole.OPERATOR: {
        SecurityAction.READ_STATUS,
        SecurityAction.RUN_EVALUATION,
        SecurityAction.MANAGE_REGISTRY,
        SecurityAction.START_TRAINING,
        SecurityAction.CREATE_TASK,
        SecurityAction.RUN_INFRA_TASK,
    },
    UserRole.RESEARCHER: {
        SecurityAction.READ_STATUS,
        SecurityAction.RUN_EVALUATION,
        SecurityAction.CREATE_TASK,
    },
    UserRole.VIEWER: {
        SecurityAction.READ_STATUS,
    },
}


async def get_auth_context(
    x_ceibo_user: str | None = Header(default=None),
    x_ceibo_role: str | None = Header(default=None),
) -> AuthContext:
    if x_ceibo_role:
        try:
            role = UserRole(x_ceibo_role.lower())
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid CEIBO role") from exc
        return AuthContext(user_id=x_ceibo_user or "local-user", role=role, local_dev=False)

    if settings.local_dev_admin_enabled and settings.environment != "production":
        return AuthContext(user_id=x_ceibo_user or "local-dev", role=UserRole.ADMIN, local_dev=True)

    if settings.rbac_enforced:
        raise HTTPException(status_code=401, detail="Missing CEIBO role")

    return AuthContext(user_id=x_ceibo_user or "anonymous", role=UserRole.VIEWER, local_dev=False)


def require_permission(action: SecurityAction) -> Callable[[AuthContext], AuthContext]:
    def dependency(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        assert_permission(auth, action)
        return auth

    return dependency


def require_audited_permission(action: SecurityAction, actor: str) -> Callable:
    async def dependency(
        auth: AuthContext = Depends(get_auth_context),
        db: AsyncSession = Depends(get_db),
    ) -> AuthContext:
        try:
            assert_permission(auth, action)
        except HTTPException:
            await audit_trail_service.record(
                db,
                auth=auth,
                event_type="security.denied",
                actor=actor,
                action=action,
                allowed=False,
                payload={"reason": "rbac_denied"},
            )
            raise
        return auth

    return dependency


def assert_permission(auth: AuthContext, action: SecurityAction) -> None:
    allowed = action in ROLE_PERMISSIONS.get(auth.role, set())
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Role {auth.role.value} cannot perform {action.value}",
        )


def task_action_for_goal(goal: str) -> SecurityAction:
    normalized = goal.lower()
    if any(keyword in normalized for keyword in ("system", "sistema", "terminal", "archivo", "proceso", "powershell")):
        return SecurityAction.RUN_SYSTEM_TASK
    if any(keyword in normalized for keyword in ("kubernetes", "docker", "deploy", "cluster", "logs", "helm")):
        return SecurityAction.RUN_INFRA_TASK
    return SecurityAction.CREATE_TASK


def policy_status(auth: AuthContext) -> SecurityPolicyStatus:
    return SecurityPolicyStatus(
        rbac_enforced=settings.rbac_enforced,
        local_dev_admin_enabled=settings.local_dev_admin_enabled,
        effective_user=auth,
        role_permissions={
            role.value: sorted(action.value for action in permissions)
            for role, permissions in ROLE_PERMISSIONS.items()
        },
    )
