from __future__ import annotations

from dataclasses import dataclass
import re

from ceibo_core.models.schemas import (
    DevCoreTemplateParameter,
    DevCoreTemplateRecord,
    DevCoreTemplateRenderRequest,
    DevCoreTemplateRenderResponse,
    DevCoreValidationIssue,
)


@dataclass(frozen=True)
class TemplateDefinition:
    template_id: str
    name: str
    language: str
    description: str
    artifact_name: str
    parameters: tuple[DevCoreTemplateParameter, ...]
    body: str
    safety_notes: tuple[str, ...]


SAFE_VALUE_PATTERN = re.compile(r"^[a-zA-Z0-9_\-./:{} ]{1,160}$")
DANGEROUS_FRAGMENTS = (
    "rm -rf",
    "format ",
    "del /f",
    "drop database",
    "truncate table",
    "xp_cmdshell",
    "invoke-expression",
    "iex ",
    "powershell -enc",
    "curl |",
    "wget |",
)


TEMPLATES: dict[str, TemplateDefinition] = {
    "fastapi_endpoint": TemplateDefinition(
        template_id="fastapi_endpoint",
        name="FastAPI endpoint",
        language="python",
        description="Endpoint FastAPI con contrato basico y sin efectos externos.",
        artifact_name="{module_name}.py",
        parameters=(
            DevCoreTemplateParameter(name="module_name", description="Nombre del modulo Python."),
            DevCoreTemplateParameter(name="router_name", description="Nombre del APIRouter."),
            DevCoreTemplateParameter(name="http_method", description="Metodo HTTP, por ejemplo get o post."),
            DevCoreTemplateParameter(name="endpoint_path", description="Ruta del endpoint, por ejemplo /api/v1/tools."),
            DevCoreTemplateParameter(name="function_name", description="Nombre de la funcion handler."),
        ),
        body='''from fastapi import APIRouter

{router_name} = APIRouter()


@{router_name}.{http_method}("{endpoint_path}")
async def {function_name}() -> dict[str, str]:
    return {{"status": "ok"}}
''',
        safety_notes=(
            "Plantilla sin acceso a filesystem, red externa o shell.",
            "Debe revisarse y probarse antes de integrarse al router principal.",
        ),
    ),
    "python_service": TemplateDefinition(
        template_id="python_service",
        name="Python service",
        language="python",
        description="Clase de servicio Python con metodo inicial puro.",
        artifact_name="{service_name}.py",
        parameters=(
            DevCoreTemplateParameter(name="service_name", description="Nombre de archivo o modulo."),
            DevCoreTemplateParameter(name="class_name", description="Nombre de la clase."),
            DevCoreTemplateParameter(name="method_name", description="Nombre del metodo inicial."),
        ),
        body='''class {class_name}:
    def {method_name}(self) -> dict[str, str]:
        return {{"status": "ready"}}
''',
        safety_notes=("No ejecuta comandos ni modifica estado externo.",),
    ),
    "powershell_task": TemplateDefinition(
        template_id="powershell_task",
        name="PowerShell task",
        language="powershell",
        description="Script PowerShell informativo con confirmacion manual.",
        artifact_name="{script_name}.ps1",
        parameters=(
            DevCoreTemplateParameter(name="script_name", description="Nombre del script."),
            DevCoreTemplateParameter(name="task_label", description="Etiqueta visible de la tarea."),
        ),
        body='''param(
    [switch]$ConfirmRun
)

if (-not $ConfirmRun) {{
    Write-Host "Preview only: {task_label}"
    Write-Host "Run again with -ConfirmRun after reviewing the script."
    exit 0
}}

Write-Host "Running reviewed task: {task_label}"
''',
        safety_notes=(
            "Incluye modo preview por defecto.",
            "No contiene Invoke-Expression ni descarga remota.",
        ),
    ),
    "bash_task": TemplateDefinition(
        template_id="bash_task",
        name="Bash task",
        language="bash",
        description="Script Bash con preview por defecto.",
        artifact_name="{script_name}.sh",
        parameters=(
            DevCoreTemplateParameter(name="script_name", description="Nombre del script."),
            DevCoreTemplateParameter(name="task_label", description="Etiqueta visible de la tarea."),
        ),
        body='''#!/usr/bin/env bash
set -euo pipefail

if [[ "${{1:-}}" != "--confirm-run" ]]; then
  echo "Preview only: {task_label}"
  echo "Run with --confirm-run after reviewing the script."
  exit 0
fi

echo "Running reviewed task: {task_label}"
''',
        safety_notes=("Incluye confirmacion explicita antes de ejecutar la rama activa.",),
    ),
    "react_component": TemplateDefinition(
        template_id="react_component",
        name="React component",
        language="tsx",
        description="Componente React presentacional y sin side effects.",
        artifact_name="{component_name}.tsx",
        parameters=(
            DevCoreTemplateParameter(name="component_name", description="Nombre PascalCase del componente."),
            DevCoreTemplateParameter(name="title", description="Titulo visible."),
        ),
        body='''type {component_name}Props = {{
  subtitle?: string;
}};

export function {component_name}({{ subtitle }}: {component_name}Props) {{
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
      {{subtitle ? <p className="mt-2 text-sm text-slate-600">{{subtitle}}</p> : null}}
    </section>
  );
}}
''',
        safety_notes=("No usa efectos, fetch ni ejecucion dinamica.",),
    ),
    "sql_migration": TemplateDefinition(
        template_id="sql_migration",
        name="SQL migration",
        language="sql",
        description="Migracion SQL aditiva con tabla simple.",
        artifact_name="{migration_name}.sql",
        parameters=(
            DevCoreTemplateParameter(name="migration_name", description="Nombre del archivo de migracion."),
            DevCoreTemplateParameter(name="table_name", description="Nombre de tabla."),
        ),
        body='''CREATE TABLE IF NOT EXISTS {table_name} (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
''',
        safety_notes=("Solo genera SQL aditivo; no incluye DROP, TRUNCATE ni DELETE.",),
    ),
}


