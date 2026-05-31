# Ceibo DevCore Local MVP

DevCore es el modulo interno de CEIBO para asistencia de desarrollo local. En
esta version MVP opera en modo seguro y de solo lectura: inspecciona el repo,
propone rutas de cambio, recomienda agente y sugiere verificaciones.

## Capacidades v1

- Inspeccion de repo.
- Planificacion de cambios.
- Recomendacion de agente.
- Ruteo de checks.
- Parser controlado de lenguaje natural: intenciones, parametros, sinonimos,
  riesgo, validacion y respuesta estructurada.
- Template Engine seguro: plantillas Python, PowerShell, Bash, FastAPI, React y
  SQL sin escritura ni ejecucion automatica.
- Cyber Safety Layer: clasificacion cyber, `lab_policy.yaml`, confirmacion,
  doble confirmacion y bloqueo de solicitudes peligrosas.
- Execution Sandbox v1: ejecucion controlada dentro del workspace con allowlist,
  confirmacion explicita y auditoria.
- Patch Planner v1: prepara archivos objetivo, pasos, tests y diff preview sin
  aplicar cambios.
- Patch Proposer v1: genera `proposed_changes` revisables desde un patch plan,
  sin escribir archivos.
- Apply Patch Gate v1: aplica cambios propuestos solo con `patch_plan_id`,
  confirmacion explicita, validacion de workspace y auditoria.
- Patch Preflight v1: bloquea `create` sobre archivos existentes y `modify`
  sobre archivos ausentes antes de escribir.
- Automatizacion local segura.
- Auditoria de planes generados.
- Persistencia de planes como Knowledge Base.
- Caso dedicado en Evaluation Harness.

## Endpoints

- `GET /api/v1/devcore/status`
- `GET /api/v1/devcore/capabilities`
- `GET /api/v1/devcore/safety/policy`
- `GET /api/v1/devcore/templates`
- `POST /api/v1/devcore/templates/render`
- `POST /api/v1/devcore/execute`
- `POST /api/v1/devcore/patch-plan`
- `POST /api/v1/devcore/patch-propose`
- `POST /api/v1/devcore/patch-apply`
- `POST /api/v1/devcore/parse`
- `POST /api/v1/devcore/capabilities/promote`
- `POST /api/v1/devcore/plan`

Ejemplo de parse:

```json
{
  "message": "agrega un endpoint FastAPI backend con tests",
  "user_id": "local-user",
  "context": []
}
```

Ejemplo de plan:

```json
{
  "goal": "agrega un endpoint backend con tests",
  "user_id": "local-user",
  "context": []
}
```

Ejemplo de render de plantilla:

```json
{
  "template_id": "fastapi_endpoint",
  "parameters": {
    "module_name": "tools",
    "router_name": "router",
    "http_method": "post",
    "endpoint_path": "/api/v1/tools",
    "function_name": "create_tool"
  }
}
```

La respuesta incluye `content`, `artifact_name`, `validation_issues`,
`safe_to_execute=false` y `requires_review=true`.

Ejemplo de ejecucion sandbox:

```json
{
  "command": "python --version",
  "working_directory": ".",
  "confirmation_phrase": "CONFIRM_EXECUTION",
  "timeout_seconds": 30
}
```

Sin `CONFIRM_EXECUTION`, DevCore devuelve `confirmation_required`. Los comandos
se ejecutan con `shell=false`, dentro del workspace resuelto y con allowlist de
ejecutables.

Ejemplo de patch planner:

```json
{
  "goal": "Crea POST /api/v1/tools en FastAPI con tests",
  "context": []
}
```

La respuesta incluye archivos objetivo, pasos, tests sugeridos y `diff_preview`.
`applies_changes` siempre es `false` en v1.

Ejemplo de patch proposer:

```json
{
  "patch_plan_id": "plan-id",
  "goal": "Crea POST /api/v1/tools en FastAPI con tests",
  "files": [
    {
      "path": "backend/src/ceibo_core/api/routes/tools.py",
      "change_type": "create",
      "rationale": "crear router revisable"
    }
  ]
}
```

La respuesta incluye `proposed_changes`, `diff_preview`, `suggested_tests` y
`applies_changes=false`.

Ejemplo de apply gate:

```json
{
  "patch_plan_id": "plan-id",
  "goal": "Crea POST /api/v1/tools en FastAPI con tests",
  "files": [
    {
      "path": "backend/tests/generated_test.py",
      "change_type": "create",
      "rationale": "validar contrato"
    }
  ],
  "proposed_changes": [
    {
      "path": "backend/tests/generated_test.py",
      "change_type": "create",
      "content": "def test_generated():\n    assert True\n"
    }
  ],
  "confirmation_phrase": "APPLY_PATCH"
}
```

Sin `APPLY_PATCH`, DevCore devuelve `confirmation_required`. El gate bloquea
paths absolutos, escapes del workspace, `.git`, deletes y solicitudes bloqueadas
por politica.

El preflight tambien bloquea sobrescrituras silenciosas: `create` falla si el
archivo ya existe y `modify` falla si el archivo objetivo todavia no existe.

## Limites actuales

- No escribe archivos sin un `patch-apply` confirmado.
- No aplica patch plans desde el preview; requiere cambios propuestos y gate.
- No aplica cambios que no pertenezcan a los archivos del patch plan.
- No sobrescribe archivos existentes con cambios `create`.
- No crea archivos implicitamente desde cambios `modify`.
- No ejecuta comandos.
- No aplica plantillas sin revision humana.
- No ejecuta comandos fuera del workspace.
- No permite operadores de shell, comandos no allowlisted ni ejecutables
  destructivos en Sandbox v1.
- Bloquea solicitudes de robo de credenciales, malware, phishing, evasion,
  destruccion o acceso no autorizado.
- Exige confirmacion para ejecucion local, cambios de infraestructura, manejo
  de credenciales y migraciones.
- Exige doble confirmacion para riesgos altos o bloqueados.
- No aplica cambios destructivos.
- No reemplaza Audit Trail ni RBAC.

## Politica de laboratorio

La politica vive en `backend/config/devcore/lab_policy.yaml`. Define categorias
permitidas, categorias que requieren confirmacion y categorias bloqueadas. La
salida del parser incluye:

- `cyber_category`
- `policy_action`
- `allowed_environment`
- `requires_confirmation`
- `double_confirmation_required`
- `safety_summary`

La escritura y ejecucion controlada quedan detras de gates de seguridad,
auditoria y evaluacion.

## Integraciones

- Audit Trail registra `devcore.plan`, `devcore.patch_plan`,
  `devcore.patch_propose` y `devcore.patch_apply`.
- Knowledge Base guarda el plan serializado con tags `devcore` y `plan`.
- Evaluation Harness ejecuta `devcore.safe-planning`.
- RBAC permite planificacion DevCore a `admin`, `operator` y `researcher`.
- Promotion Gate activa capacidades DevCore solo con aprobacion humana, score de
  seguridad suficiente y evaluacion DevCore disponible.
- Singularity Index mide capacidades DevCore activas en `Uso de herramientas`.
