from pathlib import Path

from ceibo_core.models.schemas import (
    AgentRole,
    DevCoreCapabilityPromotionDecision,
    DevCoreCapabilityPromotionRequest,
    DevCoreCapabilityRecord,
    DevCoreCapabilityStatus,
    DevCorePlanRequest,
    DevCorePlanResponse,
    DevCorePlanStep,
    DevCoreStatus,
    PromotionGateCheck,
)


class DevCoreService:
    capabilities = [
        "repo-inspection",
        "change-planning",
        "test-routing",
        "release-readiness",
        "safe-local-automation",
    ]

    def __init__(self) -> None:
        self._repo_root = Path(__file__).resolve().parents[4]
        self._capabilities: dict[str, DevCoreCapabilityRecord] = {
            "repo-inspection": DevCoreCapabilityRecord(
                capability_id="repo-inspection",
                name="Repo Inspection",
                description="Inspecciona estructura local del repositorio en modo solo lectura.",
                safety_score=95,
            ),
            "change-planning": DevCoreCapabilityRecord(
                capability_id="change-planning",
                name="Change Planning",
                description="Genera planes de cambio con pasos, targets y verificaciones.",
                safety_score=90,
            ),
            "test-routing": DevCoreCapabilityRecord(
                capability_id="test-routing",
                name="Test Routing",
                description="Recomienda checks segun el tipo de cambio solicitado.",
                safety_score=85,
            ),
            "safe-local-automation": DevCoreCapabilityRecord(
                capability_id="safe-local-automation",
                name="Safe Local Automation",
                description="Prepara automatizacion local bajo gates de seguridad.",
                safety_score=70,
            ),
        }

    def status(self) -> DevCoreStatus:
        indexed_files = sum(1 for path in self._repo_root.rglob("*") if path.is_file() and ".git" not in path.parts)
        return DevCoreStatus(
            capabilities=self.capabilities,
            active_capabilities=sum(
                1 for capability in self._capabilities.values() if capability.status == DevCoreCapabilityStatus.ACTIVE
            ),
            repo_root=str(self._repo_root),
            indexed_files=indexed_files,
            writable=False,
        )

    def capabilities_overview(self) -> list[DevCoreCapabilityRecord]:
        return list(self._capabilities.values())

    def metrics(self) -> dict[str, int]:
        records = self.capabilities_overview()
        active = sum(1 for capability in records if capability.status == DevCoreCapabilityStatus.ACTIVE)
        approved = sum(1 for capability in records if capability.status == DevCoreCapabilityStatus.APPROVED)
        average_safety = round(sum(capability.safety_score for capability in records) / len(records))
        return {
            "total": len(records),
            "active": active,
            "approved": approved,
            "average_safety": average_safety,
        }

    def promote_capability(
        self,
        request: DevCoreCapabilityPromotionRequest,
    ) -> DevCoreCapabilityPromotionDecision:
        capability = self._capabilities.get(request.capability_id)
        latest_eval = None
        if request.require_evaluation:
            from ceibo_core.services.evaluation_harness import evaluation_harness_service

            latest_eval = evaluation_harness_service.latest()
        checks = [
            PromotionGateCheck(
                name="capability_exists",
                passed=capability is not None,
                detail=request.capability_id,
            ),
            PromotionGateCheck(
                name="human_approval",
                passed=bool(request.approved_by),
                detail=request.approved_by or "sin aprobador",
            ),
            PromotionGateCheck(
                name="safety_score",
                passed=bool(capability and capability.safety_score >= request.min_safety_score),
                detail=f"{capability.safety_score if capability else 0}/100 >= {request.min_safety_score}",
            ),
            PromotionGateCheck(
                name="evaluation_available",
                passed=not request.require_evaluation or latest_eval is not None,
                detail=latest_eval.run_id if latest_eval else "sin evaluation run",
            ),
        ]
        if latest_eval is not None:
            devcore_score = latest_eval.category_scores.get("devcore", 0)
            checks.append(
                PromotionGateCheck(
                    name="devcore_evaluation_score",
                    passed=devcore_score >= 67,
                    detail=f"{devcore_score}/100 >= 67",
                )
            )
        approved = all(check.passed for check in checks)
        if capability is not None:
            status = DevCoreCapabilityStatus.ACTIVE if approved else DevCoreCapabilityStatus.BLOCKED
            capability = capability.model_copy(update={"status": status})
            self._capabilities[request.capability_id] = capability
        return DevCoreCapabilityPromotionDecision(
            capability_id=request.capability_id,
            approved=approved,
            capability=capability,
            checks=checks,
            evaluation_run_id=latest_eval.run_id if latest_eval else None,
        )

    def plan(self, request: DevCorePlanRequest) -> DevCorePlanResponse:
        normalized = request.goal.lower()
        targets = self._targets_for_goal(normalized)
        recommended_agent = self._agent_for_goal(normalized)
        steps = [
            DevCorePlanStep(
                order=1,
                action="inspect",
                target=", ".join(targets),
                safety="read-only repo scan before edits",
            ),
            DevCorePlanStep(
                order=2,
                action="design",
                target="minimal scoped change plan",
                safety="prefer existing project patterns",
            ),
            DevCorePlanStep(
                order=3,
                action="verify",
                target=self._verification_for_goal(normalized),
                safety="run checks before commit",
            ),
        ]
        return DevCorePlanResponse(
            goal=request.goal,
            summary=f"DevCore preparo una ruta local segura para: {request.goal}",
            recommended_agent=recommended_agent,
            steps=steps,
        )

    def _targets_for_goal(self, goal: str) -> list[str]:
        targets: list[str] = []
        if any(keyword in goal for keyword in ("frontend", "dashboard", "ui")):
            targets.append("frontend/app")
        if any(keyword in goal for keyword in ("api", "backend", "endpoint", "fastapi")):
            targets.append("backend/src/ceibo_core/api")
        if any(keyword in goal for keyword in ("db", "database", "alembic", "persistencia")):
            targets.append("backend/migrations")
        if any(keyword in goal for keyword in ("test", "eval", "quality")):
            targets.append("backend/tests")
        return targets or ["repo root"]

    def _agent_for_goal(self, goal: str) -> AgentRole:
        if any(keyword in goal for keyword in ("security", "seguridad", "rbac", "audit")):
            return AgentRole.CYBERSECURITY
        if any(keyword in goal for keyword in ("docker", "compose", "deploy", "ci", "alembic")):
            return AgentRole.INFRASTRUCTURE
        if any(keyword in goal for keyword in ("memoria", "knowledge", "rag")):
            return AgentRole.MEMORY
        return AgentRole.AUTOMATION

    def _verification_for_goal(self, goal: str) -> str:
        if any(keyword in goal for keyword in ("frontend", "dashboard", "ui")):
            return "npm run build"
        if any(keyword in goal for keyword in ("docker", "compose")):
            return "docker compose config"
        return "python -m pytest backend/tests"


devcore_service = DevCoreService()
