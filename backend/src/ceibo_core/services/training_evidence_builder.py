from datetime import UTC, datetime
from uuid import uuid4

from ceibo_core.models.schemas import (
    EvaluationRemediationItem,
    EvaluationRemediationPlan,
    TrainingEvidenceBuilderReport,
    TrainingEvidenceBuilderRequest,
    TrainingEvidenceCandidate,
    TrainingEvidenceGap,
    TrainingPromotionGate,
)
from ceibo_core.services.evaluation_harness import evaluation_harness_service


class TrainingEvidenceBuilderService:
    async def build(
        self,
        request: TrainingEvidenceBuilderRequest | None = None,
    ) -> TrainingEvidenceBuilderReport:
        request = request or TrainingEvidenceBuilderRequest()
        gate = await evaluation_harness_service.training_promotion_gate()
        remediation_plan = evaluation_harness_service.remediation_plan()
        return self.build_from_components(
            request=request,
            gate=gate,
            remediation_plan=remediation_plan,
        )

    def build_from_components(
        self,
        *,
        request: TrainingEvidenceBuilderRequest,
        gate: TrainingPromotionGate,
        remediation_plan: EvaluationRemediationPlan | None,
    ) -> TrainingEvidenceBuilderReport:
        gaps = self._gaps(request, gate)
        candidates = self._candidates(request, gate, remediation_plan)
        evidence_score = self._evidence_score(request, gate, gaps)
        blocking_gaps = [gap for gap in gaps if gap.blocking]

        if gate.allowed:
            status = "ready_for_dry_run"
            summary = "Training Evidence Builder confirma evidencia suficiente para dry run QLoRA."
            next_actions = [
                "Ejecutar Training Dry Run.",
                "Mantener entrenamiento real bloqueado hasta revisar manifest, logs y confirmacion humana.",
            ]
        elif gate.latest_report is None:
            status = "blocked_no_baseline"
            summary = "Falta baseline de evaluacion; no hay evidencia minima para promocion."
            next_actions = [
                "Ejecutar Evaluation Loop.",
                "Despues reconstruir evidencia antes de cualquier preflight.",
            ]
        else:
            status = "needs_evidence"
            summary = (
                f"Faltan {len(blocking_gaps)} brecha(s) bloqueantes antes de habilitar dry run."
            )
            next_actions = self._next_actions(gaps, candidates)

        return TrainingEvidenceBuilderReport(
            builder_id=f"evidence-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}",
            status=status,
            evidence_score=evidence_score,
            summary=summary,
            gate=gate,
            gaps=gaps,
            candidates=candidates[: request.max_candidates],
            remediation_plan=remediation_plan,
            curation_review=gate.curation_review,
            outcome_review=gate.outcome_review,
            next_actions=list(dict.fromkeys(next_actions)),
        )

    def _gaps(
        self,
        request: TrainingEvidenceBuilderRequest,
        gate: TrainingPromotionGate,
    ) -> list[TrainingEvidenceGap]:
        evidence = gate.evidence
        gaps: list[TrainingEvidenceGap] = []

        if evidence.evaluation_status != "passed":
            gaps.append(
                TrainingEvidenceGap(
                    key="evaluation_status",
                    label="Suite de evaluacion",
                    current=evidence.evaluation_status,
                    target="passed",
                    missing=1,
                    severity="blocker",
                    description="La suite debe quedar en passed antes de promover entrenamiento.",
                    recommended_actions=[
                        "Ejecutar remediacion sobre casos fallidos.",
                        "Re-ejecutar Evaluation Loop y comparar regresiones.",
                    ],
                )
            )

        evaluation_score = evidence.evaluation_score or 0
        score_gap = max(request.target_evaluation_score - evaluation_score, 0)
        if score_gap:
            gaps.append(
                TrainingEvidenceGap(
                    key="evaluation_score",
                    label="Score de evaluacion",
                    current=evaluation_score,
                    target=request.target_evaluation_score,
                    missing=score_gap,
                    severity="blocker" if score_gap > 5 else "warning",
                    blocking=True,
                    description="El score de evaluacion todavia no alcanza el umbral de promocion.",
                    recommended_actions=[
                        "Atacar primero los casos con menor score.",
                        "Guardar ejemplos corregidos solo con revision humana.",
                    ],
                )
            )

        failed_cases = max(evidence.total_cases - evidence.passed_cases, 0)
        if failed_cases:
            gaps.append(
                TrainingEvidenceGap(
                    key="failed_cases",
                    label="Casos fallidos",
                    current=evidence.passed_cases,
                    target=evidence.total_cases,
                    missing=failed_cases,
                    severity="blocker",
                    description="Todos los casos de evaluacion deben pasar sin regresiones.",
                    recommended_actions=[
                        "Usar el plan de remediacion para cada caso fallido.",
                        "Aceptar outcomes solo si el caso objetivo mejora sin degradar otros.",
                    ],
                )
            )

        usable_gap = max(request.target_usable_examples - evidence.usable_examples, 0)
        if usable_gap:
            gaps.append(
                TrainingEvidenceGap(
                    key="usable_examples",
                    label="Ejemplos curados utiles",
                    current=evidence.usable_examples,
                    target=request.target_usable_examples,
                    missing=usable_gap,
                    severity="blocker",
                    description="El dataset necesita mas ejemplos curados antes de preflight.",
                    recommended_actions=[
                        "Convertir decisiones tecnicas reales en ejemplos corregidos.",
                        "Exportar curation y revisar duplicados antes de entrenar.",
                    ],
                )
            )

        corrected_gap = max(
            request.target_corrected_examples - evidence.corrected_examples,
            0,
        )
        if corrected_gap:
            gaps.append(
                TrainingEvidenceGap(
                    key="corrected_examples",
                    label="Correcciones humanas",
                    current=evidence.corrected_examples,
                    target=request.target_corrected_examples,
                    missing=corrected_gap,
                    severity="blocker",
                    description="Las correcciones humanas son evidencia fuerte de comportamiento deseado.",
                    recommended_actions=[
                        "Corregir respuestas flojas en vez de marcarlas solo como buenas.",
                        "Priorizar casos de seguridad, razonamiento e infraestructura.",
                    ],
                )
            )

        accepted_gap = max(
            request.target_accepted_outcomes - evidence.accepted_outcomes,
            0,
        )
        if accepted_gap:
            has_outcome_history = bool(gate.outcome_review and gate.outcome_review.available)
            gaps.append(
                TrainingEvidenceGap(
                    key="accepted_outcomes",
                    label="Outcomes aceptados",
                    current=evidence.accepted_outcomes,
                    target=request.target_accepted_outcomes,
                    missing=accepted_gap,
                    severity="blocker" if has_outcome_history else "warning",
                    blocking=has_outcome_history,
                    description="Conviene tener al menos una remediacion aceptada como evidencia de mejora.",
                    recommended_actions=[
                        "Aplicar una remediacion con confirmacion humana.",
                        "Re-ejecutar evaluacion y aceptar solo si no hay regresion.",
                    ],
                )
            )

        if evidence.regression_outcomes:
            gaps.append(
                TrainingEvidenceGap(
                    key="regression_outcomes",
                    label="Regresiones abiertas",
                    current=evidence.regression_outcomes,
                    target=0,
                    missing=evidence.regression_outcomes,
                    severity="blocker",
                    description="No se puede promover entrenamiento con regresiones abiertas.",
                    recommended_actions=[
                        "Revertir o corregir remediaciones que degradaron casos.",
                        "Re-ejecutar Evaluation Loop antes de volver a medir.",
                    ],
                )
            )

        if evidence.pending_outcomes:
            gaps.append(
                TrainingEvidenceGap(
                    key="pending_outcomes",
                    label="Outcomes pendientes",
                    current=evidence.pending_outcomes,
                    target=0,
                    missing=evidence.pending_outcomes,
                    severity="blocker",
                    description="Las remediaciones pendientes deben verificarse antes de promocion.",
                    recommended_actions=[
                        "Re-ejecutar Evaluation Loop.",
                        "Clasificar cada outcome como accepted, blocked o regression.",
                    ],
                )
            )

        return gaps

    def _candidates(
        self,
        request: TrainingEvidenceBuilderRequest,
        gate: TrainingPromotionGate,
        remediation_plan: EvaluationRemediationPlan | None,
    ) -> list[TrainingEvidenceCandidate]:
        candidates: list[TrainingEvidenceCandidate] = []
        evidence = gate.evidence

        if not gate.allowed and gate.latest_report is None:
            candidates.append(
                TrainingEvidenceCandidate(
                    candidate_id=self._candidate_id("eval"),
                    kind="run_evaluation",
                    title="Crear baseline de evaluacion",
                    rationale="Sin baseline no se puede medir mejora ni desbloquear promotion gate.",
                    expected_impact=["evaluation_status", "evaluation_score"],
                    next_actions=["Ejecutar /evaluations/run."],
                )
            )

        if remediation_plan and remediation_plan.items:
            for item in remediation_plan.items:
                candidates.append(self._candidate_from_remediation(item, request))

        usable_gap = max(request.target_usable_examples - evidence.usable_examples, 0)
        if usable_gap:
            candidates.append(
                TrainingEvidenceCandidate(
                    candidate_id=self._candidate_id("dataset"),
                    kind="collect_curated_examples",
                    title=f"Agregar {usable_gap} ejemplos curados utiles",
                    rationale="El dataset curado todavia es pequeno para un preflight confiable.",
                    expected_impact=["usable_examples", "curation_ready"],
                    next_actions=[
                        "Guardar feedback bueno/corregido desde el Workbench.",
                        "Ejecutar curation preview y export cuando el score promedio sea estable.",
                    ],
                )
            )

        corrected_gap = max(
            request.target_corrected_examples - evidence.corrected_examples,
            0,
        )
        if corrected_gap:
            candidates.append(
                TrainingEvidenceCandidate(
                    candidate_id=self._candidate_id("correction"),
                    kind="collect_human_corrections",
                    title=f"Crear {corrected_gap} correcciones humanas",
                    rationale="Las correcciones humanas pesan mas que ejemplos sinteticos o marcados como good.",
                    expected_impact=["corrected_examples", "dataset_quality"],
                    next_actions=[
                        "Corregir respuestas reales del chat con respuesta ideal.",
                        "Evitar duplicados exactos y respuestas genericas.",
                    ],
                )
            )

        if (
            gate.outcome_review
            and not gate.outcome_review.available
            and remediation_plan
            and remediation_plan.items
        ):
            candidates.append(
                TrainingEvidenceCandidate(
                    candidate_id=self._candidate_id("outcome"),
                    kind="accept_remediation_outcome",
                    title="Generar primer outcome aceptado",
                    rationale="El promotion gate necesita evidencia de mejora aplicada y verificada.",
                    expected_impact=["accepted_outcomes"],
                    next_actions=[
                        "Aplicar una remediacion con confirmacion exacta.",
                        "Re-ejecutar evaluacion y aceptar solo si no hay regresion.",
                    ],
                )
            )

        return candidates

    def _candidate_from_remediation(
        self,
        item: EvaluationRemediationItem,
        request: TrainingEvidenceBuilderRequest,
    ) -> TrainingEvidenceCandidate:
        return TrainingEvidenceCandidate(
            candidate_id=self._candidate_id(item.case_id),
            kind="evaluation_remediation",
            title=f"Remediar {item.case_id}",
            rationale=item.diagnosis,
            expected_impact=[
                "evaluation_status",
                "evaluation_score",
                "corrected_examples",
                "accepted_outcomes",
            ],
            source_case_id=item.case_id,
            proposed_learning_example=(
                item.proposed_learning_example if request.include_candidate_examples else None
            ),
            next_actions=[
                "Revisar proposed_learning_example.",
                "Aplicar remediacion con confirmacion humana.",
                "Re-ejecutar Evaluation Loop y bloquear si hay regresion.",
            ],
        )

    def _evidence_score(
        self,
        request: TrainingEvidenceBuilderRequest,
        gate: TrainingPromotionGate,
        gaps: list[TrainingEvidenceGap],
    ) -> int:
        evidence = gate.evidence
        score = 0
        if evidence.evaluation_status == "passed":
            score += 20
        score += round(min((evidence.evaluation_score or 0) / request.target_evaluation_score, 1) * 20)
        score += round(min(evidence.usable_examples / request.target_usable_examples, 1) * 20)
        if request.target_corrected_examples:
            score += round(
                min(evidence.corrected_examples / request.target_corrected_examples, 1) * 15
            )
        else:
            score += 15
        if request.target_accepted_outcomes:
            score += round(
                min(evidence.accepted_outcomes / request.target_accepted_outcomes, 1) * 15
            )
        else:
            score += 15
        if evidence.total_cases:
            score += round(min(evidence.passed_cases / evidence.total_cases, 1) * 10)

        blocking_penalty = min(sum(5 for gap in gaps if gap.blocking), 30)
        return max(0, min(100, score - blocking_penalty))

    def _next_actions(
        self,
        gaps: list[TrainingEvidenceGap],
        candidates: list[TrainingEvidenceCandidate],
    ) -> list[str]:
        actions: list[str] = []
        for gap in gaps[:3]:
            actions.extend(gap.recommended_actions[:1])
        for candidate in candidates[:2]:
            actions.append(candidate.next_actions[0])
        actions.append("Revisar Training Evidence Builder antes de repetir dry run.")
        return actions

    def _candidate_id(self, key: str) -> str:
        normalized = "".join(char if char.isalnum() else "-" for char in key.lower()).strip("-")
        return f"ev-{normalized[:36]}-{uuid4().hex[:6]}"


training_evidence_builder_service = TrainingEvidenceBuilderService()
