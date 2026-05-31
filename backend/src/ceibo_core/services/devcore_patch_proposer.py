from __future__ import annotations

from ceibo_core.models.schemas import (
    DevCoreParseRequest,
    DevCoreParsedParameter,
    DevCorePatchChange,
    DevCorePatchPlanFile,
    DevCorePatchProposeRequest,
    DevCorePatchProposeResponse,
    DevCoreValidationIssue,
)
from ceibo_core.services.devcore import devcore_service


class DevCorePatchProposer:
    def propose(self, request: DevCorePatchProposeRequest) -> DevCorePatchProposeResponse:
        parsed = devcore_service.parse(DevCoreParseRequest(message=request.goal, context=request.context))
        issues = list(parsed.validation_issues)
        if parsed.policy_action == "block":
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="patch_proposal_blocked_by_policy",
                    message="No se generan cambios propuestos para solicitudes bloqueadas por politica.",
                )
            )
            return self._response(request, [], issues)

        changes = self._changes_for_goal(request.files, parsed.parameters)
        if not changes:
            issues.append(
                DevCoreValidationIssue(
                    severity="info",
                    code="patch_proposal_needs_manual_authoring",
                    message="No se pudo generar contenido aplicable; completar proposed_changes manualmente.",
                )
            )
        return self._response(request, changes, issues)

    def _changes_for_goal(
        self,
        files: list[DevCorePatchPlanFile],
        parameters: list[DevCoreParsedParameter],
    ) -> list[DevCorePatchChange]:
        endpoint_path = self._parameter(parameters, "endpoint_path") or "/api/v1/generated"
        http_method = (self._parameter(parameters, "http_method") or "GET").lower()
        changes: list[DevCorePatchChange] = []
        for file in files:
            if file.path.endswith(".py") and "api/routes" in file.path.replace("\\", "/"):
                changes.append(
                    DevCorePatchChange(
                        path=file.path,
                        change_type=file.change_type,
                        content=self._fastapi_route_content(endpoint_path, http_method),
                    )
                )
            elif file.path.endswith(".py") and "tests" in file.path.replace("\\", "/"):
                changes.append(
                    DevCorePatchChange(
                        path=file.path,
                        change_type=file.change_type,
                        content=self._pytest_content(file.path, endpoint_path, http_method),
                    )
                )
            elif file.path.endswith(".md"):
                changes.append(
                    DevCorePatchChange(
                        path=file.path,
                        change_type=file.change_type,
                        content="# DevCore Proposed Change\n\nDescribe el cambio propuesto antes de aplicar.\n",
                    )
                )
        return changes

    def _parameter(self, parameters: list[DevCoreParsedParameter], name: str) -> str | None:
        for parameter in parameters:
            if parameter.name == name:
                return parameter.value
        return None

    def _fastapi_route_content(self, endpoint_path: str, http_method: str) -> str:
        function_name = endpoint_path.strip("/").replace("/", "_").replace("-", "_") or "generated"
        return (
            "from fastapi import APIRouter\n\n"
            "router = APIRouter()\n\n\n"
            f"@router.{http_method}(\"{endpoint_path}\")\n"
            f"async def {http_method}_{function_name}() -> dict[str, str]:\n"
            "    return {\"status\": \"ok\"}\n"
        )

    def _pytest_content(self, file_path: str, endpoint_path: str, http_method: str) -> str:
        function_name = endpoint_path.strip("/").replace("/", "_").replace("-", "_") or "generated"
        module_name = file_path.replace("\\", "/").split("/")[-1].removeprefix("test_").removesuffix("_api.py")
        return (
            "import pytest\n\n"
            f"from ceibo_core.api.routes.{module_name} import {http_method}_{function_name}\n\n\n"
            "@pytest.mark.asyncio\n"
            f"async def test_{http_method}_{function_name}_returns_ok():\n"
            f"    response = await {http_method}_{function_name}()\n\n"
            "    assert response == {\"status\": \"ok\"}\n"
        )

    def _response(
        self,
        request: DevCorePatchProposeRequest,
        changes: list[DevCorePatchChange],
        issues: list[DevCoreValidationIssue],
    ) -> DevCorePatchProposeResponse:
        return DevCorePatchProposeResponse(
            patch_plan_id=request.patch_plan_id,
            goal=request.goal,
            proposed_changes=changes,
            diff_preview=self._diff_preview(changes),
            suggested_tests=self._tests_for_goal(request.goal.lower()),
            validation_issues=issues,
            applies_changes=False,
        )

    def _diff_preview(self, changes: list[DevCorePatchChange]) -> str:
        if not changes:
            return "No proposed diff generated."
        lines: list[str] = []
        for change in changes:
            lines.extend(
                [
                    f"diff --git a/{change.path} b/{change.path}",
                    f"--- a/{change.path}",
                    f"+++ b/{change.path}",
                    "@@",
                ]
            )
            lines.extend(f"+{line}" for line in change.content.splitlines())
        return "\n".join(lines)

    def _tests_for_goal(self, goal: str) -> list[str]:
        tests: list[str] = []
        if "frontend" in goal or "ui" in goal or "react" in goal:
            tests.append("npm run build")
        if "backend" in goal or "fastapi" in goal or "endpoint" in goal:
            tests.append("python -m pytest backend/tests/test_agents.py -q")
        return tests or ["python -m pytest backend/tests -q"]


devcore_patch_proposer = DevCorePatchProposer()
