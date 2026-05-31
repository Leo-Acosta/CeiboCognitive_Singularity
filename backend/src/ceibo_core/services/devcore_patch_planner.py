from __future__ import annotations

from ceibo_core.models.schemas import (
    DevCoreParseRequest,
    DevCorePatchPlanFile,
    DevCorePatchPlannerRequest,
    DevCorePatchPlannerResponse,
    DevCoreValidationIssue,
)
from ceibo_core.services.devcore import devcore_service


class DevCorePatchPlanner:
    def plan(self, request: DevCorePatchPlannerRequest) -> DevCorePatchPlannerResponse:
        parsed = devcore_service.parse(DevCoreParseRequest(message=request.goal, context=request.context))
        files = self._files_for_intent(parsed.intent, request.goal.lower())
        steps = self._steps_for_intent(parsed.intent)
        tests = self._tests_for_goal(request.goal.lower())
        issues = list(parsed.validation_issues)
        if parsed.policy_action == "block":
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="patch_planning_blocked_by_policy",
                    message="No se genera patch plan aplicable para solicitudes bloqueadas por politica.",
                )
            )
        if not files and parsed.policy_action != "block":
            issues.append(
                DevCoreValidationIssue(
                    severity="info",
                    code="patch_targets_need_review",
                    message="No se pudo inferir un archivo objetivo concreto; revisar alcance antes de aplicar cambios.",
                )
            )
        return DevCorePatchPlannerResponse(
            goal=request.goal,
            intent=parsed.intent,
            risk_level=parsed.risk_level,
            policy_action=parsed.policy_action,
            cyber_category=parsed.cyber_category,
            requires_confirmation=True,
            files=files,
            steps=steps,
            suggested_tests=tests,
            diff_preview=self._diff_preview(files, parsed.intent),
            validation_issues=issues,
            applies_changes=False,
        )

    def _files_for_intent(self, intent: str, goal: str) -> list[DevCorePatchPlanFile]:
        files: list[DevCorePatchPlanFile] = []
        if intent == "create_endpoint" or "fastapi" in goal or "backend" in goal:
            files.append(
                DevCorePatchPlanFile(
                    path="backend/src/ceibo_core/api/routes/devcore.py",
                    change_type="modify",
                    rationale="Agregar o conectar ruta FastAPI siguiendo el router existente.",
                )
            )
            files.append(
                DevCorePatchPlanFile(
                    path="backend/tests/test_agents.py",
                    change_type="modify",
                    rationale="Cubrir contrato del endpoint o servicio con test enfocado.",
                )
            )
        if "frontend" in goal or "ui" in goal or "workbench" in goal or "react" in goal:
            files.append(
                DevCorePatchPlanFile(
                    path="frontend/app/page.tsx",
                    change_type="modify",
                    rationale="Actualizar experiencia del Workbench sin agregar paneles innecesarios.",
                )
            )
        if "docs" in goal or "documenta" in goal:
            files.append(
                DevCorePatchPlanFile(
                    path="docs/devcore.md",
                    change_type="modify",
                    rationale="Documentar contrato, limites y flujo de seguridad.",
                )
            )
        return files

    def _steps_for_intent(self, intent: str) -> list[str]:
        if intent == "create_endpoint":
            return [
                "Confirmar contrato del endpoint: metodo, ruta, payload y respuesta.",
                "Ubicar router o servicio existente antes de crear archivos nuevos.",
                "Preparar diff minimo con test enfocado.",
                "Revisar seguridad y ejecutar tests antes de aplicar.",
            ]
        return [
            "Inspeccionar archivos objetivo en modo solo lectura.",
            "Preparar cambio minimo y reversible.",
            "Generar diff preview para revision humana.",
            "Ejecutar verificacion sugerida antes de aplicar.",
        ]

    def _tests_for_goal(self, goal: str) -> list[str]:
        tests: list[str] = []
        if "frontend" in goal or "ui" in goal or "react" in goal:
            tests.append("npm run build")
        if "backend" in goal or "fastapi" in goal or "endpoint" in goal:
            tests.append("python -m pytest backend/tests/test_agents.py -q")
        if not tests:
            tests.append("python -m pytest backend/tests -q")
        return tests

    def _diff_preview(self, files: list[DevCorePatchPlanFile], intent: str) -> str:
        if not files:
            return "No diff preview generated until target files are confirmed."
        lines = [
            "diff --git a/<target> b/<target>",
            "--- a/<target>",
            "+++ b/<target>",
            "@@",
            f"+# DevCore Patch Planner preview for intent: {intent}",
            "+# No files are modified by this preview.",
        ]
        lines.extend(f"+# target: {file.path} ({file.change_type})" for file in files)
        return "\n".join(lines)


devcore_patch_planner = DevCorePatchPlanner()
