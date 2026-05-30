# Ceibo Cognitive Singularity

Ceibo Cognitive Singularity es una plataforma local-first de inteligencia
artificial progresiva. Su nucleo operativo, CEIBO CORE, esta orientado a
agentes IA, voz natural, memoria persistente, automatizacion, control de
sistema operativo, entrenamiento local e infraestructura distribuida.

El proyecto no afirma haber alcanzado una Singularidad de IA. La Singularidad
se toma como horizonte tecnico medible: mejorar por ciclos controlados de
memoria, razonamiento, entrenamiento, uso de herramientas, autonomia,
seguridad y evaluacion continua.

## Objetivo

Construir un sistema central, modular, escalable y entrenable capaz de:

- Conversar con lenguaje natural.
- Coordinar agentes especializados.
- Ejecutar tareas locales y remotas.
- Mantener memoria persistente mediante RAG.
- Curar datasets propios para entrenamiento.
- Ejecutar ciclos de fine-tuning LoRA/QLoRA bajo evaluacion.
- Medir progreso con un Singularity Index.
- Integrarse con modelos cloud y locales.
- Operar con Docker, Kubernetes y GPU en fases futuras.
- Exponer APIs, WebSockets y dashboard administrativo.

## Stack inicial

- Backend: Python 3.12, FastAPI, AsyncIO, Pydantic, SQLAlchemy.
- IA: OpenAI API, Ollama, vLLM-ready, RAG, embeddings, Qdrant.
- Datos: PostgreSQL, Redis, Qdrant.
- Eventos: NATS.
- Infra: Docker Compose, Kubernetes, Helm, Traefik/NGINX-ready.
- Observabilidad: Prometheus, Grafana, Loki, OpenTelemetry-ready.
- Frontend: Next.js, React, TailwindCSS.
- Seguridad: JWT/OAuth2-ready, RBAC, rate limiting, auditoria y sandboxing.

## Estructura

```text
backend/              API, agentes y servicios core
frontend/             Dashboard Next.js
infra/                Manifests base de infraestructura
charts/ceibo-core/    Helm chart principal
docs/                 Arquitectura, agentes, seguridad y Kubernetes
scripts/              Utilidades de desarrollo
```

## Arranque local

```bash
cp .env.example .env
docker compose up --build
```

Checks de release:

```powershell
.\scripts\check.ps1
```

Migraciones:

```powershell
cd backend
alembic upgrade head
```

El `docker-compose.yml` ejecuta migraciones Alembic antes de levantar la API.

API:

- `GET /health`
- `GET /health/persistence`
- `GET /api/v1/agents`
- `POST /api/v1/agents/orchestration/plan`
- `GET /api/v1/agents/orchestration/recent`
- `GET /api/v1/status`
- `GET /api/v1/status/security`
- `GET /api/v1/status/audit`
- `GET /api/v1/status/singularity-index`
- `GET /api/v1/status/singularity-index/history`
- `POST /api/v1/status/singularity-index/snapshots`
- `GET /api/v1/engine/status`
- `POST /api/v1/engine/generate`
- `POST /api/v1/engine/evaluations/run`
- `GET /api/v1/engine/evaluations/latest`
- `GET /api/v1/engine/models`
- `POST /api/v1/engine/models/recommend`
- `GET /api/v1/engine/registry`
- `POST /api/v1/engine/registry/bootstrap`
- `POST /api/v1/engine/registry/datasets`
- `POST /api/v1/engine/registry/models`
- `POST /api/v1/engine/registry/models/promote`
- `POST /api/v1/engine/training/plan`
- `GET /api/v1/engine/training/examples`
- `POST /api/v1/engine/training/examples`
- `POST /api/v1/engine/training/feedback`
- `GET /api/v1/engine/training/stats`
- `POST /api/v1/engine/training/curate/preview`
- `POST /api/v1/engine/training/curate/export`
- `GET /api/v1/engine/teacher/status`
- `POST /api/v1/engine/teacher/review`
- `POST /api/v1/engine/teacher/synthetic-examples`
- `POST /api/v1/engine/training/qlora/preflight`
- `POST /api/v1/engine/training/qlora/start`
- `GET /api/v1/engine/training/qlora/jobs`
- `POST /api/v1/chat`
- `GET /api/v1/memory/health`
- `POST /api/v1/memory/remember`
- `GET /api/v1/memory/search`
- `GET /api/v1/memory/knowledge/status`
- `GET /api/v1/memory/knowledge`
- `POST /api/v1/memory/knowledge`
- `GET /api/v1/memory/knowledge/search`
- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/jobs`
- `POST /api/v1/tasks/jobs`
- `GET /api/v1/tasks/jobs/{job_id}`
- `WS /api/v1/ws`

Si los puertos `8000` o `8001` ya estan ocupados en desarrollo local, puedes
levantar la API en un puerto alto:

```bash
cd backend
python -m uvicorn ceibo_core.main:app --app-dir src --host 127.0.0.1 --port 8765
```

Curar dataset antes de fine-tuning:

```bash
python training/scripts/curate_dataset.py --min-score 60
```

Preflight e inicio QLoRA:

```bash
python training/scripts/run_qlora.py --config training/configs/ceibo_qlora.local.json --preflight-only
python training/scripts/run_qlora.py --config training/configs/ceibo_qlora.local.json --max-steps 1
```

## Kubernetes

```bash
kubectl apply -f infra/k8s/namespaces.yaml
helm upgrade --install ceibo-core charts/ceibo-core -n ceibo-core --create-namespace
```

## Documentacion

- [Arquitectura](docs/architecture.md)
- [Ceibo Cognitive Singularity](docs/ceibo-cognitive-singularity.md)
- [Release Readiness](docs/release-readiness.md)
- [Prompt operativo](docs/ceibo-operating-prompt.md)
- [Sistema multiagente](docs/agents.md)
- [CEIBO AI Engine](docs/local-ai-engine.md)
- [Teacher Agent local](docs/teacher-agent.md)
- [Flujo de entrenamiento local](docs/model-training-flow.md)
- [Training Runner QLoRA](docs/training-runner.md)
- [Desbloquear QLoRA en Windows](docs/qlora-unblock-windows.md)
- [Kubernetes](docs/kubernetes.md)
- [Seguridad](docs/security.md)
- [Roadmap](docs/roadmap.md)
