from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Iterable

from ceibo_core.core.config import settings
from ceibo_core.models.schemas import (
    DialogueAnalysis,
    DialogueOrchestrationTrace,
    DialogueOrchestratorResponse,
    DialogueSignal,
)
from ceibo_core.services.chat_tools import ChatToolResult, chat_tool_router
from ceibo_core.services.dialogue_memory import dialogue_memory_service
from ceibo_core.services.llm_gateway import llm_gateway
from ceibo_core.services.persona import build_persona_prompt
from ceibo_core.security.safety_supervisor import safety_supervisor


@dataclass(frozen=True)
class DialogueRoute:
    intent: str
    cognitive_route: str
    speech_act: str
    response_style: str
    reason: str
    needs: tuple[str, ...]


class DialogueOrchestratorService:
    """Fast cognitive front-door for human conversation.

    The service does not pretend to solve consciousness. It gives CEIBO a stable
    dialogue loop: understand, route, answer, trace. The analysis is local and
    deterministic so the user gets low-latency behavior even when a model is slow
    or unavailable.
    """

    route_rules = (
        DialogueRoute(
            intent="technical_build",
            cognitive_route="devcore_reasoning",
            speech_act="request",
            response_style="precise_actionable",
            reason="El usuario pide construir, modificar o diagnosticar software.",
            needs=("objetivo", "restricciones", "verificacion"),
        ),
        DialogueRoute(
            intent="self_understanding",
            cognitive_route="project_cognition",
            speech_act="question",
            response_style="reflective_clear",
            reason="El usuario pregunta por CEIBO, su estado, capacidades o identidad.",
            needs=("estado_actual", "limites", "siguiente_paso"),
        ),
        DialogueRoute(
            intent="emotional_dialogue",
            cognitive_route="human_dialogue",
            speech_act="conversation",
            response_style="warm_brief",
            reason="El usuario busca charla, acompaniamiento o continuidad humana.",
            needs=("tono", "continuidad", "pregunta_suave"),
        ),
        DialogueRoute(
            intent="training_growth",
            cognitive_route="learning_and_training",
            speech_act="request",
            response_style="structured_coach",
            reason="El usuario habla de entrenamiento, dataset, aprendizaje o fine-tuning.",
            needs=("dataset", "evaluacion", "preflight"),
        ),
        DialogueRoute(
            intent="robot_embodiment",
            cognitive_route="embodied_interface",
            speech_act="request",
            response_style="systems_architect",
            reason="El usuario conecta CEIBO con voz, robot, sensores o movimiento.",
            needs=("seguridad_fisica", "interfaces", "simulacion"),
        ),
    )

    async def respond(
        self,
        *,
        user_message: str,
        conversation_history: list[dict] | None = None,
        memory_context: str | None = None,
        mode: str = "human_persona",
    ) -> DialogueOrchestratorResponse:
        started = perf_counter()
        safety_class = safety_supervisor.classify(user_message)
        analysis = self.analyze(user_message, safety_class=safety_class)

        if safety_class == "blocked_abuse":
            return self._direct_response(
                response=(
                    f"{settings.ceibo_user_name}, no puedo ayudar con una accion de dano real. "
                    "Si queres, puedo llevarlo a un analisis defensivo, educativo o de laboratorio controlado."
                ),
                analysis=analysis,
                selected_module="safety_supervisor",
                started=started,
            )
        if safety_class == "sensitive_requires_confirmation":
            return self._direct_response(
                response=(
                    f"{settings.ceibo_user_name}, eso toca una zona sensible. "
                    "Puedo analizarlo primero en modo seguro, sin ejecutar nada, y despues pedir confirmacion exacta."
                ),
                analysis=analysis,
                selected_module="safety_supervisor",
                started=started,
            )

        memory_ctx = memory_context or await dialogue_memory_service.get_relevant_memory_context(user_message)
        tool_result = None
        if self._should_use_tool_router(analysis):
            tool_result = await chat_tool_router.route(
                user_message,
                self._history_to_context(conversation_history, memory_ctx),
            )
        if tool_result is not None:
            return self._direct_response(
                response=self._compose_tool_dialogue(tool_result, analysis),
                analysis=analysis.model_copy(
                    update={
                        "tool_candidate": tool_result.tool_name,
                        "cognitive_route": "tool_augmented_dialogue",
                    }
                ),
                selected_module="chat_tool_router",
                started=started,
                tool_used=tool_result.tool_name,
            )

        if self._should_answer_human_locally(analysis):
            return self._direct_response(
                response=self._compose_human_dialogue(user_message, analysis),
                analysis=analysis,
                selected_module=analysis.cognitive_route,
                started=started,
            )

        messages = self._build_messages(
            user_message=user_message,
            conversation_history=conversation_history or [],
            memory_context=memory_ctx,
            analysis=analysis,
            mode=mode,
        )
        response = await llm_gateway.chat(
            messages=messages,
            temperature=self._temperature_for(analysis),
            max_tokens=700,
        )
        fallback_used = self._looks_like_gateway_error(response)
        if fallback_used:
            response = self._fallback_response(user_message, analysis, memory_ctx)
        response = self._polish(response, analysis)

        if self._should_remember_preference(user_message):
            await dialogue_memory_service.remember(
                kind="relationship_memory",
                title="Preferencia conversacional del usuario",
                content=user_message,
                importance=80,
                tags=["dialogue", "preference", settings.ceibo_user_name.lower()],
            )

        return DialogueOrchestratorResponse(
            response=response,
            trace=DialogueOrchestrationTrace(
                analysis=analysis,
                selected_module=analysis.cognitive_route,
                provider=settings.default_llm_provider,
                latency_ms=self._elapsed_ms(started),
                fallback_used=fallback_used,
                safety_checked=True,
            ),
        )

    def analyze(self, message: str, *, safety_class: str = "normal") -> DialogueAnalysis:
        normalized = self._normalize(message)
        route = self._select_route(normalized)
        tone = self._tone(normalized)
        ambiguity = self._ambiguity(normalized)
        irony = self._irony(normalized)
        urgency = self._urgency(normalized)
        confidence = max(0.35, min(0.95, 0.82 - ambiguity * 0.25 + len(route.needs) * 0.01))
        signals = [
            DialogueSignal(name="message_length", value=len(message), confidence=1),
            DialogueSignal(name="ambiguity", value=round(ambiguity, 2), confidence=0.75),
            DialogueSignal(name="irony", value=round(irony, 2), confidence=0.55),
            DialogueSignal(name="urgency", value=round(urgency, 2), confidence=0.7),
        ]
        return DialogueAnalysis(
            intent=route.intent,
            cognitive_route=route.cognitive_route,
            speech_act=route.speech_act,
            emotional_tone=tone,
            response_style=route.response_style,
            safety_class=safety_class,
            memory_policy=self._memory_policy(normalized),
            ambiguity_score=ambiguity,
            irony_likelihood=irony,
            urgency_score=urgency,
            confidence=confidence,
            route_reason=route.reason,
            inferred_needs=list(route.needs),
            signals=signals,
        )

    def _select_route(self, normalized: str) -> DialogueRoute:
        if self._is_practical_tool_request(normalized):
            return DialogueRoute(
                intent="practical_tool_query",
                cognitive_route="tool_query",
                speech_act="question",
                response_style="direct_with_source",
                reason="El usuario pide informacion externa o estado local que debe resolverse con herramienta.",
                needs=("herramienta", "fuente", "respuesta_breve"),
            )
        if self._contains(
            normalized,
            (
                "hola",
                "como estas",
                "charlemos",
                "conversemos",
                "conversar",
                "dialogo",
                "naturalidad",
                "ironia",
                "ironias",
                "siento",
                "pienso",
            ),
        ):
            return self.route_rules[2]
        if self._contains(normalized, ("endpoint", "fastapi", "codigo", "bug", "test", "commit", "docker", "frontend")):
            return self.route_rules[0]
        if self._contains(normalized, ("que sos", "quien sos", "ceibo", "proyecto", "cognicion", "singularidad", "estado")):
            return self.route_rules[1]
        if self._contains(normalized, ("entren", "dataset", "qlora", "fine tune", "aprende", "learning")):
            return self.route_rules[3]
        if self._contains(normalized, ("robot", "voz", "vision", "movimiento", "sensor", "hablar", "escuchar")):
            return self.route_rules[4]
        return DialogueRoute(
            intent="general_dialogue",
            cognitive_route="general_reasoning",
            speech_act="conversation",
            response_style="clear_natural",
            reason="No hay una ruta especializada dominante; se responde con razonamiento general.",
            needs=("entender_pedido", "responder_directo"),
        )

    def _should_use_tool_router(self, analysis: DialogueAnalysis) -> bool:
        return analysis.cognitive_route != "human_dialogue"

    def _should_answer_human_locally(self, analysis: DialogueAnalysis) -> bool:
        return analysis.cognitive_route == "human_dialogue"

    def _build_messages(
        self,
        *,
        user_message: str,
        conversation_history: list[dict],
        memory_context: str,
        analysis: DialogueAnalysis,
        mode: str,
    ) -> list[dict]:
        system_prompt = build_persona_prompt(memory_context=self._trim(memory_context, 1800), mode=mode)
        cognitive_prompt = (
            "Capa de dialogo CEIBO:\n"
            f"- intencion: {analysis.intent}\n"
            f"- ruta cognitiva: {analysis.cognitive_route}\n"
            f"- tono humano detectado: {analysis.emotional_tone}\n"
            f"- estilo de respuesta: {analysis.response_style}\n"
            f"- ironia probable: {analysis.irony_likelihood:.2f}\n"
            f"- ambiguedad: {analysis.ambiguity_score:.2f}\n"
            "Reglas: responde natural, sin sonar mecanico; si hay ambiguedad, hace una sola pregunta breve; "
            "si hay ironia, no la tomes literal de inmediato; si el usuario pide accion, primero razona y acota riesgo."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": cognitive_prompt},
        ]
        for item in conversation_history[-6:]:
            role = item.get("role", "user")
            if role not in {"user", "assistant"}:
                continue
            messages.append({"role": role, "content": self._trim(item.get("content", ""), 900)})
        messages.append({"role": "user", "content": user_message})
        return messages

    def _compose_tool_dialogue(self, result: ChatToolResult, analysis: DialogueAnalysis) -> str:
        steps = "\n".join(f"- {step}" for step in result.next_steps[:4])
        if result.status in {"needs_details", "needs_preference", "missing_location", "missing_symbol"}:
            return f"{result.answer}\n\nPara seguir sin adivinar:\n{steps}"
        return f"{result.answer}\n\nNotas utiles:\n{steps}"

    def _compose_human_dialogue(self, message: str, analysis: DialogueAnalysis) -> str:
        parts = [
            "Si. Puedo conversar con vos de una forma mas natural: menos informe, mas presencia, y con mejor lectura del tono.",
            "Voy a tratar cada mensaje como algo humano antes que como una orden seca: intencion, contexto, emocion, ambiguedad e ironia posible.",
        ]
        if analysis.irony_likelihood >= 0.45 or self._contains(self._normalize(message), ("ironia", "ironias", "sarcasmo")):
            parts.append(
                "Si aparece ironia, no la voy a tomar literal de entrada; primero voy a mirar si hay critica, humor o cansancio detras."
            )
        parts.append("Decime algo como se lo dirias a una persona, y yo te respondo desde ahi.")
        return "\n\n".join(parts)

    def _fallback_response(self, message: str, analysis: DialogueAnalysis, memory_context: str) -> str:
        if analysis.intent == "emotional_dialogue":
            return (
                f"Estoy aca, {settings.ceibo_user_name}. Te sigo el hilo: "
                "decime que queres pensar o construir y lo ordeno con vos sin hacerlo pesado."
            )
        if analysis.intent == "technical_build":
            return (
                "Lo interpreto como trabajo tecnico. Primero separaria objetivo, archivos afectados, riesgo y tests. "
                "Despues recien prepararia un cambio chico y verificable."
            )
        if analysis.intent == "training_growth":
            return (
                "Para mejorar mi cognicion, el camino correcto es experiencia corregida: ejemplos reales, "
                "curacion, evaluacion, preflight y recien despues fine-tune corto."
            )
        if analysis.intent == "robot_embodiment":
            return (
                "Para llevar CEIBO a un robot, separaria mente, percepcion, voz, movimiento y seguridad fisica. "
                "Primero simularia ordenes; despues habilitaria actuadores con confirmacion."
            )
        context_note = " Tengo contexto previo disponible." if memory_context else ""
        return f"Te entiendo.{context_note} Puedo responderlo mejor si lo enfocamos en una decision concreta."

    def _polish(self, response: str, analysis: DialogueAnalysis) -> str:
        cleaned = (response or "").strip()
        if not cleaned:
            return self._fallback_response("", analysis, "")
        if analysis.irony_likelihood >= 0.55 and "?" not in cleaned[:160]:
            cleaned += "\n\nSi lo dijiste con ironia, lo tomo: puedo leerlo en tono literal o en tono critico, como prefieras."
        if analysis.ambiguity_score >= 0.65 and cleaned.count("?") == 0:
            cleaned += "\n\nPara afinarlo: queres que lo piense como charla, como arquitectura o como implementacion?"
        return cleaned

    def _direct_response(
        self,
        *,
        response: str,
        analysis: DialogueAnalysis,
        selected_module: str,
        started: float,
        tool_used: str | None = None,
    ) -> DialogueOrchestratorResponse:
        return DialogueOrchestratorResponse(
            response=response,
            trace=DialogueOrchestrationTrace(
                analysis=analysis,
                selected_module=selected_module,
                tool_used=tool_used,
                provider="ceibo_dialogue_orchestrator",
                latency_ms=self._elapsed_ms(started),
                fallback_used=False,
                safety_checked=True,
            ),
        )

    def _history_to_context(self, history: list[dict] | None, memory_context: str) -> list[str]:
        context = [memory_context] if memory_context else []
        for item in (history or [])[-4:]:
            content = item.get("content")
            if content:
                context.append(str(content))
        return context

    def _tone(self, normalized: str) -> str:
        if self._contains(normalized, ("gracias", "perfecto", "bien", "excelente")):
            return "positivo_colaborativo"
        if self._contains(normalized, ("mal", "no funciona", "frustr", "cansado", "preocup")):
            return "frustracion_o_preocupacion"
        if self._contains(normalized, ("jaja", "jeje", "sarcas", "ironia", "claro seguro")):
            return "humor_o_ironia"
        return "neutral_atento"

    def _ambiguity(self, normalized: str) -> float:
        vague = sum(1 for token in ("eso", "esto", "algo", "cosa", "mejor", "arreglalo", "continua") if token in normalized)
        question = 0 if any(token in normalized for token in ("que", "como", "cuando", "donde", "por que", "cual")) else 1
        return min(1.0, vague * 0.18 + question * 0.18)

    def _irony(self, normalized: str) -> float:
        markers = ("ironia", "sarcasmo", "claro seguro", "si, claro", "genial...", "buenisimo...")
        score = 0.65 if self._contains(normalized, markers) else 0.0
        if "jaja" in normalized or "jeje" in normalized:
            score += 0.15
        return min(1.0, score)

    def _urgency(self, normalized: str) -> float:
        markers = ("urgente", "ya", "ahora", "rapido", "inmediato", "se rompio")
        return min(1.0, sum(1 for marker in markers if marker in normalized) * 0.2)

    def _is_practical_tool_request(self, normalized: str) -> bool:
        return self._contains(
            normalized,
            (
                "clima",
                "temperatura",
                "pronostico",
                "llover",
                "llueve",
                "lluvia",
                "estado del tiempo",
                "que hora",
                "hora es",
                "fecha",
                "que dia",
                "dolar",
                "usd",
                "euro",
                "cotizacion",
                "acciones",
                "stock",
                "ticker",
                "cartelera",
                "cine",
                "teatro",
                "pasaje",
                "pasajes",
                "vuelo",
                "vuelos",
                "docker",
                "contenedor",
                "git",
            ),
        )

    def _memory_policy(self, normalized: str) -> str:
        if self._contains(normalized, ("prefiero", "recorda", "recuerda", "mi objetivo", "decision")):
            return "candidate_autobiographical_memory"
        if self._contains(normalized, ("no recuerdes", "olvida", "borra")):
            return "forget_or_do_not_store"
        return "short_term_context"

    def _temperature_for(self, analysis: DialogueAnalysis) -> float:
        if analysis.response_style in {"warm_brief", "reflective_clear"}:
            return 0.65
        if analysis.response_style in {"precise_actionable", "systems_architect"}:
            return 0.35
        return 0.5

    def _looks_like_gateway_error(self, response: str) -> bool:
        lowered = (response or "").lower()
        return any(
            marker in lowered
            for marker in (
                "ollama no parece",
                "tiempo de espera agotado",
                "error al comunicarse",
                "proveedor de llm",
                "fallo al generar",
                "fallÃ³ al generar",
            )
        )

    def _should_remember_preference(self, message: str) -> bool:
        normalized = self._normalize(message)
        return self._contains(normalized, ("prefiero", "me gusta que", "recorda que", "recuerda que"))

    def _elapsed_ms(self, started: float) -> int:
        return int((perf_counter() - started) * 1000)

    def _trim(self, value: str, limit: int) -> str:
        value = value or ""
        return value if len(value) <= limit else value[-limit:]

    def _normalize(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def _contains(self, value: str, needles: Iterable[str]) -> bool:
        return any(needle in value for needle in needles)


dialogue_orchestrator_service = DialogueOrchestratorService()
