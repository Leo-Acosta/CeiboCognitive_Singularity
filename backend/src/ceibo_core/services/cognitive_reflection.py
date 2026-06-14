from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

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
        if len(response) >= 160:
            strengths.append("Respondio con suficiente desarrollo inicial.")
        if "Siguientes pasos recomendados" in response or "siguiente" in response.lower():
            strengths.append("Incluyo orientacion accionable.")
        if request.used_context or request.memory_context:
            strengths.append("Uso contexto recuperado para continuidad.")
        if any(intent in request.intents for intent in ("security", "devcore_modify", "training")):
            strengths.append("Detecto una intencion tecnica relevante.")
        return strengths or ["Genero una respuesta util para continuar la conversacion."]

    def _missing(self, request: CognitiveReflectionRequest, response: str) -> list[str]:
        missing: list[str] = []
        lowered = response.lower()
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
        if "objetivo" in normalized or "decision" in normalized or "prefer" in normalized:
            return AutobiographicalMemoryRequest(
                kind="decision" if "decision" in normalized else "project_state",
                title=f"Reflexion desde {request.source}: {prompt[:72]}",
                content=(
                    "CEIBO debe recordar esta interaccion como senal de continuidad. "
                    f"Respuesta resumida: {response[:220]}"
                ),
                importance=72 if missing else 80,
                source="cognitive_reflection_loop",
                tags=["sprint42", "reflection", request.source],
                metadata={"missing": missing, "intents": request.intents},
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
        return tags

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
