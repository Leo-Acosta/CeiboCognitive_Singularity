from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from ceibo_core.ai_engine import ceibo_engine
from ceibo_core.models.schemas import EvaluationCaseResult, EvaluationSuiteReport
from ceibo_core.services.memory import memory_service


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    category: str
    prompt: str
    expected_signals: tuple[str, ...]
    context: tuple[str, ...] = ()


class EvaluationHarnessService:
    def __init__(self) -> None:
        self._latest_report: EvaluationSuiteReport | None = None

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
        return report

    def latest(self) -> EvaluationSuiteReport | None:
        return self._latest_report

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
