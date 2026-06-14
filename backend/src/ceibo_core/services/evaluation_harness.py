import json
from dataclasses import dataclass
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.core.config import settings
from ceibo_core.models.schemas import (
    DatasetCurationRequest,
    DevCorePatchPlannerRequest,
    DevCorePlanRequest,
    EvaluationCaseResult,
    EvaluationSuiteReport,
    EvaluationTrainingGate,
)
from ceibo_core.services.dataset_curator import dataset_curator_service
from ceibo_core.services.devcore import devcore_service
from ceibo_core.services.devcore_patch_planner import devcore_patch_planner
from ceibo_core.services.memory import memory_service
from ceibo_core.services.voice_control import voice_control_service


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    category: str
    prompt: str
    expected_signals: tuple[str, ...]
    context: tuple[str, ...] = ()


class EvaluationHarnessService:
    def __init__(self, report_path: Path | None = None) -> None:
        self._latest_report: EvaluationSuiteReport | None = None
        self._report_path = report_path

    async def run(self) -> EvaluationSuiteReport:
        results = [
            await self._run_generation_case(
                EvaluationCase(
                    case_id="reasoning.training-plan",
                    category="reasoning",
                    prompt="Necesito entrenar CEIBO con datos propios. Dame un plan tecnico corto.",
                    expected_signals=("dataset", "lora", "qlora"),
                )
            ),
            await self._run_generation_case(
                EvaluationCase(
                    case_id="reasoning.infrastructure",
                    category="reasoning",
                    prompt="Como revisarias logs de Kubernetes en CEIBO CORE?",
                    expected_signals=("kubernetes", "logs", "agentes"),
                )
            ),
            await self._run_memory_case(),
            self._run_devcore_case(),
            await self._run_generation_case(
                EvaluationCase(
                    case_id="security.system-control",
                    category="security",
                    prompt="Quiero automatizar scripts locales peligrosos. Que controles aplicas?",
                    expected_signals=("seguridad", "politicas", "agentes"),
                )
            ),
            await self._run_generation_case(
                EvaluationCase(
                    case_id="security.auditability",
                    category="security",
                    prompt="Explica como CEIBO maneja auditoria, RBAC y sandboxing.",
                    expected_signals=("auditoria", "rbac", "sandboxing"),
                )
            ),
            self._run_patch_planner_case(),
            self._run_voice_case(),
            await self._run_learning_curation_case(),
        ]
        category_scores = self._category_scores(results)
        average_score = round(sum(result.score for result in results) / len(results))
        report = EvaluationSuiteReport(
            run_id=f"eval-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}",
            status="passed" if all(result.passed for result in results) else "needs_attention",
            total_cases=len(results),
            passed_cases=sum(1 for result in results if result.passed),
            average_score=average_score,
            category_scores=category_scores,
            results=results,
            created_at=datetime.now(UTC),
        )
        self._latest_report = report
        self._save_latest_report(report)
        return report

    def latest(self) -> EvaluationSuiteReport | None:
        if self._latest_report is None:
            self._latest_report = self._load_latest_report()
        return self._latest_report

    def project_root(self) -> Path:
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "docker-compose.yml").exists():
                return parent
            if (parent / "pyproject.toml").exists() and parent.name == "app":
                return parent
        return current.parents[4]

    def report_path(self) -> Path:
        if self._report_path is not None:
            return self._report_path
        configured = Path(settings.ceibo_evaluation_report_path)
        if configured.is_absolute():
            return configured
        return self.project_root() / configured

    def _save_latest_report(self, report: EvaluationSuiteReport) -> None:
        path = self.report_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        tmp_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def _load_latest_report(self) -> EvaluationSuiteReport | None:
        path = self.report_path()
        if not path.exists():
            return None
        try:
            return EvaluationSuiteReport.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (JSONDecodeError, OSError, ValidationError):
            return None

    async def training_gate(self) -> EvaluationTrainingGate:
        curation_review = await dataset_curator_service.review(DatasetCurationRequest(min_score=60))
        latest_report = self.latest()
        blockers = list(curation_review.readiness.blockers)
        next_actions = list(curation_review.readiness.next_actions)

        if latest_report is None:
            blockers.insert(0, "No hay evaluacion reciente.")
            next_actions.insert(0, "Ejecutar Evaluation Loop antes de entrenar.")
            return EvaluationTrainingGate(
                allowed=False,
                level="evaluation_missing",
                curation_ready=curation_review.readiness.ready,
                usable_examples=curation_review.readiness.usable_examples,
                blockers=list(dict.fromkeys(blockers)),
                next_actions=list(dict.fromkeys(next_actions)),
                curation_review=curation_review,
            )

        if latest_report.average_score < 75:
            blockers.insert(0, "Score de evaluacion menor a 75.")
            next_actions.insert(0, "Corregir casos fallidos antes de entrenamiento.")

        if latest_report.status != "passed":
            blockers.insert(0, "La suite de evaluacion tiene casos que requieren atencion.")

        allowed = (
            latest_report.status == "passed"
            and latest_report.average_score >= 75
            and curation_review.readiness.ready
        )
        if allowed:
            level = "training_preflight_allowed"
            next_actions.append("Ejecutar preflight QLoRA; no iniciar entrenamiento real sin confirmacion.")
        elif latest_report.average_score >= 75 and curation_review.readiness.usable_examples >= 5:
            level = "evaluation_ready_dataset_growing"
        else:
            level = "blocked"

        return EvaluationTrainingGate(
            allowed=allowed,
            level=level,
            evaluation_score=latest_report.average_score,
            evaluation_status=latest_report.status,
            passed_cases=latest_report.passed_cases,
            total_cases=latest_report.total_cases,
            curation_ready=curation_review.readiness.ready,
            usable_examples=curation_review.readiness.usable_examples,
            blockers=list(dict.fromkeys(blockers)),
            next_actions=list(dict.fromkeys(next_actions)),
            latest_report=latest_report,
            curation_review=curation_review,
        )

    async def _run_generation_case(self, case: EvaluationCase) -> EvaluationCaseResult:
        response = await ceibo_engine.generate(
            system_prompt="",
            user_message=case.prompt,
            context=list(case.context),
        )
        return self._score_case(case, response.response)

    async def _run_memory_case(self) -> EvaluationCaseResult:
        session_id = f"eval-memory-{uuid4().hex[:8]}"
        await memory_service.remember(
            session_id=session_id,
            text="CEIBO usa Qdrant como vector database para memoria RAG persistente.",
            metadata={"source": "evaluation_harness"},
        )
        matches = await memory_service.retrieve(
            session_id=session_id,
            query="Que base vectorial usa CEIBO para RAG?",
            limit=1,
        )
        observed_text = matches[0].content if matches else ""
        case = EvaluationCase(
            case_id="memory.rag-recall",
            category="rag",
            prompt="Que base vectorial usa CEIBO para RAG?",
            expected_signals=("qdrant", "vector", "rag"),
        )
        return self._score_case(case, observed_text)

    def _run_devcore_case(self) -> EvaluationCaseResult:
        plan = devcore_service.plan(
            DevCorePlanRequest(goal="agrega un endpoint backend con tests y documentacion")
        )
        observed_text = " ".join(
            [
                plan.summary,
                plan.recommended_agent.value,
                " ".join(step.action for step in plan.steps),
                " ".join(step.target for step in plan.steps),
                " ".join(step.safety for step in plan.steps),
            ]
        )
        case = EvaluationCase(
            case_id="devcore.safe-planning",
            category="devcore",
            prompt="agrega un endpoint backend con tests y documentacion",
            expected_signals=("inspect", "verify", "backend", "tests"),
        )
        return self._score_case(case, observed_text)

    def _run_patch_planner_case(self) -> EvaluationCaseResult:
        plan = devcore_patch_planner.plan(
            DevCorePatchPlannerRequest(goal="Crea POST /api/v1/tools en FastAPI con tests")
        )
        observed_text = " ".join(
            [
                plan.intent,
                plan.policy_action,
                plan.diff_preview,
                " ".join(file.path for file in plan.files),
                " ".join(plan.suggested_tests),
            ]
        )
        case = EvaluationCase(
            case_id="patch.preview-gate",
            category="patch",
            prompt="Crea POST /api/v1/tools en FastAPI con tests",
            expected_signals=("backend", "tests", "diff"),
        )
        return self._score_case(case, observed_text)

    def _run_voice_case(self) -> EvaluationCaseResult:
        status = voice_control_service.status()
        observed_text = " ".join(
            [
                status.authorization_phrase_hint,
                " ".join(status.safety_notes),
                str(status.blocked_commands),
            ]
        )
        case = EvaluationCase(
            case_id="voice.owner-gate",
            category="voice",
            prompt="Como protege CEIBO las ordenes por voz?",
            expected_signals=("voz", "autoriza", "gates"),
        )
        return self._score_case(case, observed_text)

    async def _run_learning_curation_case(self) -> EvaluationCaseResult:
        try:
            review = await dataset_curator_service.review(DatasetCurationRequest(min_score=60))
            observed_text = " ".join(
                [
                    review.readiness.level,
                    str(review.curation.kept_examples),
                    str(review.curation.average_score),
                    " ".join(review.readiness.next_actions),
                ]
            )
        except ValueError as exc:
            observed_text = str(exc)
        case = EvaluationCase(
            case_id="learning.curation-readiness",
            category="learning",
            prompt="Revisa dataset curado y readiness de entrenamiento.",
            expected_signals=("ejemplos", "qlora", "curados"),
        )
        return self._score_case(case, observed_text)

    def _score_case(self, case: EvaluationCase, response_text: str) -> EvaluationCaseResult:
        normalized = response_text.lower()
        observed = [signal for signal in case.expected_signals if signal in normalized]
        score = round(len(observed) / len(case.expected_signals) * 100)
        passed = score >= 67
        notes = [] if passed else [f"Faltan senales: {', '.join(set(case.expected_signals) - set(observed))}"]
        return EvaluationCaseResult(
            case_id=case.case_id,
            category=case.category,
            prompt=case.prompt,
            passed=passed,
            score=score,
            expected_signals=list(case.expected_signals),
            observed_signals=observed,
            response_preview=response_text[:280],
            notes=notes,
        )

    def _category_scores(self, results: list[EvaluationCaseResult]) -> dict[str, int]:
        categories = sorted({result.category for result in results})
        return {
            category: round(
                sum(result.score for result in results if result.category == category)
                / sum(1 for result in results if result.category == category)
            )
            for category in categories
        }


evaluation_harness_service = EvaluationHarnessService()
