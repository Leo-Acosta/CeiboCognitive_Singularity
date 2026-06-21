from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ceibo_core.models.schemas import (
    AutobiographicalMemoryRequest,
    CognitiveReflectionRecord,
    CognitiveReflectionRequest,
    CognitiveReflectionState,
)
from ceibo_core.services.autobiographical_memory import autobiographical_memory_service
from ceibo_core.services.memory import sanitize_memory_text
from ceibo_core.services.training_data import training_data_service


class CognitiveReflectionService:
    def __init__(self, path: Path | None = None, autobiography_service=None) -> None:
        self._path_override = path
        self._autobiography_service = autobiography_service or autobiographical_memory_service

    def reflection_path(self) -> Path:
        if self._path_override is not None:
            return self._path_override
        return training_data_service.project_root() / "training" / "reflections" / "cognitive_reflections.jsonl"

    async def reflect_after_response(
        self,
        request: CognitiveReflectionRequest,
    ) -> CognitiveReflectionRecord:
        record = self._build_reflection(request)
        self._append(record)
        memory = record.recommended_memory
        if memory is not None:
            await self._autobiography_service.remember(memory)
        return record

    async def state(self, limit: int = 8) -> CognitiveReflectionState:
        records = self._read_records()
        recent = records[-limit:]
        latest = records[-1] if records else None
        average_score = round(sum(item.score for item in records) / len(records), 1) if records else 0
        missing = Counter(item for record in records for item in record.missing)
        learning = Counter(item for record in records for item in record.should_learn)
        warnings: list[str] = []
        if not records:
            warnings.append("Todavia no hay reflexiones internas guardadas.")
        elif average_score < 65:
            warnings.append("La calidad promedio de reflexion indica respuestas que necesitan mas contexto o verificacion.")
        if missing:
            warnings.append(f"Patron recurrente a mejorar: {missing.most_common(1)[0][0]}")

        return CognitiveReflectionState(
            status="reflection_loop_active" if records else "reflection_loop_empty",
            summary=self._summary(records, average_score),
            reflection_path=str(self.reflection_path()),
            total_reflections=len(records),
            average_score=average_score,
            latest_reflection=latest,
            recent_reflections=list(reversed(recent)),
            recurring_missing=dict(missing.most_common(6)),
            recurring_learning=dict(learning.most_common(6)),
            warnings=warnings,
            next_actions=[
                "Revisar patrones missing antes de expandir dataset.",
                "Convertir buenas correcciones en ejemplos del Human Feedback Studio.",
                "Persistir decisiones de proyecto como memoria autobiografica.",
            ],
        )

    def _build_reflection(self, request: CognitiveReflectionRequest) -> CognitiveReflectionRecord:
        prompt, prompt_redacted = sanitize_memory_text(request.prompt)
        response, response_redacted = sanitize_memory_text(request.response)
        did_well = self._did_well(request, response)
        missing = self._missing(request, response)
        should_learn = self._should_learn(request, response, missing)
        score = self._score(did_well, missing, request.used_context)
        metadata = {**request.metadata}
        if prompt_redacted or response_redacted:
            metadata["redacted"] = True
        recommended_memory = self._recommended_memory(prompt, response, request, missing)
        return CognitiveReflectionRecord(
            prompt=prompt[:280],
            response_preview=response[:360],
            source=request.source,
            user_id=request.user_id,
            session_id=request.session_id,
            score=score,
            did_well=did_well,
            missing=missing,
            should_learn=should_learn,
            recommended_memory=recommended_memory,
            tags=self._tags(request, missing, should_learn),
            metadata=metadata,
            created_at=datetime.now(UTC),
        )

    def _did_well(self, request: CognitiveReflectionRequest, response: str) -> list[str]:
        strengths: list[str] = []
        trace = self._dialogue_trace(request)
        analysis = trace.get("analysis", {}) if trace else {}
        emotional = self._emotional_trace(request)
        if len(response) >= 160:
            strengths.append("Respondio con suficiente desarrollo inicial.")
        if "Siguientes pasos recomendados" in response or "siguiente" in response.lower():
            strengths.append("Incluyo orientacion accionable.")
        if request.used_context or request.memory_context:
            strengths.append("Uso contexto recuperado para continuidad.")
        if any(intent in request.intents for intent in ("security", "devcore_modify", "training")):
            strengths.append("Detecto una intencion tecnica relevante.")
        if analysis.get("cognitive_route"):
            strengths.append(f"Orquesto la respuesta por ruta cognitiva {analysis['cognitive_route']}.")
        if trace.get("tool_used"):
            strengths.append(f"Uso herramienta controlada {trace['tool_used']} cuando correspondia.")
        if analysis.get("safety_class") and analysis.get("safety_class") != "normal":
            strengths.append("Ejecuto control de seguridad antes de responder.")
        if emotional.get("recommended_response_style"):
            strengths.append(f"Considero estado emocional conversacional {emotional['primary_state']}.")
        return strengths or ["Genero una respuesta util para continuar la conversacion."]

    def _missing(self, request: CognitiveReflectionRequest, response: str) -> list[str]:
        missing: list[str] = []
        lowered = response.lower()
        trace = self._dialogue_trace(request)
        analysis = trace.get("analysis", {}) if trace else {}
        emotional = self._emotional_trace(request)
        if not request.used_context and not request.memory_context:
            missing.append("No uso memoria o contexto previo.")
        if "test" not in lowered and any(intent in request.intents for intent in ("devcore_modify", "training")):
            missing.append("No explicito verificacion o tests.")
        if "riesgo" not in lowered and any(intent in request.intents for intent in ("security", "automation", "devcore_modify")):
            missing.append("No explicito clasificacion de riesgo.")
        if len(response) < 120:
            missing.append("Respuesta demasiado breve para aprender de ella.")
        if "robot" in request.prompt.lower() and "robot" not in lowered:
            missing.append("No conecto la respuesta con el objetivo robotico del proyecto.")
        if analysis.get("ambiguity_score", 0) >= 0.65 and "?" not in response:
            missing.append("La traza marco ambiguedad alta pero la respuesta no pidio precision.")
        if analysis.get("irony_likelihood", 0) >= 0.55 and "ironia" not in lowered and "tono" not in lowered:
            missing.append("La traza marco ironia posible pero la respuesta no reflejo tono.")
        if analysis.get("cognitive_route") == "tool_query" and not trace.get("tool_used"):
            missing.append("La traza esperaba herramienta pero no quedo herramienta registrada.")
        if (
            emotional.get("should_offer_step_by_step")
            and "paso" not in lowered
            and "orden" not in lowered
            and "primero" not in lowered
        ):
            missing.append("La capa emocional sugirio paso a paso pero la respuesta no lo reflejo.")
        return missing

    def _should_learn(
        self,
        request: CognitiveReflectionRequest,
        response: str,
        missing: list[str],
    ) -> list[str]:
        learning: list[str] = []
        if missing:
            learning.extend(f"Mejorar: {item}" for item in missing[:3])
        trace = self._dialogue_trace(request)
        analysis = trace.get("analysis", {}) if trace else {}
        emotional = self._emotional_trace(request)
        route = analysis.get("cognitive_route")
        if route == "human_dialogue":
            learning.append("Aprender patrones de dialogo humano: tono, continuidad, ironia y pregunta suave.")
        if trace.get("tool_used"):
            learning.append(f"Reforzar en dataset cuando usar {trace['tool_used']} y cuando no usar herramienta.")
        if analysis.get("memory_policy") == "candidate_autobiographical_memory":
            learning.append("Convertir preferencias u objetivos del usuario en memoria autobiografica curada.")
        if emotional.get("primary_state") and emotional.get("primary_state") != "neutral":
            learning.append("Usar estado emocional conversacional solo para adaptar la respuesta actual.")
        if emotional.get("should_avoid_memory"):
            learning.append("No convertir emociones momentaneas en memoria autobiografica.")
        if "decision" in request.prompt.lower() or "objetivo" in request.prompt.lower():
            learning.append("Guardar decisiones y objetivos importantes como memoria autobiografica.")
        if any(intent in request.intents for intent in ("training", "devcore_modify")):
            learning.append("Crear ejemplos de alta calidad con contexto tecnico y resultado esperado.")
        if "voz" in request.prompt.lower() or "robot" in request.prompt.lower():
            learning.append("Mantener continuidad entre cognicion, voz, robotica y seguridad.")
        return list(dict.fromkeys(learning)) or ["Observar si el usuario corrige la respuesta para convertirla en ejemplo."]

    def _score(self, did_well: list[str], missing: list[str], used_context: bool) -> int:
        score = 58 + len(did_well) * 8 - len(missing) * 9
        if used_context:
            score += 6
        return max(0, min(100, score))

    def _recommended_memory(
        self,
        prompt: str,
        response: str,
        request: CognitiveReflectionRequest,
        missing: list[str],
    ) -> AutobiographicalMemoryRequest | None:
        normalized = prompt.lower()
        trace = self._dialogue_trace(request)
        analysis = trace.get("analysis", {}) if trace else {}
        memory_policy = analysis.get("memory_policy")
        route = analysis.get("cognitive_route")
        should_store_dialogue = memory_policy == "candidate_autobiographical_memory"
        has_preference_marker = any(
            marker in normalized
            for marker in (
                "prefiero que",
                "me gusta que",
                "recorda que",
                "recuerda que",
                "quiero que recuerdes",
                "de ahora en adelante",
                "siempre que",
            )
        )
        has_goal_marker = any(
            marker in normalized
            for marker in ("mi objetivo es", "mi objetivo principal", "objetivo de largo plazo")
        )
        has_decision_marker = "decision" in normalized
        allow_explicit_stable_memory = has_goal_marker or has_decision_marker or has_preference_marker
        block_reason = self._memory_block_reason(normalized, analysis, self._emotional_trace(request), allow_explicit_stable_memory)
        if block_reason is not None:
            return None
        if has_goal_marker or has_decision_marker or has_preference_marker or should_store_dialogue:
            kind = "decision" if "decision" in normalized else "project_state"
            if has_preference_marker:
                kind = "preference"
            if has_goal_marker:
                kind = "goal"
            return AutobiographicalMemoryRequest(
                kind=kind,
                title=f"Reflexion desde {request.source}: {prompt[:72]}",
                content=(
                    "CEIBO debe recordar esta interaccion como senal de continuidad. "
                    f"Ruta cognitiva: {route or 'sin ruta'}. "
                    f"Respuesta resumida: {response[:220]}"
                ),
                importance=72 if missing else 80,
                source="cognitive_reflection_loop",
                tags=["sprint42", "dialogue-orchestrator-v1", "reflection", request.source],
                metadata={
                    "missing": missing,
                    "intents": request.intents,
                    "dialogue_route": route,
                    "tool_used": trace.get("tool_used") if trace else None,
                },
            )
        return None

    def _tags(
        self,
        request: CognitiveReflectionRequest,
        missing: list[str],
        should_learn: list[str],
    ) -> list[str]:
        tags = ["cognitive-reflection", f"source:{request.source}"]
        tags.extend(f"intent:{intent}" for intent in request.intents[:4])
        if missing:
            tags.append("has-missing")
        if should_learn:
            tags.append("learning-signal")
        trace = self._dialogue_trace(request)
        analysis = trace.get("analysis", {}) if trace else {}
        if analysis.get("cognitive_route"):
            tags.append(f"route:{analysis['cognitive_route']}")
        if trace.get("tool_used"):
            tags.append(f"tool:{trace['tool_used']}")
        emotional = self._emotional_trace(request)
        if emotional.get("primary_state"):
            tags.append(f"emotional:{emotional['primary_state']}")
        return tags

    def _dialogue_trace(self, request: CognitiveReflectionRequest) -> dict[str, Any]:
        trace = request.metadata.get("dialogue_trace")
        return trace if isinstance(trace, dict) else {}

    def _emotional_trace(self, request: CognitiveReflectionRequest) -> dict[str, Any]:
        trace = self._dialogue_trace(request)
        emotional = trace.get("emotional_state_trace")
        return emotional if isinstance(emotional, dict) else {}

    def _memory_block_reason(
        self,
        normalized_prompt: str,
        analysis: dict[str, Any],
        emotional: dict[str, Any] | None = None,
        allow_explicit_stable_memory: bool = False,
    ) -> str | None:
        memory_policy = analysis.get("memory_policy")
        if memory_policy in {
            "forget_or_do_not_store",
            "blocked_sensitive_memory",
            "blocked_transient_memory",
            "needs_user_confirmation",
        }:
            return str(memory_policy)
        if emotional and emotional.get("should_avoid_memory") and not allow_explicit_stable_memory:
            return "emotional_state_should_not_be_memorized"
        if self._contains(
            normalized_prompt,
            (
                "no recuerdes",
                "no recordar",
                "no guardes",
                "olvida",
                "borra",
            ),
        ):
            return "user_requested_no_memory"
        if self._contains(
            normalized_prompt,
            (
                "password",
                "contrasena",
                "contraseña",
                "token",
                "api key",
                "apikey",
                "secret",
                "dni",
                "documento",
                "pasaporte",
                "tarjeta",
                "cvv",
                "diagnostico",
                "diagnóstico",
                "depresion",
                "depresión",
                "ansiedad",
                "mi religion",
                "mi religión",
                "mi partido politico",
                "mi partido político",
                "vida intima",
                "vida íntima",
                "sexual",
            ),
        ):
            return "sensitive_content"
        if self._contains(
            normalized_prompt,
            (
                "hoy estoy",
                "ahora estoy",
                "me siento",
                "estoy enojado",
                "estoy triste",
                "estoy frustrado",
                "estoy cansado",
                "jaja",
                "jeje",
                "sarcasmo",
                "claro seguro",
                "idiota",
                "inutil",
                "estupido",
                "mierda",
            ),
        ):
            return "transient_or_aggressive_content"
        if self._contains(
            normalized_prompt,
            (
                "prefiero que no",
                "antes dije",
                "me contradigo",
                "cambio de opinion",
                "cambio de opinión",
                "ya no prefiero",
            ),
        ):
            return "contradictory_preference"
        return None

    def _contains(self, value: str, needles: tuple[str, ...]) -> bool:
        return any(needle in value for needle in needles)

    def _append(self, record: CognitiveReflectionRecord) -> None:
        path = self.reflection_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    def _read_records(self) -> list[CognitiveReflectionRecord]:
        path = self.reflection_path()
        if not path.exists():
            return []
        records: list[CognitiveReflectionRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(CognitiveReflectionRecord.model_validate(json.loads(line)))
            except Exception:
                continue
        return records

    def _summary(self, records: list[CognitiveReflectionRecord], average_score: float) -> str:
        if not records:
            return "Cognitive Reflection Loop espera respuestas reales para registrar aprendizaje interno."
        return (
            f"Cognitive Reflection Loop activo: {len(records)} reflexiones, "
            f"calidad promedio {average_score}/100."
        )


cognitive_reflection_service = CognitiveReflectionService()
