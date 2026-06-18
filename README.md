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
- `GET /api/v1/devcore/status`
- `GET /api/v1/devcore/capabilities`
- `POST /api/v1/devcore/capabilities/promote`
- `POST /api/v1/devcore/plan`
- `POST /api/v1/engine/evaluations/run`
- `GET /api/v1/engine/evaluations/latest`
- `GET /api/v1/engine/evaluations/training-gate`
- `GET /api/v1/engine/evaluations/remediation`
- `GET /api/v1/engine/evaluations/remediation/outcomes`
- `POST /api/v1/engine/evaluations/remediation/apply`
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
- `POST /api/v1/engine/training/learning-event`
- `GET /api/v1/engine/training/human-feedback-studio`
- `POST /api/v1/engine/training/human-feedback-studio/review`
- `GET /api/v1/engine/memory/autobiographical`
- `POST /api/v1/engine/memory/autobiographical`
- `POST /api/v1/engine/memory/autobiographical/bootstrap`
- `GET /api/v1/engine/reflections/cognitive`
- `GET /api/v1/engine/training/promotion-gate`
- `POST /api/v1/engine/training/evidence/build`
- `GET /api/v1/engine/training/dataset-expansion/latest`
- `POST /api/v1/engine/training/dataset-expansion/build`
- `GET /api/v1/engine/training/stats`
- `POST /api/v1/engine/training/curate/review`
- `POST /api/v1/engine/training/curate/preview`
- `POST /api/v1/engine/training/curate/export`
- `GET /api/v1/engine/teacher/status`
- `POST /api/v1/engine/teacher/review`
- `POST /api/v1/engine/teacher/synthetic-examples`
- `POST /api/v1/engine/training/qlora/dry-run`
- `POST /api/v1/engine/training/qlora/preflight`
- `POST /api/v1/engine/training/qlora/start`
- `GET /api/v1/engine/training/qlora/jobs`
- `POST /api/v1/chat`
- `GET /api/v1/voice/status`
- `POST /api/v1/voice/authorize`
- `POST /api/v1/voice/command`
- `POST /api/v1/voice/revoke`
- `GET /api/v1/memory/health`
- `POST /api/v1/memory/remember`
- `GET /api/v1/memory/search`
- `GET /api/v1/memory/knowledge/status`
- `GET /api/v1/memory/knowledge`

Evaluation Loop v1 persists the latest report in `training/evaluations/latest_report.json`.
The training gate reads that report after API restarts and stays blocked when the suite is missing,
needs attention, or the curated dataset is not ready.
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

## CEIBO Local AI / Ollama

CEIBO está diseñado para correr modelos localmente usando Ollama como runtime inicial. Recomendado flujo rápido:

1. Instalar Ollama en tu máquina.
2. Descargar Qwen3 8B (ejemplo):

```bash
ollama pull qwen3:8b
```

3. Ejecutar el modelo:

```bash
ollama run qwen3:8b
```

