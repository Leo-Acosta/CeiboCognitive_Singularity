from __future__ import annotations

from pathlib import Path

from ceibo_core.models.schemas import (
    DevCoreParseRequest,
    DevCorePatchApplyRequest,
    DevCorePatchApplyResponse,
    DevCorePatchChange,
    DevCorePatchPlanFile,
    DevCoreValidationIssue,
)
from ceibo_core.services.devcore import devcore_service


CONFIRM_PATCH_PHRASE = "APPLY_PATCH"
MAX_PATCH_CONTENT_CHARS = 200_000


class DevCorePatchApplyGate:
    def __init__(self) -> None:
        self.workspace_root = Path.cwd().resolve()

    def apply(self, request: DevCorePatchApplyRequest) -> DevCorePatchApplyResponse:
        parsed = devcore_service.parse(DevCoreParseRequest(message=request.goal))
        validation_issues = list(parsed.validation_issues)
        validation_issues.extend(self._validate_plan_files(request.files))
        validation_issues.extend(self._validate_changes(request.proposed_changes))
        validation_issues.extend(self._validate_changes_match_plan(request.files, request.proposed_changes))
        validation_issues.extend(self._validate_file_state(request.proposed_changes))

        if parsed.policy_action == "block":
            validation_issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="patch_apply_blocked_by_policy",
                    message="La politica de seguridad bloqueo la aplicacion de este patch.",
                )
            )

        if request.confirmation_phrase != CONFIRM_PATCH_PHRASE:
            validation_issues.append(
                DevCoreValidationIssue(
                    severity="warning",
                    code="patch_apply_confirmation_required",
                    message=f"Para aplicar cambios envia confirmation_phrase={CONFIRM_PATCH_PHRASE}.",
                )
            )

        if any(issue.severity == "error" for issue in validation_issues):
            return self._response(
                request=request,
                status="blocked",
                risk_level=parsed.risk_level,
                policy_action=parsed.policy_action,
                cyber_category=parsed.cyber_category,
                validation_issues=validation_issues,
            )

        if request.confirmation_phrase != CONFIRM_PATCH_PHRASE:
            return self._response(
                request=request,
                status="confirmation_required",
                risk_level=parsed.risk_level,
                policy_action=parsed.policy_action,
                cyber_category=parsed.cyber_category,
                validation_issues=validation_issues,
            )

        if not request.proposed_changes:
            validation_issues.append(
                DevCoreValidationIssue(
                    severity="warning",
                    code="no_patch_changes_provided",
                    message="El gate fue confirmado, pero no recibio cambios propuestos para aplicar.",
                )
            )
            return self._response(
                request=request,
                status="no_changes",
                risk_level=parsed.risk_level,
                policy_action=parsed.policy_action,
                cyber_category=parsed.cyber_category,
                validation_issues=validation_issues,
            )

        applied_files: list[str] = []
        for change in request.proposed_changes:
            target = self._resolve_workspace_path(change.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change.content, encoding="utf-8")
            applied_files.append(target.relative_to(self.workspace_root).as_posix())

        return self._response(
            request=request,
            status="applied",
            risk_level=parsed.risk_level,
            policy_action=parsed.policy_action,
            cyber_category=parsed.cyber_category,
            validation_issues=validation_issues,
            applied_files=applied_files,
            applies_changes=True,
        )

    def _validate_plan_files(self, files: list[DevCorePatchPlanFile]) -> list[DevCoreValidationIssue]:
        issues: list[DevCoreValidationIssue] = []
        for file in files:
            issues.extend(self._validate_path(file.path))
            if file.change_type not in {"create", "modify"}:
                issues.append(
                    DevCoreValidationIssue(
                        severity="error",
                        code="unsupported_patch_plan_change_type",
                        message=f"El tipo de cambio {file.change_type} no esta permitido en Apply Gate v1.",
                    )
                )
        return issues

    def _validate_changes(self, changes: list[DevCorePatchChange]) -> list[DevCoreValidationIssue]:
        issues: list[DevCoreValidationIssue] = []
        for change in changes:
            issues.extend(self._validate_path(change.path))
            if change.change_type not in {"create", "modify"}:
                issues.append(
                    DevCoreValidationIssue(
                        severity="error",
                        code="unsupported_patch_change_type",
                        message=f"El tipo de cambio {change.change_type} no esta permitido en Apply Gate v1.",
                    )
                )
            if len(change.content) > MAX_PATCH_CONTENT_CHARS:
                issues.append(
                    DevCoreValidationIssue(
                        severity="error",
                        code="patch_content_too_large",
                        message="El contenido propuesto excede el limite de Apply Gate v1.",
                    )
                )
        return issues

    def _validate_changes_match_plan(
        self,
        files: list[DevCorePatchPlanFile],
        changes: list[DevCorePatchChange],
    ) -> list[DevCoreValidationIssue]:
        if not files or not changes:
            return []
        planned_paths = {file.path.replace("\\", "/") for file in files}
        issues: list[DevCoreValidationIssue] = []
        for change in changes:
            if change.path.replace("\\", "/") not in planned_paths:
                issues.append(
                    DevCoreValidationIssue(
                        severity="error",
                        code="patch_change_not_in_plan",
                        message=f"El cambio {change.path} no pertenece al patch plan aprobado.",
                    )
                )
        return issues

    def _validate_file_state(self, changes: list[DevCorePatchChange]) -> list[DevCoreValidationIssue]:
        issues: list[DevCoreValidationIssue] = []
        for change in changes:
            try:
                target = self._resolve_workspace_path(change.path)
            except ValueError:
                continue
            if change.change_type == "create" and target.exists():
                issues.append(
                    DevCoreValidationIssue(
                        severity="error",
                        code="patch_create_target_exists",
                        message=f"No se puede crear {change.path}: el archivo ya existe.",
                    )
                )
            if change.change_type == "modify" and not target.exists():
                issues.append(
                    DevCoreValidationIssue(
                        severity="error",
                        code="patch_modify_target_missing",
                        message=f"No se puede modificar {change.path}: el archivo no existe.",
                    )
                )
        return issues

    def _validate_path(self, path: str) -> list[DevCoreValidationIssue]:
        issues: list[DevCoreValidationIssue] = []
        candidate = Path(path)
        if candidate.is_absolute():
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="absolute_patch_path_blocked",
                    message="Los paths del patch deben ser relativos al workspace.",
                )
            )
            return issues
        if ".git" in candidate.parts:
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="git_directory_patch_blocked",
                    message="Apply Gate v1 no permite modificar archivos dentro de .git.",
                )
            )
        try:
            self._resolve_workspace_path(path)
        except ValueError:
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="patch_workspace_escape_blocked",
                    message="El patch intenta salir del workspace permitido.",
                )
            )
        return issues

    def _resolve_workspace_path(self, path: str) -> Path:
        target = (self.workspace_root / path).resolve()
        target.relative_to(self.workspace_root)
        return target

    def _response(
        self,
        request: DevCorePatchApplyRequest,
        status: str,
        risk_level: str,
        policy_action: str,
        cyber_category: str,
        validation_issues: list[DevCoreValidationIssue],
        applied_files: list[str] | None = None,
        applies_changes: bool = False,
    ) -> DevCorePatchApplyResponse:
        return DevCorePatchApplyResponse(
            patch_plan_id=request.patch_plan_id,
            status=status,
            risk_level=risk_level,
            policy_action=policy_action,
            cyber_category=cyber_category,
            applied_files=applied_files or [],
            suggested_tests=self._tests_for_goal(request.goal.lower()),
            validation_issues=validation_issues,
            audit_notes=[
                "Apply Gate v1 exige confirmation_phrase=APPLY_PATCH.",
                "Solo se permiten create/modify dentro del workspace.",
                "Delete, paths absolutos, .git y escapes del workspace quedan bloqueados.",
                "Patch Preflight v1 bloquea create sobre archivos existentes y modify sobre archivos ausentes.",
            ],
            applies_changes=applies_changes,
        )

    def _tests_for_goal(self, goal: str) -> list[str]:
        tests: list[str] = []
        if "frontend" in goal or "ui" in goal or "react" in goal:
            tests.append("npm run build")
        if "backend" in goal or "fastapi" in goal or "endpoint" in goal:
            tests.append("python -m pytest backend/tests/test_agents.py -q")
        return tests or ["python -m pytest backend/tests -q"]


devcore_patch_apply_gate = DevCorePatchApplyGate()
