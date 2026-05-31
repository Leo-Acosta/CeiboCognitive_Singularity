from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from ceibo_core.models.schemas import (
    DevCoreExecutionRequest,
    DevCoreExecutionResponse,
    DevCoreParseRequest,
    DevCoreValidationIssue,
)
from ceibo_core.services.devcore import devcore_service
from ceibo_core.services.devcore_safety import devcore_safety_layer


CONFIRMATION_PHRASE = "CONFIRM_EXECUTION"
MAX_OUTPUT_CHARS = 8000
BLOCKED_COMMANDS = {
    "rm",
    "rmdir",
    "del",
    "format",
    "shutdown",
    "reboot",
    "curl",
    "wget",
    "ssh",
    "scp",
    "powershell",
}
ALLOWED_COMMANDS = {
    "python",
    "python3",
    "pytest",
    "node",
    "npm",
    "git",
}


class DevCoreExecutionSandbox:
    def __init__(self) -> None:
        self.workspace_root = Path.cwd().resolve()

    def run(self, request: DevCoreExecutionRequest) -> DevCoreExecutionResponse:
        command_parts, parse_issues = self._parse_command(request.command)
        working_directory, path_issues = self._resolve_working_directory(request.working_directory)
        executable = command_parts[0].lower() if command_parts else ""
        command_issues = self._validate_command(executable, request.command)
        parse_result = devcore_service.parse(DevCoreParseRequest(message=f"execute {request.command}"))
        safety_decision = devcore_safety_layer.classify(
            message=f"execute {request.command}".lower(),
            intent="execute_command",
            base_risk_level=parse_result.risk_level,
        )
        validation_issues = [
            *parse_issues,
            *path_issues,
            *command_issues,
        ]
        if safety_decision.policy_action == "block":
            validation_issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="execution_blocked_by_policy",
                    message=safety_decision.summary,
                )
            )

        requires_confirmation = True
        double_confirmation_required = safety_decision.double_confirmation_required
        if request.confirmation_phrase != CONFIRMATION_PHRASE:
            validation_issues.append(
                DevCoreValidationIssue(
                    severity="warning",
                    code="execution_confirmation_required",
                    message=f"Para ejecutar en sandbox envia confirmation_phrase={CONFIRMATION_PHRASE}.",
                )
            )

        if any(issue.severity == "error" for issue in validation_issues):
            return self._response(
                request=request,
                working_directory=working_directory,
                status="blocked",
                risk_level=safety_decision.risk_level,
                cyber_category=safety_decision.category,
                policy_action=safety_decision.policy_action,
                requires_confirmation=requires_confirmation,
                double_confirmation_required=double_confirmation_required,
                validation_issues=validation_issues,
            )

        if request.confirmation_phrase != CONFIRMATION_PHRASE:
            return self._response(
                request=request,
                working_directory=working_directory,
                status="confirmation_required",
                risk_level=safety_decision.risk_level,
                cyber_category=safety_decision.category,
                policy_action=safety_decision.policy_action,
                requires_confirmation=requires_confirmation,
                double_confirmation_required=double_confirmation_required,
                validation_issues=validation_issues,
            )

        try:
            completed = subprocess.run(
                command_parts,
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return self._response(
                request=request,
                working_directory=working_directory,
                status="timeout",
                risk_level=safety_decision.risk_level,
                cyber_category=safety_decision.category,
                policy_action=safety_decision.policy_action,
                requires_confirmation=requires_confirmation,
                double_confirmation_required=double_confirmation_required,
                validation_issues=validation_issues,
                stdout=(exc.stdout or "")[:MAX_OUTPUT_CHARS],
                stderr=(exc.stderr or "Command timed out.")[:MAX_OUTPUT_CHARS],
            )
        return self._response(
            request=request,
            working_directory=working_directory,
            status="completed" if completed.returncode == 0 else "failed",
            exit_code=completed.returncode,
            risk_level=safety_decision.risk_level,
            cyber_category=safety_decision.category,
            policy_action=safety_decision.policy_action,
            requires_confirmation=requires_confirmation,
            double_confirmation_required=double_confirmation_required,
            validation_issues=validation_issues,
            stdout=completed.stdout[:MAX_OUTPUT_CHARS],
            stderr=completed.stderr[:MAX_OUTPUT_CHARS],
        )

    def _parse_command(self, command: str) -> tuple[list[str], list[DevCoreValidationIssue]]:
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            return [], [
                DevCoreValidationIssue(
                    severity="error",
                    code="invalid_command_syntax",
                    message=f"No se pudo parsear el comando: {exc}.",
                )
            ]
        if not parts:
            return [], [
                DevCoreValidationIssue(
                    severity="error",
                    code="empty_command",
                    message="El comando esta vacio.",
                )
            ]
        return parts, []

    def _resolve_working_directory(self, working_directory: str) -> tuple[Path, list[DevCoreValidationIssue]]:
        candidate = (self.workspace_root / working_directory).resolve()
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError:
            return candidate, [
                DevCoreValidationIssue(
                    severity="error",
                    code="workspace_escape_blocked",
                    message="El directorio de trabajo debe estar dentro del workspace.",
                )
            ]
        if not candidate.exists() or not candidate.is_dir():
            return candidate, [
                DevCoreValidationIssue(
                    severity="error",
                    code="working_directory_not_found",
                    message="El directorio de trabajo no existe.",
                )
            ]
        return candidate, []

    def _validate_command(self, executable: str, command: str) -> list[DevCoreValidationIssue]:
        issues: list[DevCoreValidationIssue] = []
        normalized = command.lower()
        if executable in BLOCKED_COMMANDS:
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="blocked_executable",
                    message=f"El ejecutable {executable} no esta permitido en el sandbox v1.",
                )
            )
        if executable not in ALLOWED_COMMANDS:
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="executable_not_allowlisted",
                    message=f"El ejecutable {executable} no esta en la allowlist del sandbox v1.",
                )
            )
        if any(fragment in normalized for fragment in ("&&", "||", ";", "|", ">", "<", "`")):
            issues.append(
                DevCoreValidationIssue(
                    severity="error",
                    code="shell_operator_blocked",
                    message="Los operadores de shell estan bloqueados; envia un comando simple.",
                )
            )
        return issues

    def _response(
        self,
        request: DevCoreExecutionRequest,
        working_directory: Path,
        status: str,
        risk_level: str,
        cyber_category: str,
        policy_action: str,
        requires_confirmation: bool,
        double_confirmation_required: bool,
        validation_issues: list[DevCoreValidationIssue],
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> DevCoreExecutionResponse:
        return DevCoreExecutionResponse(
            command=request.command,
            working_directory=str(working_directory),
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            risk_level=risk_level,
            cyber_category=cyber_category,
            policy_action=policy_action,
            requires_confirmation=requires_confirmation,
            double_confirmation_required=double_confirmation_required,
            validation_issues=validation_issues,
            audit_notes=[
                "Sandbox v1 usa allowlist de ejecutables y shell=False.",
                "La ejecucion queda limitada al workspace resuelto.",
            ],
        )


devcore_execution_sandbox = DevCoreExecutionSandbox()
