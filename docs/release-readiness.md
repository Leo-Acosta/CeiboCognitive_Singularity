# Release Readiness v1

Este documento define el minimo operativo para considerar publicable una version
privada de Ceibo Cognitive Singularity.

## Estado del sistema

La version actual incluye:

- Backend FastAPI con health checks, RBAC, audit trail y persistencia opcional.
- Dashboard Next.js para chat, tareas, evaluacion, training, registry, jobs y Singularity Index.
- Memoria local con embeddings deterministas y adaptador Qdrant-ready.
- Knowledge Base v1 con saneamiento de secretos antes de persistir contenido.
- Evaluation Harness v1.
- Model/Dataset Registry v1 con gate de promocion.
- Agent Orchestration v1 con trazas y handoffs.
- Long-running Jobs v1 para tareas, evaluaciones y training.

## Checks obligatorios

Desde la raiz del repo:

```powershell
.\scripts\check.ps1
```

El check ejecuta:

- `python -m pytest backend\tests`
- `npm run build` dentro de `frontend/`
- Validacion de archivos base de release

## Arranque local recomendado

Backend sin Docker:

```powershell
cd backend
python -m uvicorn ceibo_core.main:app --app-dir src --host 127.0.0.1 --port 8765
```

Frontend:

```powershell
cd frontend
$env:NEXT_PUBLIC_API_URL="http://localhost:8765"
npm run dev
```

Stack completo:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Variables criticas

Antes de usar fuera de desarrollo local:

- Cambiar `JWT_SECRET`.
- Revisar `RBAC_ENFORCED`.
- Revisar `LOCAL_DEV_ADMIN_ENABLED`.
- Confirmar `DATABASE_URL`.
- Confirmar `PERSISTENCE_ENABLED`.
- Confirmar `EVENT_BUS_ENABLED`.
- Confirmar `MEMORY_VECTOR_ENABLED`.
- Definir `NEXT_PUBLIC_API_URL` para el frontend.

## Smoke test manual

1. Abrir `GET /health`.
2. Abrir `GET /health/persistence`.
3. Abrir `GET /api/v1/status`.
4. Crear una tarea con `POST /api/v1/tasks`.
5. Revisar trazas en `GET /api/v1/agents/orchestration/recent`.
6. Revisar jobs en `GET /api/v1/tasks/jobs`.
7. Ejecutar `POST /api/v1/engine/evaluations/run`.
8. Revisar `GET /api/v1/status/audit`.
9. Verificar el dashboard con el backend local.

## Politica de secretos

No commitear `.env`, credenciales, tokens, exports de bases de datos ni logs con
datos sensibles. La memoria y Knowledge Base aplican redaccion basica, pero eso
no reemplaza la revision humana antes de publicar datasets o documentos.

## Criterio de salida

Sprint 12 se considera listo cuando:

- La suite backend pasa.
- El build frontend pasa.
- `.env.example` documenta las variables necesarias.
- README lista endpoints y flujo local vigente.
- El repo privado queda con commit y push de release readiness.