4. Verificar la API local de Ollama:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
# o
curl.exe http://127.0.0.1:11434/api/tags
```

5. Configurar `.env` (copiar `.env.example`) y ajustar:

```
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen3:8b
LOCAL_ONLY_MODE=true
ALLOW_EXTERNAL_LLM=false
```

Seguridad:

- No exponer Ollama a Internet.
- No usar 0.0.0.0 para `OLLAMA_BASE_URL`.
- No abrir el puerto 11434 en el firewall salvo un laboratorio controlado.
- CEIBO valida que Ollama esté en localhost por defecto.


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
- [Ceibo DevCore](docs/devcore.md)
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

## Commercial Vision

Ceibo AI is an Argentine AI platform designed to turn open models, local data,
professional workflows, human-like conversation, RAG, agents, and fine-tuning
into specialized assistants for real work. It focuses on employment, law,
cybersecurity, digital forensics, programming, economics, finance, and
autonomous agents. Its central brain, Ceibo Core, is a conversational,
cognitive and agentic system capable of natural human dialogue while operating
specialized verticals.

## Vision comercial

Ceibo AI es una plataforma argentina de inteligencia artificial aplicada que combina modelos abiertos, datos locales, interaccion humana natural, agentes especializados, RAG documental, fine-tuning y herramientas profesionales para asistir trabajo real en empleo, derecho, ciberseguridad, economia, programacion y automatizacion.

Ceibo AI: la inteligencia argentina que trabaja con vos.

Ceibo Core es el cerebro conversacional, cognitivo y agente de Ceibo AI, capaz de dialogar con humanos de forma natural y ademas operar verticales especializadas.

CeiboCognitive_Singularity es el repositorio tecnico que contiene el backend,
frontend, training, infraestructura y documentacion de esta plataforma. No
afirma ser una AGI ni una singularidad real: define una plataforma progresiva,
medible, auditable, conversacional, agente y entrenable.

## Ceibo Core

Ceibo Core conserva la Human Interaction Layer: conversacion natural, dialogo
sostenido, tono claro, empatico y profesional, adaptacion al usuario, memoria
contextual cuando este habilitada, futura voz, texto/audio, continuidad
conversacional y trazabilidad. Core clasifica intencion, elige vertical, llama
agentes, usa RAG, aplica guardrails y devuelve una respuesta humana, clara y
util.

## Productos y verticales

- Ceibo AI: marca comercial, SaaS local-first y cloud-ready.
- Ceibo Core: cerebro conversacional, cognitivo y agente.
- Ceibo Empleo: CV, entrevistas, ATS y postulaciones.
- Ceibo Legal: asistencia juridica argentina con revision humana.
- Ceibo Forense: ciberseguridad defensiva y evidencia digital autorizada.
- Ceibo Code: programacion, debugging, DevOps y revision.
- Ceibo Economics/Finance: economia, finanzas educativas, escenarios y riesgo.
- Ceibo Agents: agentes autonomos supervisados.

## Local-first, cloud-ready y entrenable

Local-first significa que Ceibo AI puede operar en entornos locales con Ollama,
datos propios y controles de privacidad. Cloud-ready significa que la misma
arquitectura queda preparada para despliegues con Kubernetes, vLLM, Qdrant,
PostgreSQL, Redis y observabilidad. Entrenable significa que datasets curados,
LoRA/QLoRA, evaluaciones, registros de modelos y monitoreo permiten mejorar
verticales de forma versionada.

## RAG y fine-tuning

RAG recupera documentos por vertical, cita fuentes y evita responder sin base
documental cuando el riesgo lo exige. QLoRA/LoRA permite entrenar adaptadores
especializados sin reentrenar un modelo fundacional completo.

## Modelos base

Qwen 3B sirve para smoke tests. Qwen 7B sirve como base general inicial. Qwen
Coder 7B sirve para Ceibo Code. Mistral queda como alternativa. Ollama sirve
para ejecucion local/demo. QLoRA requiere modelos compatibles con
HuggingFace/Transformers y no directamente GGUF/Ollama. La capa conversacional
de Ceibo Core debe poder operar con modelos locales o cloud segun
configuracion.

## Futuro entrenamiento

Los proximos pasos documentados son construir datasets reales de Ceibo Core
Conversational v0.1, Ceibo Legal Laboral v0.1 y Ceibo Empleo v0.1; activar
Qwen 3B smoke test y Qwen 7B QLoRA; crear adaptadores
ceibo-core-conversational-qwen7b-lora-v0.1 y ceibo-legal-qwen7b-lora-v0.1;
comparar modelos base contra adaptadores; crear RAG legal y economico
argentino; crear MVP comercial, landing page, beta cerrada, politica de
privacidad, terminos de uso e infraestructura Ollama local con futura
compatibilidad vLLM.

## Ceibo Ingenieria Inversa

Ceibo AI incorpora Ceibo Ingenieria Inversa / Ceibo Reverse Engineering como
vertical especializada para analizar, comprender, documentar, auditar y
reconstruir legalmente tecnologias propias, open-source o autorizadas. Opera
con Ceibo Core como cerebro conversacional, usa RAG
`ceibo_reverse_engineering`, adaptador planificado
`ceibo_reverse_engineering_qwen7b_lora` y guardrails de autorizacion,
propiedad intelectual, no evasion, no malware y clean-room.
