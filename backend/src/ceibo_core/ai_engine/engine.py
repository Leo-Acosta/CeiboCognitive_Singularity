from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ceibo_core.core.config import settings
from ceibo_core.models.schemas import EngineGenerateResponse, EngineStatus


@dataclass(frozen=True)
class IntentRule:
    name: str
    keywords: tuple[str, ...]


class CeiboAIEngine:
    """Local-first CEIBO reasoning engine.

    This is the first native layer: deterministic, inspectable, trainable later.
    It does not require OpenAI, Ollama, or any external provider.
    """

    rules = (
        IntentRule("architecture", ("arquitectura", "sistema", "microservicio", "modular")),
        IntentRule("memory", ("memoria", "rag", "qdrant", "recordar", "contexto")),
        IntentRule("automation", ("automatiza", "workflow", "script", "playwright", "selenium")),
        IntentRule("infrastructure", ("kubernetes", "docker", "deploy", "cluster", "logs")),
        IntentRule("security", ("seguridad", "hardening", "siem", "auditoria", "rbac")),
        IntentRule("training", ("entrenar", "fine-tuning", "dataset", "lora", "qlora")),
        IntentRule("voice", ("voz", "whisper", "tts", "wake word", "piper")),
    )

    def status(self) -> EngineStatus:
        return EngineStatus(
            model_id=settings.ceibo_engine_model_id,
            mode=settings.ceibo_engine_mode,
            provider="ceibo_local",
            trainable=True,
            local_first=True,
            dataset_path=settings.ceibo_training_dataset_path,
            core_directive=settings.ceibo_core_directive,
        )

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: list[str] | None = None,
    ) -> EngineGenerateResponse:
        context = context or self._extract_context(system_prompt)
        intents = self._detect_intents(user_message)
        response = self._compose_response(user_message=user_message, intents=intents, context=context)
        return EngineGenerateResponse(
            response=response,
            model_id=settings.ceibo_engine_model_id,
            mode=settings.ceibo_engine_mode,
            intents=intents,
            used_context=bool(context),
            created_at=datetime.now(UTC),
        )

    def _detect_intents(self, message: str) -> list[str]:
        normalized = message.lower()
        intents = [
            rule.name
            for rule in self.rules
            if any(keyword in normalized for keyword in rule.keywords)
        ]
        return intents or ["general"]

    def _compose_response(self, user_message: str, intents: list[str], context: list[str]) -> str:
        intent_line = ", ".join(intents)
        if "training" in intents:
            core = (
                "CEIBO AI Engine local activo. Para convertir esto en una IA entrenada, "
                "el siguiente paso es alimentar datasets propios en formato JSONL, elegir un "
                "modelo base local y preparar fine-tuning LoRA/QLoRA."
            )
        elif "memory" in intents:
            core = (
                "CEIBO AI Engine local activo. La memoria ya opera con embeddings locales, "
                "busqueda semantica y adaptador Qdrant-ready para usar vector DB cuando este disponible."
            )
        elif "infrastructure" in intents:
            core = (
                "CEIBO AI Engine local activo. Puedo planificar tareas de Docker, Kubernetes, logs "
                "y despliegues mediante agentes especializados y cola operacional."
            )
        elif "automation" in intents:
            core = (
                "CEIBO AI Engine local activo. La automatizacion debe pasar por agentes y politicas "
                "de seguridad antes de ejecutar scripts, navegador o escritorio."
            )
        elif "security" in intents:
            core = (
                "CEIBO AI Engine local activo. Para seguridad, priorizo monitoreo defensivo, auditoria, "
                "RBAC, sandboxing y trazabilidad de acciones."
            )
        else:
            core = (
                "CEIBO AI Engine local activo. Estoy respondiendo desde el motor propio inicial, "
                "sin depender de OpenAI. Esta capa sera la base para entrenamiento local posterior."
            )

        if context:
            context_preview = " | ".join(item[:120] for item in context[-3:])
            return (
                f"{core}\n\nDirectiva: {settings.ceibo_core_directive}\n"
                f"Intencion detectada: {intent_line}.\n"
                f"Contexto usado: {context_preview}\n"
                f"Mensaje recibido: {user_message}"
            )
        return (
            f"{core}\n\nDirectiva: {settings.ceibo_core_directive}\n"
            f"Intencion detectada: {intent_line}.\nMensaje recibido: {user_message}"
        )

    @staticmethod
    def _extract_context(system_prompt: str) -> list[str]:
        marker = "Contexto reciente recuperado:"
        if marker not in system_prompt:
            return []
        context_block = system_prompt.split(marker, maxsplit=1)[1]
        return [
            line.removeprefix("- ").strip()
            for line in context_block.splitlines()
            if line.strip().startswith("- ")
        ]


ceibo_engine = CeiboAIEngine()
