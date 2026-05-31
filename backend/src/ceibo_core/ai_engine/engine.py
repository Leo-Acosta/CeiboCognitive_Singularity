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
        IntentRule("devcore_modify", ("endpoint", "fastapi", "implementar", "agregar", "crear", "create", "fix")),
        IntentRule("weather", ("clima", "tiempo", "temperatura", "pronostico")),
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
        parser_context = next((item for item in context if item.startswith("DevCore parse:")), "")
        if "intent=create_endpoint" in parser_context:
            focus = "endpoint backend"
            answer = (
                "Interprete esto como una solicitud para crear o modificar un endpoint. "
                "No conviene avanzar directo a codigo hasta fijar el contrato minimo: metodo, "
                "ruta, entrada, salida esperada y tests que validen el comportamiento."
            )
            next_steps = [
                "Definir la ruta exacta del endpoint si todavia no esta indicada.",
                "Confirmar metodo HTTP, payload esperado y respuesta.",
                "Luego generar el cambio FastAPI y su test enfocado.",
            ]
        elif "devcore_modify" in intents or "intent=modify_code" in parser_context:
            focus = "cambio de codigo"
            answer = (
                "Entendi que queres modificar el proyecto, no solo inspeccionarlo. Para ese caso "
                "lo correcto es armar primero un plan de cambio acotado: identificar archivos, "
                "definir contrato del endpoint o componente, implementar y verificar con tests."
            )
            next_steps = [
                "Confirmar el objetivo exacto del cambio y el modulo afectado.",
                "Proponer archivos a tocar y contrato esperado.",
                "Aplicar cambios pequenos y correr la verificacion correspondiente.",
            ]
        elif "weather" in intents:
            focus = "consulta de clima"
            answer = (
                "Ahora mismo CEIBO no tiene conectado un proveedor de clima en tiempo real. "
                "Puedo interpretar la solicitud, pero para responder temperatura o pronostico "
                "necesitamos integrar una API de clima o habilitar una herramienta externa."
            )
            next_steps = [
                "Agregar un proveedor de clima configurable.",
                "Pedir ciudad o ubicacion cuando no este definida.",
                "Responder con fuente, hora de consulta y unidades.",
            ]
        elif "training" in intents:
            focus = "entrenamiento local"
            answer = (
                "CEIBO esta listo para preparar entrenamiento local. El camino practico es "
                "curar ejemplos propios en JSONL, versionar el dataset, ejecutar un preflight "
                "QLoRA y recien despues lanzar pruebas cortas de fine-tuning."
            )
            next_steps = [
                "Revisar calidad y duplicados del dataset.",
                "Elegir modelo base segun RAM/VRAM disponible.",
                "Correr preflight antes de iniciar cualquier entrenamiento.",
            ]
        elif "memory" in intents:
            focus = "memoria y contexto"
            answer = (
                "La memoria de CEIBO esta preparada para combinar historial reciente con busqueda "
                "semantica. El objetivo es que el chat recuerde decisiones utiles sin arrastrar "
                "ruido de conversaciones anteriores."
            )
            next_steps = [
                "Definir que datos se guardan como memoria estable.",
                "Separar memoria conversacional de conocimiento del proyecto.",
                "Agregar controles para olvidar o depurar contexto.",
            ]
        elif "infrastructure" in intents:
            focus = "infraestructura"
            answer = (
                "La infraestructura local esta operativa con Docker Compose. El siguiente nivel es "
                "hacer que CEIBO pueda diagnosticar servicios, leer estado, proponer acciones y "
                "pedir confirmacion antes de cualquier cambio."
            )
            next_steps = [
                "Mantener healthchecks claros para API, frontend y dependencias.",
                "Exponer logs y estado de contenedores desde una capa controlada.",
                "Preparar plantillas seguras para tareas repetibles.",
            ]
        elif "automation" in intents:
            focus = "automatizacion"
            answer = (
                "CEIBO puede evolucionar hacia automatizacion, pero debe hacerlo con una capa de "
                "interpretacion, validacion de riesgo y confirmacion humana. Primero se genera un "
                "plan, despues codigo o comandos, y solo al final se habilita ejecucion controlada."
            )
            next_steps = [
                "Clasificar la intencion del usuario.",
                "Generar comandos o codigo sin ejecutarlos automaticamente.",
                "Registrar auditoria y requerir confirmacion para acciones sensibles.",
            ]
        elif "security" in intents:
            focus = "seguridad"
            answer = (
                "La linea correcta para CEIBO es seguridad defensiva: auditoria, politicas, RBAC, "
                "sandboxing y bloqueo de acciones peligrosas. Cualquier capacidad cyber debe quedar "
                "acotada a laboratorio propio y uso no ofensivo."
            )
            next_steps = [
                "Crear una politica explicita de laboratorio permitido.",
                "Clasificar solicitudes por riesgo antes de generar acciones.",
                "Aplicar doble confirmacion para tareas delicadas.",
            ]
        else:
            focus = "estado general"
            answer = (
                "CEIBO CORE esta online y funcionando en modo local inicial. La API, el chat, "
                "la memoria base y la orquestacion estan disponibles para seguir construyendo "
                "capacidades mas avanzadas."
            )
            next_steps = [
                "Pulir el flujo principal de chat.",
                "Definir las capacidades DevCore que se van a activar primero.",
                "Conectar un modelo mas potente cuando quieras mejorar razonamiento.",
            ]

        memory_note = (
            "Use contexto reciente para mantener continuidad."
            if context
            else "No necesite memoria previa para esta respuesta."
        )
        steps = "\n".join(f"- {step}" for step in next_steps)
        return (
            f"{answer}\n\n"
            f"Foco: {focus}.\n"
            f"{memory_note}\n\n"
            f"Siguientes pasos recomendados:\n{steps}"
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
