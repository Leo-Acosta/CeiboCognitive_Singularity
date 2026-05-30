# Ceibo DevCore Local MVP

DevCore es el modulo interno de CEIBO para asistencia de desarrollo local. En
esta version MVP opera en modo seguro y de solo lectura: inspecciona el repo,
propone rutas de cambio, recomienda agente y sugiere verificaciones.

## Capacidades v1

- Inspeccion de repo.
- Planificacion de cambios.
- Recomendacion de agente.
- Ruteo de checks.
- Automatizacion local segura.
- Auditoria de planes generados.
- Persistencia de planes como Knowledge Base.
- Caso dedicado en Evaluation Harness.

## Endpoints

- `GET /api/v1/devcore/status`
- `POST /api/v1/devcore/plan`

Ejemplo:

```json
{
  "goal": "agrega un endpoint backend con tests",
  "user_id": "local-user",
  "context": []
}
```

## Limites actuales

- No escribe archivos por su cuenta.
- No ejecuta comandos.
- No aplica cambios destructivos.
- No reemplaza Audit Trail ni RBAC.

La escritura y ejecucion controlada quedan para sprints posteriores, detras de
gates de seguridad, auditoria y evaluacion.

## Integraciones

- Audit Trail registra `devcore.plan`.
- Knowledge Base guarda el plan serializado con tags `devcore` y `plan`.
- Evaluation Harness ejecuta `devcore.safe-planning`.
- RBAC permite planificacion DevCore a `admin`, `operator` y `researcher`.
