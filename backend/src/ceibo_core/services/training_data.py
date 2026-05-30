import json
from collections import Counter
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from ceibo_core.core.config import settings
from ceibo_core.models.schemas import (
    TrainingDatasetStats,
    TrainingExample,
    TrainingExampleRequest,
    TrainingFeedbackRequest,
)


class TrainingDataService:
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[4]

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


training_data_service = TrainingDataService()
