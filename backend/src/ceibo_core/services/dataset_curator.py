import json
import re
from collections import Counter
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from ceibo_core.models.schemas import (
    CuratedTrainingExample,
    DatasetCurationIssue,
    DatasetCurationReport,
    DatasetCurationRequest,
    DatasetIssueSeverity,
    TrainingExample,
    TrainingFeedbackRating,
)


WHITESPACE_PATTERN = re.compile(r"\s+")
PLACEHOLDER_PATTERNS = (
    "no pude conectar",
    "lorem ipsum",
    "todo",
    "pendiente",
    "respuesta inicial",
    "placeholder",
)


class DatasetCuratorService:
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[4]

    def default_source_path(self) -> Path:
        return self.project_root() / "training" / "datasets" / "ceibo_instructions.jsonl"

    def default_output_path(self, source_path: Path) -> Path:
        return source_path.with_name(f"{source_path.stem}.curated.jsonl")

    def curate(
        self,
        request: DatasetCurationRequest | None = None,
        *,
        write_output: bool = False,
    ) -> DatasetCurationReport:
        request = request or DatasetCurationRequest()
        source_path = self._resolve_project_path(request.source_path, self.default_source_path())
        output_path = self._resolve_project_path(
            request.output_path,
            self.default_output_path(source_path),
        )

        if not source_path.exists():
            raise ValueError(f"Dataset source does not exist: {source_path}")

        lines = source_path.read_text(encoding="utf-8-sig").splitlines()
        issues: list[DatasetCurationIssue] = []
        curated: list[CuratedTrainingExample] = []
        seen_fingerprints: set[str] = set()
        score_buckets: Counter[str] = Counter()
        duplicate_examples = 0
        invalid_lines = 0
        parsed_examples = 0
        score_total = 0

        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            try:
                payload = json.loads(line)
                example = TrainingExample.model_validate(payload)
            except (JSONDecodeError, ValidationError) as exc:
                invalid_lines += 1
                issues.append(
                    DatasetCurationIssue(
                        line_number=line_number,
                        severity=DatasetIssueSeverity.ERROR,
                        code="invalid_jsonl_record",
                        message=f"Registro ignorado: {exc}",
                    )
                )
                continue

            parsed_examples += 1
            normalized = self._normalize_example(example)
            fingerprint = self._fingerprint(normalized)
            is_duplicate = fingerprint in seen_fingerprints
            if is_duplicate:
                duplicate_examples += 1
            else:
                seen_fingerprints.add(fingerprint)

            quality_score, quality_notes, example_issues = self._score_example(
                normalized,
                request,
                line_number=line_number,
                is_duplicate=is_duplicate,
            )
            issues.extend(example_issues)
            score_total += quality_score
            score_buckets.update([self._score_bucket(quality_score)])

            should_keep = (
                quality_score >= request.min_score
                and not is_duplicate
                and (request.include_bad_rated or normalized.rating != TrainingFeedbackRating.BAD)
            )
            if should_keep:
                curated.append(
                    CuratedTrainingExample(
                        **normalized.model_dump(),
                        quality_score=quality_score,
                        quality_notes=quality_notes,
                    )
                )

        if request.max_examples is not None:
            curated = curated[: request.max_examples]

        if write_output:
            self._write_curated_dataset(output_path, curated)

        average_score = round(score_total / parsed_examples, 2) if parsed_examples else 0.0
        return DatasetCurationReport(
            source_path=str(source_path),
            output_path=str(output_path) if write_output else None,
            total_lines=len(lines),
            parsed_examples=parsed_examples,
            kept_examples=len(curated),
            dropped_examples=max(parsed_examples - len(curated), 0),
            invalid_lines=invalid_lines,
            duplicate_examples=duplicate_examples,
            average_score=average_score,
            score_buckets=dict(score_buckets),
            issues=issues[:100],
            preview_examples=curated[:5],
        )

    def _resolve_project_path(self, configured_path: str | None, default_path: Path) -> Path:
        project_root = self.project_root().resolve()
        candidate = Path(configured_path) if configured_path else default_path
        if not candidate.is_absolute():
            candidate = project_root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"Path must stay inside project root: {resolved}") from exc
        return resolved

    def _normalize_example(self, example: TrainingExample) -> TrainingExample:
        return example.model_copy(
            update={
                "instruction": self._clean_text(example.instruction),
                "input": self._clean_text(example.input),
                "response": self._clean_text(example.response),
                "tags": self._clean_tags(example.tags),
                "source": self._clean_text(example.source) or "manual",
            }
        )

    def _score_example(
        self,
        example: TrainingExample,
        request: DatasetCurationRequest,
        *,
        line_number: int,
        is_duplicate: bool,
    ) -> tuple[int, list[str], list[DatasetCurationIssue]]:
        score = 70
        notes: list[str] = []
        issues: list[DatasetCurationIssue] = []

        if example.rating == TrainingFeedbackRating.GOOD:
            score += 15
            notes.append("approved_feedback")
        elif example.rating == TrainingFeedbackRating.CORRECTED:
            score += 18
            notes.append("corrected_feedback")
        elif example.rating == TrainingFeedbackRating.BAD:
            score -= 80
            notes.append("bad_feedback")
            issues.append(
                self._issue(
                    line_number,
                    example,
                    DatasetIssueSeverity.WARNING,
                    "bad_feedback",
                    "Ejemplo marcado como malo; se excluye salvo include_bad_rated=true.",
                )
            )
        else:
            notes.append("unrated")

        if len(example.instruction) < request.min_instruction_chars:
            score -= 25
            notes.append("short_instruction")
            issues.append(
                self._issue(
                    line_number,
                    example,
                    DatasetIssueSeverity.WARNING,
                    "short_instruction",
                    "La instruccion es demasiado corta para entrenar con contexto util.",
                )
            )

        if len(example.response) < request.min_response_chars:
            score -= 35
            notes.append("short_response")
            issues.append(
                self._issue(
                    line_number,
                    example,
                    DatasetIssueSeverity.WARNING,
                    "short_response",
                    "La respuesta es demasiado corta para funcionar como respuesta ideal.",
                )
            )

        if not example.tags:
            score -= 5
            notes.append("missing_tags")

        if example.input:
            score += 3
            notes.append("has_context")

        if example.source and example.source != "manual":
            score += 3
            notes.append("tracked_source")

        if self._looks_like_placeholder(example.response):
            score -= 30
            notes.append("placeholder_like_response")
            issues.append(
                self._issue(
                    line_number,
                    example,
                    DatasetIssueSeverity.WARNING,
                    "placeholder_like_response",
                    "La respuesta parece temporal, generica o de error.",
                )
            )

        if is_duplicate:
            score -= 50
            notes.append("duplicate")
            issues.append(
                self._issue(
                    line_number,
                    example,
                    DatasetIssueSeverity.INFO,
                    "duplicate_example",
                    "Ejemplo duplicado exacto; se descarta para evitar sobreentrenamiento.",
                )
            )

        score = max(0, min(score, 100))
        if score < request.min_score:
            issues.append(
                self._issue(
                    line_number,
                    example,
                    DatasetIssueSeverity.INFO,
                    "below_min_score",
                    f"Score {score} menor que el minimo configurado {request.min_score}.",
                )
            )

        return score, notes, issues

    def _write_curated_dataset(
        self,
        output_path: Path,
        curated_examples: list[CuratedTrainingExample],
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        curated_at = datetime.now(UTC).isoformat()
        with output_path.open("w", encoding="utf-8") as file:
            for example in curated_examples:
                metadata = {
                    **example.metadata,
                    "curation_score": example.quality_score,
                    "curation_notes": example.quality_notes,
                    "curated_at": curated_at,
                }
                record = {
                    "example_id": example.example_id,
                    "instruction": example.instruction,
                    "input": example.input,
                    "response": example.response,
                    "tags": example.tags,
                    "source": example.source,
                    "rating": example.rating.value if example.rating else None,
                    "metadata": metadata,
                    "created_at": example.created_at.isoformat(),
                }
                file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _issue(
        self,
        line_number: int,
        example: TrainingExample,
        severity: DatasetIssueSeverity,
        code: str,
        message: str,
    ) -> DatasetCurationIssue:
        return DatasetCurationIssue(
            line_number=line_number,
            example_id=example.example_id,
            severity=severity,
            code=code,
            message=message,
        )

    def _fingerprint(self, example: TrainingExample) -> str:
        return "\n".join(
            [
                example.instruction.lower(),
                example.input.lower(),
                example.response.lower(),
            ]
        )

    def _clean_text(self, value: str) -> str:
        return WHITESPACE_PATTERN.sub(" ", value).strip()

    def _clean_tags(self, tags: list[str]) -> list[str]:
        cleaned = [self._clean_text(tag).lower() for tag in tags]
        return [tag for tag in dict.fromkeys(cleaned) if tag]

    def _looks_like_placeholder(self, response: str) -> bool:
        lower_response = response.lower()
        return any(pattern in lower_response for pattern in PLACEHOLDER_PATTERNS)

    def _score_bucket(self, score: int) -> str:
        if score < 40:
            return "0-39"
        if score < 60:
            return "40-59"
        if score < 80:
            return "60-79"
        return "80-100"


dataset_curator_service = DatasetCuratorService()
