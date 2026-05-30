# Roadmap

## Fase 1 - Fundacion

- API FastAPI versionada.
- Registro de agentes.
- Docker Compose.
- Helm chart base.
- Health checks y metricas.
- Dashboard inicial.

## Fase 2 - Inteligencia operativa

- Integracion robusta OpenAI/Ollama/vLLM.
- Memoria RAG con Qdrant.
- Persistencia PostgreSQL para usuarios, sesiones, tareas y auditoria.
- NATS JetStream para workflows asincronicos.

Estado inicial implementado:

- Chat del dashboard conectado al CORE Orchestrator.
- Sesiones de chat con `session_id` y memoria reciente.
- Modelos SQLAlchemy para conversaciones, mensajes, tareas y auditoria.
- Persistencia/event bus opcionales en modo local y activos para Docker/Kubernetes.
- Publicacion de eventos base para chat y tareas cuando NATS esta habilitado.
- Cola operacional de tareas de agentes con fallback local.
- Endpoint de estado del CORE para dashboard y health operacional.
- Memoria RAG inicial con embeddings locales, OpenAI/Ollama-ready y Qdrant-ready.
- Endpoints `/api/v1/memory/health`, `/api/v1/memory/remember` y `/api/v1/memory/search`.
- CEIBO AI Engine local-first como provider por defecto (`ceibo_local`).
- Dataset JSONL y estructura `training/` para fine-tuning futuro.
- Catalogo de modelos base locales y planificador de entrenamiento LoRA/QLoRA.
- Camino separado para experimentos de entrenamiento desde cero con modelos pequenos.

## Fase 3 - Voz y automatizacion

- Whisper STT.
- Piper TTS.
- Wake word local.
- Playwright/Selenium.
- Control de SO con sandbox y aprobaciones.

## Fase 4 - Produccion

- OAuth2, RBAC y rate limiting.
- OpenTelemetry completo.
- Prometheus, Grafana, Loki.
- External Secrets/Vault.
- CI/CD.
- HPA/KEDA.

## Fase 5 - Multimodal y robotica

- Vision artificial.
- Agentes multimodales.
- Integracion con camaras/sensores.
- ROS2-ready.
- Workloads GPU para inferencia local.
