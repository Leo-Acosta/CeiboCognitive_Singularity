from pathlib import Path

from ceibo_core.models.schemas import (
    DatasetCurationRequest,
    LearningCurationReview,
    QloraTrainingRequest,
    TrainingDryRunReport,
    TrainingPromotionGate,
    TrainingReadinessConsole,
    TrainingReadinessCoverage,
    TrainingReadinessSignal,
)
from ceibo_core.services.dataset_curator import DatasetCuratorService, dataset_curator_service
from ceibo_core.services.evaluation_harness import EvaluationHarnessService, evaluation_harness_service
from ceibo_core.services.training_runner import TrainingRunnerService, training_runner_service


class TrainingReadinessService:
    def __init__(
        self,
        *,
        curator: DatasetCuratorService = dataset_curator_service,
        evaluation: EvaluationHarnessService = evaluation_harness_service,
        runner: TrainingRunnerService = training_runner_service,
    ) -> None:
        self.curator = curator
        self.evaluation = evaluation
        self.runner = runner

    async def console(
        self,
        request: QloraTrainingRequest | None = None,
    ) -> TrainingReadinessConsole:
        request = request or QloraTrainingRequest(max_steps=1, local_files_only=True)
        curation = await self.curator.review(DatasetCurationRequest(min_score=60))
        gate = await self.evaluation.training_promotion_gate()
        dry_run, dry_run_warnings = self._safe_dry_run(request, gate)
        signals = self._signals(curation, gate, dry_run, request)
        coverage = self._coverage(curation)
        blockers = self._blockers(signals, gate, curation, dry_run)
        warnings = list(dict.fromkeys([*gate.warnings, *dry_run_warnings, *self._coverage_warnings(coverage)]))
        readiness_score = self._score(signals, coverage)
        ready_for_preflight = bool(dry_run and dry_run.allowed and gate.allowed and curation.readiness.ready)
        ready_for_training = ready_for_preflight and readiness_score >= 85
        status = self._status(ready_for_preflight, ready_for_training, blockers, readiness_score)
        next_actions = self._next_actions(status, blockers, warnings, gate, curation, dry_run)

        dataset_path = dry_run.dataset_path if dry_run else str(curation.stats.dataset_path)
        return TrainingReadinessConsole(
            status=status,
            summary=self._summary(status, readiness_score, ready_for_preflight, ready_for_training),
            readiness_score=readiness_score,
            ready_for_preflight=ready_for_preflight,
            ready_for_training=ready_for_training,
            dataset_path=dataset_path,
            config_path=str(Path(request.config_path)),
            output_dir=dry_run.output_dir if dry_run else None,
            base_model=dry_run.base_model if dry_run else request.base_model,
            signals=signals,
            coverage=coverage,
            blockers=blockers,
            warnings=warnings,
            next_actions=next_actions,
            curation_review=curation,
            promotion_gate=gate,
            dry_run=dry_run,
        )

    def _safe_dry_run(
        self,
        request: QloraTrainingRequest,
        gate: TrainingPromotionGate,
    ) -> tuple[TrainingDryRunReport | None, list[str]]:
        try:
            return self.runner.dry_run(request, gate), []
        except Exception as exc:
            return None, [f"Dry run no disponible: {exc}"]

    def _signals(
        self,
        curation: LearningCurationReview,
        gate: TrainingPromotionGate,
        dry_run: TrainingDryRunReport | None,
        request: QloraTrainingRequest,
    ) -> list[TrainingReadinessSignal]:
        latest = gate.latest_report
        signals = [
            TrainingReadinessSignal(
                name="dataset_curado",
                passed=curation.readiness.usable_examples >= curation.readiness.required_examples,
                severity="blocking",
                current=curation.readiness.usable_examples,
                target=curation.readiness.required_examples,
                detail="Ejemplos curados disponibles para entrenamiento.",
            ),
            TrainingReadinessSignal(
                name="correcciones_humanas",
                passed=curation.readiness.corrected_examples >= 3,
                severity="blocking",
                current=curation.readiness.corrected_examples,
                target=3,
                detail="Correcciones humanas suficientes para orientar conducta.",
            ),
            TrainingReadinessSignal(
                name="calidad_promedio",
                passed=curation.readiness.average_score >= 70,
                severity="warning",
                current=round(curation.readiness.average_score, 2),
                target=70,
                detail="Calidad promedio del dataset curado.",
            ),
            TrainingReadinessSignal(
                name="evaluacion_reciente",
                passed=latest is not None,
                severity="blocking",
                current=latest.run_id if latest else "missing",
                target="latest_report",
                detail="Existe una suite de evaluacion reciente.",
            ),
            TrainingReadinessSignal(
                name="score_evaluacion",
                passed=(gate.evidence.evaluation_score or 0) >= 85,
                severity="blocking",
                current=gate.evidence.evaluation_score,
                target=85,
                detail="Score minimo para no entrenar sobre regresiones abiertas.",
            ),
            TrainingReadinessSignal(
                name="promotion_gate",
                passed=gate.allowed,
                severity="blocking",
                current=gate.level,
                target="promotion_preflight_allowed",
                detail=gate.summary,
            ),
            TrainingReadinessSignal(
                name="dry_run_qlora",
                passed=bool(dry_run and dry_run.allowed),
                severity="blocking",
                current=dry_run.status.value if dry_run else "missing",
                target="ready",
                detail="Preflight planificado sin ejecutar entrenamiento real.",
            ),
            TrainingReadinessSignal(
                name="modo_local_seguro",
                passed=request.local_files_only is True and (request.max_steps or 1) <= 10,
                severity="warning",
                current=f"local_files_only={request.local_files_only}, max_steps={request.max_steps}",
                target="local_files_only=true, max_steps<=10",
                detail="Configuracion conservadora para primera prueba local.",
            ),
        ]
        return signals

    def _coverage(self, curation: LearningCurationReview) -> list[TrainingReadinessCoverage]:
        tag_counts = curation.stats.tag_counts
        category_tags = {
            "seguridad": ("security", "safety", "cyber", "evaluation_remediation"),
            "codigo": ("code", "devcore", "patch", "fastapi", "react"),
            "memoria": ("memory", "autobiographical", "reflection"),
            "herramientas": ("tool", "weather", "travel", "entertainment", "market"),
            "robot": ("robot", "voice", "embodied", "movement"),
            "proyecto": ("project", "architecture", "cognition", "training"),
        }
        coverage: list[TrainingReadinessCoverage] = []
        for category, tags in category_tags.items():
            count = sum(tag_counts.get(tag, 0) for tag in tags)
            if count >= 3:
                status = "covered"
            elif count:
                status = "thin"
            else:
                status = "missing"
            coverage.append(
                TrainingReadinessCoverage(
                    category=category,
                    examples=count,
                    required_examples=3,
                    status=status,
                )
            )
        return coverage

    def _coverage_warnings(self, coverage: list[TrainingReadinessCoverage]) -> list[str]:
        return [
            f"Cobertura baja en {item.category}: {item.examples}/{item.required_examples}."
            for item in coverage
            if item.status != "covered"
        ][:4]

    def _blockers(
        self,
        signals: list[TrainingReadinessSignal],
        gate: TrainingPromotionGate,
        curation: LearningCurationReview,
        dry_run: TrainingDryRunReport | None,
    ) -> list[str]:
        blockers = [
            signal.detail
            for signal in signals
            if signal.severity == "blocking" and not signal.passed
        ]
        blockers.extend(gate.blockers)
        blockers.extend(curation.readiness.blockers)
        if dry_run:
            blockers.extend(dry_run.blockers)
        return list(dict.fromkeys(blockers))

    def _score(
        self,
        signals: list[TrainingReadinessSignal],
        coverage: list[TrainingReadinessCoverage],
    ) -> int:
        weights = {
            "dataset_curado": 18,
            "correcciones_humanas": 12,
            "calidad_promedio": 10,
            "evaluacion_reciente": 12,
            "score_evaluacion": 16,
            "promotion_gate": 14,
            "dry_run_qlora": 10,
            "modo_local_seguro": 4,
        }
        score = sum(weights.get(signal.name, 0) for signal in signals if signal.passed)
        covered = sum(1 for item in coverage if item.status == "covered")
        thin = sum(1 for item in coverage if item.status == "thin")
        score += min(4, covered) + min(2, thin)
        return max(0, min(100, score))

    def _status(
        self,
        ready_for_preflight: bool,
        ready_for_training: bool,
        blockers: list[str],
        readiness_score: int,
    ) -> str:
        if ready_for_training:
            return "ready_for_first_local_finetune"
        if ready_for_preflight:
            return "ready_for_qlora_preflight"
        if blockers:
            return "blocked_needs_evidence"
        if readiness_score >= 60:
            return "nearly_ready"
        return "collecting_evidence"

    def _summary(
        self,
        status: str,
        readiness_score: int,
        ready_for_preflight: bool,
        ready_for_training: bool,
    ) -> str:
        if ready_for_training:
            return f"Training Readiness {readiness_score}/100: habilitado para primer fine-tune local conservador."
        if ready_for_preflight:
            return f"Training Readiness {readiness_score}/100: listo para preflight QLoRA, todavia no para entrenamiento largo."
        if status == "blocked_needs_evidence":
            return f"Training Readiness {readiness_score}/100: bloqueado hasta completar evidencia minima."
        return f"Training Readiness {readiness_score}/100: seguir acumulando dataset, evaluacion y cobertura."

    def _next_actions(
        self,
        status: str,
        blockers: list[str],
        warnings: list[str],
        gate: TrainingPromotionGate,
        curation: LearningCurationReview,
        dry_run: TrainingDryRunReport | None,
    ) -> list[str]:
        actions: list[str] = []
        if blockers:
            actions.append(f"Resolver primero: {blockers[0]}")
        actions.extend(curation.readiness.next_actions[:2])
        actions.extend(gate.next_actions[:2])
        if dry_run:
            actions.extend(dry_run.next_actions[:2])
        if warnings:
            actions.append(f"Revisar advertencia: {warnings[0]}")
        if status == "ready_for_qlora_preflight":
            actions.insert(0, "Ejecutar preflight QLoRA y revisar manifest/logs antes de entrenar.")
        if status == "ready_for_first_local_finetune":
            actions.insert(0, "Preparar primer fine-tune local corto con rollback y comparacion antes/despues.")
        return list(dict.fromkeys(actions))[:8]


training_readiness_service = TrainingReadinessService()