class DevCoreTemplateEngine:
    def list_templates(self) -> list[DevCoreTemplateRecord]:
        return [
            DevCoreTemplateRecord(
                template_id=template.template_id,
                name=template.name,
                language=template.language,
                description=template.description,
                parameters=list(template.parameters),
                safety_notes=list(template.safety_notes),
            )
            for template in TEMPLATES.values()
        ]

    def render(self, request: DevCoreTemplateRenderRequest) -> DevCoreTemplateRenderResponse:
        template = TEMPLATES.get(request.template_id)
        if template is None:
            return DevCoreTemplateRenderResponse(
                template_id=request.template_id,
                language="unknown",
                artifact_name="unknown",
                content="",
                missing_parameters=[],
                validation_issues=[
                    DevCoreValidationIssue(
                        severity="error",
                        code="unknown_template",
                        message="La plantilla solicitada no existe.",
                    )
                ],
                safety_notes=["No se genero contenido."],
            )

        missing = [
            parameter.name
            for parameter in template.parameters
            if parameter.required and not request.parameters.get(parameter.name)
        ]
        issues = self._validate_parameters(request.parameters)
        if missing:
            issues.append(
                DevCoreValidationIssue(
                    severity="info",
                    code="missing_template_parameters",
                    message=f"Faltan parametros requeridos: {', '.join(missing)}.",
                )
            )

        values = {
            parameter.name: request.parameters.get(parameter.name) or parameter.default or f"{{{parameter.name}}}"
            for parameter in template.parameters
        }
        content = "" if any(issue.severity == "error" for issue in issues) else template.body.format_map(values)
        artifact_name = template.artifact_name.format_map(values)
        return DevCoreTemplateRenderResponse(
            template_id=template.template_id,
            language=template.language,
            artifact_name=artifact_name,
            content=content,
            missing_parameters=missing,
            validation_issues=issues,
            safe_to_execute=False,
            requires_review=True,
            safety_notes=[
                *template.safety_notes,
                "DevCore solo genera la plantilla; no la escribe ni ejecuta automaticamente.",
            ],
        )

    def _validate_parameters(self, parameters: dict[str, str]) -> list[DevCoreValidationIssue]:
        issues: list[DevCoreValidationIssue] = []
        for name, value in parameters.items():
            normalized = value.lower()
            if any(fragment in normalized for fragment in DANGEROUS_FRAGMENTS):
                issues.append(
                    DevCoreValidationIssue(
                        severity="error",
                        code="unsafe_template_parameter",
                        message=f"El parametro {name} contiene una secuencia no permitida.",
                    )
                )
            if not SAFE_VALUE_PATTERN.match(value):
                issues.append(
                    DevCoreValidationIssue(
                        severity="warning",
                        code="template_parameter_needs_review",
                        message=f"El parametro {name} contiene caracteres que requieren revision manual.",
                    )
                )
        return issues


devcore_template_engine = DevCoreTemplateEngine()
