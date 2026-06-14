import json
from hashlib import sha256
from collections import Counter
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from ceibo_core.core.config import settings
from ceibo_core.models.schemas import (
    LearningEventRequest,
    LearningEventResponse,
    TrainingDatasetStats,
    TrainingExample,
    TrainingExampleRequest,
    TrainingFeedbackRequest,
)


class TrainingDataService:
    def project_root(self) -> Path:
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "docker-compose.yml").exists():
                return parent
            if (parent / "pyproject.toml").exists() and parent.name == "app":
                return parent
        return current.parents[4]

    def dataset_path(self) -> Path:
        configured = Path(settings.ceibo_training_dataset_path)
        if configured.is_absolute():
            return configured
        return self.project_root() / configured

    async def append_example(self, request: TrainingExampleRequest) -> TrainingExample:
        example = TrainingExample(
            instruction=request.instruction,
            input=request.input,
            response=request.response,
            tags=request.tags,
            source=request.source,
            metadata=request.metadata,
        )
        self._write_example(example)
        return example

    async def append_feedback(self, request: TrainingFeedbackRequest) -> TrainingExample:
        corrected_response = (request.corrected_response or "").strip()
        response = corrected_response or request.original_response
        tags = list(dict.fromkeys([*request.tags, "feedback", f"rating:{request.rating.value}"]))
        metadata = {
            **request.metadata,
            "original_response": request.original_response,
            "has_correction": bool(corrected_response),
        }
        example = TrainingExample(
            instruction=request.instruction,
            input=request.input,
            response=response,
            tags=tags,
            source=request.source,
            rating=request.rating,
            metadata=metadata,
        )
        self._write_example(example)
        return example

    async def append_learning_event(self, request: LearningEventRequest) -> LearningEventResponse:
        corrected_response = (
            request.corrected_response
            if request.rating.value == "corrected"
            else None
        )
        response_text = (corrected_response or request.assistant_response).strip()
        fingerprint = self._learning_fingerprint(
            request.instruction,
            response_text,
            request.rating.value,
        )
        existing = self._find_learning_duplicate(fingerprint)
        if existing:
            return LearningEventResponse(
                saved=False,
                example=existing,
                duplicate_of=existing.example_id,
                quality_score=self._quality_score(existing),
                warnings=["duplicado exacto: no se guardo otra copia"],
                summary=f"Learning Loop ya tenia este ejemplo como {existing.rating}.",
                next_actions=["Revisar el ejemplo existente antes de repetir feedback."],
            )

        tags = self._normalized_tags([*request.tags, "learning_loop", "workbench"])
        warnings = self._learning_warnings(request, response_text)
        feedback = TrainingFeedbackRequest(
            instruction=request.instruction,
            original_response=request.assistant_response,
            corrected_response=corrected_response,
            rating=request.rating,
            tags=tags,
            source=request.source,
            metadata={
                **request.metadata,
                "learning_loop": True,
                "reviewed_by": "human",
                "learning_fingerprint": fingerprint,
                "quality_warnings": warnings,
            },
        )
        example = await self.append_feedback(feedback)
        summary = self._learning_summary(example)
        quality_score = self._quality_score(example)
        next_actions = [
            "Usar este ejemplo en curacion de dataset.",
            "Revisar ejemplos corregidos antes de entrenamiento.",
        ]
        if example.rating and example.rating.value == "bad":
            next_actions.insert(0, "No promover esta respuesta; usarla como contraejemplo.")
        if warnings:
            next_actions.insert(0, "Revisar advertencias antes de entrenar con este ejemplo.")
        return LearningEventResponse(
            saved=True,
            example=example,
            summary=summary,
            quality_score=quality_score,
            warnings=warnings,
            next_actions=next_actions,
        )

    async def list_examples(self, limit: int = 20) -> list[TrainingExample]:
        examples = self._read_examples()
        return examples[-limit:]

    async def stats(self) -> TrainingDatasetStats:
        path = self.dataset_path()
        examples = self._read_examples()
        tag_counts: Counter[str] = Counter()
        rating_counts: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()

        for example in examples:
            tag_counts.update(example.tags)
            rating_counts.update([example.rating.value if example.rating else "unrated"])
            source_counts.update([example.source])

        last_updated = (
            datetime.fromtimestamp(path.stat().st_mtime, UTC) if path.exists() else None
        )
        return TrainingDatasetStats(
            dataset_path=str(path),
            total_examples=len(examples),
            tag_counts=dict(tag_counts),
            rating_counts=dict(rating_counts),
            source_counts=dict(source_counts),
            last_updated=last_updated,
        )

    def _write_example(self, example: TrainingExample) -> None:
        path = self.dataset_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(example.model_dump_json() + "\n")

    def _read_examples(self) -> list[TrainingExample]:
        path = self.dataset_path()
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        examples: list[TrainingExample] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                examples.append(TrainingExample.model_validate(json.loads(line)))
            except (JSONDecodeError, ValidationError):
                continue
        return examples

    def _learning_summary(self, example: TrainingExample) -> str:
        rating = example.rating.value if example.rating else "unrated"
        correction = " con correccion humana" if example.metadata.get("has_correction") else ""
        return f"Learning Loop guardo ejemplo {rating}{correction} desde {example.source}."

    def _normalized_tags(self, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw_tag in tags:
            tag = raw_tag.strip().lower().replace(" ", "-")[:48]
            if tag and tag not in normalized:
                normalized.append(tag)
        return normalized[:16]

    def _learning_fingerprint(self, instruction: str, response: str, rating: str) -> str:
        payload = "\n".join(
            [
                self._normalized_text(instruction),
                self._normalized_text(response),
                rating.strip().lower(),
            ]
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def _find_learning_duplicate(self, fingerprint: str) -> TrainingExample | None:
        for example in reversed(self._read_examples()):
            if example.metadata.get("learning_fingerprint") == fingerprint:
                return example
        return None

    def _learning_warnings(self, request: LearningEventRequest, response_text: str) -> list[str]:
        warnings: list[str] = []
        if len(request.instruction) < 12:
            warnings.append("instruccion muy corta")
        if len(response_text) < 24:
            warnings.append("respuesta muy corta")
        if request.rating.value == "good" and request.corrected_response:
            warnings.append("rating good ignora correccion enviada")
        if request.rating.value == "bad" and not request.corrected_response:
            warnings.append("contraejemplo sin respuesta ideal")
        return warnings

    def _quality_score(self, example: TrainingExample) -> int:
        score = 40
        if len(example.instruction.strip()) >= 12:
            score += 15
        if len(example.response.strip()) >= 24:
            score += 20
        if example.rating:
            score += 10
        if example.rating and example.rating.value == "corrected":
            score += 10
        if example.metadata.get("has_correction"):
            score += 5
        score -= len(example.metadata.get("quality_warnings", [])) * 10
        return max(0, min(100, score))

    def _normalized_text(self, value: str) -> str:
        return " ".join(value.strip().lower().split())


training_data_service = TrainingDataService()
