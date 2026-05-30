from pathlib import Path

from ceibo_core.models.schemas import (
    AgentRole,
    DevCorePlanRequest,
    DevCorePlanResponse,
    DevCorePlanStep,
    DevCoreStatus,
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

    def status(self) -> DevCoreStatus:
        indexed_files = sum(1 for path in self._repo_root.rglob("*") if path.is_file() and ".git" not in path.parts)
        return DevCoreStatus(
            capabilities=self.capabilities,
            repo_root=str(self._repo_root),
            indexed_files=indexed_files,
            writable=False,
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
