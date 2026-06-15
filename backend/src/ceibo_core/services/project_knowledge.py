from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectKnowledgeAnswer:
    topic: str
    answer: str
    evidence: list[str]
    next_steps: list[str]


class ProjectKnowledgeService:
    """Curated project knowledge for CEIBO chat answers.

    This is intentionally explicit instead of free-form RAG: it gives CEIBO a
    stable, auditable self-description while the project is still evolving.
    """

    capabilities = {
        "chat": "Chat central con motor local, memoria, reflexion cognitiva y router de herramientas.",
        "tools": "Herramientas de solo lectura para clima, hora, Git, Docker y estado del proyecto.",
        "devcore": "DevCore con parser de lenguaje controlado, plantillas, safety layer, sandbox, patch planner y apply gate.",
        "memory": "Memoria conversacional, memoria autobiografica y conocimiento del proyecto.",
        "learning": "Human Feedback Studio, learning loop, curacion, dataset expansion y evidencia de entrenamiento.",
        "evaluation": "Evaluation Loop, remediation planning, remediation apply gate y promotion gate.",
        "voice": "Control de voz inicial con frase de autorizacion y ruteo por politicas.",
        "training": "Preflight QLoRA, training runner, catalogo de modelos y registro de datasets/modelos.",
        "cognition": "Cognition state y Singularity Index para medir madurez tecnica.",
        "robotics": "Preparacion conceptual para robot: voz, vision, movimiento y accion fisica bajo gates.",
    }

    modules = {
        "backend": "FastAPI, agentes, servicios cognitivos, seguridad, memoria, entrenamiento y herramientas.",
        "frontend": "Workbench Next.js con chat, voz, paneles de sprints, dataset, evaluacion y DevCore.",
        "training": "Datasets, scripts, configuraciones QLoRA, expansion y artefactos revisables.",
        "docs": "Arquitectura, seguridad, DevCore, entrenamiento, Kubernetes y roadmap.",
        "infra": "Manifests base para despliegue e infraestructura futura.",
        "charts": "Helm chart para empaquetar CEIBO CORE en Kubernetes.",
    }

    sprint_map = {
        17: "Controlled Language Parser: intencion, parametros, riesgo y respuesta estructurada.",
        18: "Template Engine: plantillas seguras sin ejecucion automatica.",
        19: "Cyber Safety Layer: clasificacion de riesgo, politicas y bloqueos.",
        20: "Execution Sandbox: ejecucion controlada, confirmacion y auditoria.",
        21: "UI Workbench: chat central, interpretacion e historial sin sobrecargar.",
        22: "Patch Planner: plan de cambios sin aplicar.",
        23: "Patch Preview: mostrar plan, archivos, tests y diff preview.",
        24: "Apply Patch Gate: confirmacion, snapshot y rollback.",
        31: "Learning Loop: guardar feedback humano como aprendizaje.",
        32: "Learning Curation: puntuar, deduplicar y exportar dataset curado.",
        33: "Evaluation Loop: pruebas sobre seguridad, razonamiento, memoria, voz y codigo.",
        35: "Remediation Apply Gate: aplicar correcciones con evidencia.",
        39: "Training Evidence Builder: medir brechas antes de entrenar.",
        40: "Human Feedback Studio: corregir respuestas y guardar ejemplos buenos.",
        41: "Autobiographical Memory: objetivos, decisiones, preferencias y estado.",
        42: "Cognitive Reflection Loop: registrar que salio bien, que falto y que aprender.",
        43: "Dataset Expansion: generar 100-300 candidatos con gates y revision humana.",
        44: "Chat Tool Router: enrutar preguntas practicas a herramientas reales.",
        45: "Project Knowledge Answers: responder sobre proyecto, capacidades, modulos y sprints.",
    }

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or self._default_repo_root()

    def answer(self, message: str, context: list[str] | None = None) -> ProjectKnowledgeAnswer:
        normalized = message.lower()
        if self._asks_capabilities(normalized):
            return self._capabilities_answer()
        if self._asks_modules(normalized):
            return self._modules_answer()
        if self._asks_sprint(normalized):
            return self._sprint_answer(normalized)
        if self._asks_architecture(normalized):
            return self._architecture_answer()
        if self._asks_limits(normalized):
            return self._limits_answer()
        return self._overview_answer(context or [])

    def _asks_capabilities(self, message: str) -> bool:
        return any(term in message for term in ("capacidades", "que puede", "puede hacer", "funcionalidades"))

    def _asks_modules(self, message: str) -> bool:
        return any(term in message for term in ("modulos", "estructura", "carpetas", "partes"))

    def _asks_sprint(self, message: str) -> bool:
        return "sprint" in message or "en que estamos" in message or "que sigue" in message

    def _asks_architecture(self, message: str) -> bool:
        return any(term in message for term in ("arquitectura", "capas", "cognicion", "cerebro"))

    def _asks_limits(self, message: str) -> bool:
        return any(term in message for term in ("falta", "limites", "no tiene", "todavia no", "que falta"))

    def _overview_answer(self, context: list[str]) -> ProjectKnowledgeAnswer:
        robot_context = any("robot" in item.lower() for item in context)
        answer = (
            "CEIBO CORE es un sistema local-first para construir un nucleo cognitivo operativo: "
            "interpreta pedidos, recuerda decisiones, usa herramientas controladas, genera datos de "
            "entrenamiento, evalua respuestas y prepara ejecucion segura."
        )
        if robot_context:
            answer += " Su direccion de largo plazo es servir como logica y discernimiento para un futuro robot."
        return ProjectKnowledgeAnswer(
            topic="project_overview",
            answer=answer,
            evidence=[
                "Backend FastAPI con agentes, memoria, DevCore, training y evaluacion.",
                "Frontend Workbench con chat, voz, paneles de sprints y controles.",
                "Training pipeline con feedback humano, curacion, expansion y gates.",
            ],
            next_steps=[
                "Responder preguntas de proyecto desde esta base de conocimiento.",
                "Mantener evidencia actualizada al cerrar cada sprint.",
                "Conectar mas herramientas de solo lectura antes de habilitar acciones.",
            ],
        )

    def _capabilities_answer(self) -> ProjectKnowledgeAnswer:
        selected = [
            "chat",
            "tools",
            "devcore",
            "memory",
            "learning",
            "evaluation",
            "voice",
            "training",
            "cognition",
        ]
        answer = "Hoy CEIBO puede:\n" + "\n".join(
            f"- {self.capabilities[key]}" for key in selected
        )
        return ProjectKnowledgeAnswer(
            topic="project_capabilities",
            answer=answer,
            evidence=[
                "ChatToolRouter v1 enruta herramientas de solo lectura.",
                "Sprint 43 genero Dataset Expansion con quality gates.",
                "Sprints 31-42 agregaron aprendizaje, memoria y reflexion.",
            ],
            next_steps=[
                "Agregar respuestas mas finas por modulo o sprint.",
                "Conectar evidencia de tests y commits recientes.",
                "Preparar APIs para vision y movimiento cuando llegue la fase robotica.",
            ],
        )

    def _modules_answer(self) -> ProjectKnowledgeAnswer:
        answer = "La estructura principal es:\n" + "\n".join(
            f"- `{name}/`: {description}" for name, description in self.modules.items()
        )
        return ProjectKnowledgeAnswer(
            topic="project_modules",
            answer=answer,
            evidence=[
                "README.md declara backend, frontend, infra, charts, docs y scripts.",
                "Los servicios cognitivos viven en backend/src/ceibo_core/services.",
            ],
            next_steps=[
                "Si queres, puedo detallar un modulo especifico.",
                "El siguiente paso natural es documentar dependencias entre servicios.",
            ],
        )

    def _sprint_answer(self, message: str) -> ProjectKnowledgeAnswer:
        current = 45
        if "43" in message:
            current = 43
        elif "44" in message:
            current = 44
        elif "45" in message:
            current = 45
        answer = (
            f"El sprint consultado es Sprint {current}: {self.sprint_map[current]} "
            f"El siguiente paso recomendado es consolidar evidencia, tests y respuestas en chat."
        )
        return ProjectKnowledgeAnswer(
            topic="project_sprints",
            answer=answer,
            evidence=[
                f"Sprint {current}: {self.sprint_map[current]}",
                "Los sprints recientes cerrados incluyen Dataset Expansion y Chat Tool Router.",
            ],
            next_steps=[
                "Mantener cada sprint con tests, smoke real, commit y push.",
                "Despues de Sprint 45 conviene ampliar Knowledge Answers con lectura de commits y docs.",
            ],
        )

    def _architecture_answer(self) -> ProjectKnowledgeAnswer:
        answer = (
            "La arquitectura cognitiva actual separa percepcion, memoria, razonamiento, seguridad, accion, "
            "aprendizaje y modelo de si mismo. En codigo eso se materializa como chat/orquestador, servicios "
            "de memoria, DevCore parser, safety gates, sandbox, evaluation loop, dataset/training y cognition state."
        )
        return ProjectKnowledgeAnswer(
            topic="project_architecture",
            answer=answer,
            evidence=[
                "Cognition state mide capas como percepcion, memoria, razonamiento, seguridad, accion y aprendizaje.",
                "DevCore controla interpretacion, planificacion, safety y aplicacion de patches.",
            ],
            next_steps=[
                "Agregar mapa visual de dependencias entre servicios.",
                "Conectar esta arquitectura con APIs futuras de voz, vision y movimiento.",
            ],
        )

    def _limits_answer(self) -> ProjectKnowledgeAnswer:
        return ProjectKnowledgeAnswer(
            topic="project_limits",
            answer=(
                "A CEIBO todavia le falta un modelo fundacional propio entrenado con suficiente evidencia, "
                "mas evaluaciones duras, memoria mas curada, herramientas de proyecto mas profundas y APIs "
                "reales para vision/movimiento. Ya es un sistema local operativo, pero no una mente humana ni AGI."
            ),
            evidence=[
                "El entrenamiento local aun esta en preflight/gates.",
                "Las herramientas actuales son mayormente de solo lectura.",
                "La capa robotica todavia es preparatoria.",
            ],
            next_steps=[
                "Curar ejemplos humanos de alta calidad.",
                "Expandir evaluaciones sobre robotica, seguridad, memoria y decisiones.",
                "Comparar respuestas antes/despues de fine-tune pequeño.",
            ],
        )

    def _default_repo_root(self) -> Path:
        return Path(__file__).resolve().parents[4]


project_knowledge_service = ProjectKnowledgeService()
