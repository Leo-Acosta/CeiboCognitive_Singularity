from ceibo_core.models.schemas import (
    HumanFeedbackStudioExample,
    HumanFeedbackStudioReport,
    HumanFeedbackStudioRequest,
    LearningEventRequest,
    LearningEventResponse,
    TrainingDatasetStats,
    TrainingExample,
    TrainingFeedbackRating,
)
from ceibo_core.services.training_data import training_data_service


TARGET_TOTAL_EXAMPLES = 100
TARGET_CORRECTED_EXAMPLES = 25
TARGET_GOOD_EXAMPLES = 50


class HumanFeedbackStudioService:
    async def status(self, limit: int = 8) -> HumanFeedbackStudioReport:
        stats = await training_data_service.stats()
        recent_examples = await training_data_service.list_examples(limit=limit)
        return self._report(
            stats=stats,
            recent_examples=recent_examples,
            saved_event=None,
        )

    async def save_review(
        self,
        request: HumanFeedbackStudioRequest,
    ) -> HumanFeedbackStudioReport:
        metadata = {
            "human_feedback_studio": True,
            "intent": request.intent,
            "risk_level": request.risk_level,
            "policy_action": request.policy_action,
            "review_notes": request.notes,
            "sprint": "40",
        }
        event = await training_data_service.append_learning_event(
            LearningEventRequest(
                instruction=request.instruction,
                assistant_response=request.assistant_response,
                corrected_response=request.corrected_response,
                rating=request.rating,
                source=request.source,
                tags=[
                    *request.tags,
                    "human-feedback-studio",
                    f"studio-rating:{request.rating.value}",
                ],
                metadata={key: value for key, value in metadata.items() if value not in (None, "")},
            )
        )
        stats = await training_data_service.stats()
        recent_examples = await training_data_service.list_examples(limit=8)
        return self._report(
            stats=stats,
            recent_examples=recent_examples,
            saved_event=event,
        )

    def _report(
        self,
        *,
        stats: TrainingDatasetStats,
        recent_examples: list[TrainingExample],
        saved_event: LearningEventResponse | None,
    ) -> HumanFeedbackStudioReport:
        corrected_count = stats.rating_counts.get(TrainingFeedbackRating.CORRECTED.value, 0)
        good_count = stats.rating_counts.get(TrainingFeedbackRating.GOOD.value, 0)
        bad_count = stats.rating_counts.get(TrainingFeedbackRating.BAD.value, 0)
        progress = {
            "total_examples": stats.total_examples,
            "good_examples": good_count,
            "corrected_examples": corrected_count,
            "bad_examples": bad_count,
        }
        targets = {
            "total_examples": TARGET_TOTAL_EXAMPLES,
            "good_examples": TARGET_GOOD_EXAMPLES,
            "corrected_examples": TARGET_CORRECTED_EXAMPLES,
        }
        warnings = self._warnings(stats)
        status = self._status(stats, corrected_count)
        summary = self._summary(status, progress)
        return HumanFeedbackStudioReport(
            status=status,
            summary=summary,
            stats=stats,
            recent_examples=[self._example_preview(example) for example in reversed(recent_examples)],
            saved_event=saved_event,
            targets=targets,
            progress=progress,
            warnings=warnings,
            next_actions=self._next_actions(stats, corrected_count, saved_event),
        )

    def _status(self, stats: TrainingDatasetStats, corrected_count: int) -> str:
        if stats.total_examples >= TARGET_TOTAL_EXAMPLES and corrected_count >= TARGET_CORRECTED_EXAMPLES:
            return "ready_for_dataset_expansion_review"
        if corrected_count >= 3 and stats.total_examples >= 25:
            return "studio_collecting_high_quality_examples"
        if stats.total_examples > 0:
            return "studio_warming_up"
        return "studio_empty"

    def _summary(self, status: str, progress: dict[str, int]) -> str:
        if status == "ready_for_dataset_expansion_review":
            return "Human Feedback Studio ya tiene base suficiente para revisar expansion de dataset."
        if status == "studio_collecting_high_quality_examples":
            return "Human Feedback Studio tiene senales utiles; seguir priorizando correcciones humanas."
        if status == "studio_warming_up":
            return "Human Feedback Studio esta juntando experiencia propia revisada por humano."
        return "Human Feedback Studio espera la primera revision humana."

    def _warnings(self, stats: TrainingDatasetStats) -> list[str]:
        warnings: list[str] = []
        corrected_count = stats.rating_counts.get(TrainingFeedbackRating.CORRECTED.value, 0)
        good_count = stats.rating_counts.get(TrainingFeedbackRating.GOOD.value, 0)
        if corrected_count < 3:
            warnings.append("Faltan correcciones humanas; son mas valiosas que marcar respuestas buenas.")
        if good_count > corrected_count * 8 and good_count > 10:
            warnings.append("Hay muchas respuestas good frente a pocas corrected; revisar calidad antes de entrenar.")
        if stats.total_examples < 25:
            warnings.append("Dataset todavia chico para desbloquear entrenamiento.")
        return warnings

    def _next_actions(
        self,
        stats: TrainingDatasetStats,
        corrected_count: int,
        saved_event: LearningEventResponse | None,
    ) -> list[str]:
        actions: list[str] = []
        if saved_event and saved_event.saved:
            actions.append("Revisar curation preview para ver si el ejemplo queda util.")
        elif saved_event and not saved_event.saved:
            actions.append("Evitar duplicados: corregir con mas contexto o revisar el ejemplo existente.")
        if corrected_count < TARGET_CORRECTED_EXAMPLES:
            actions.append("Priorizar respuestas corregidas con version ideal escrita por humano.")
        if stats.total_examples < TARGET_TOTAL_EXAMPLES:
            actions.append("Construir ejemplos reales de decisiones, seguridad, robotica, memoria y codigo.")
        actions.append("No entrenar hasta que Evaluation y Promotion Gate esten en verde.")
        return list(dict.fromkeys(actions))

    def _example_preview(self, example: TrainingExample) -> HumanFeedbackStudioExample:
        return HumanFeedbackStudioExample(
            example_id=example.example_id,
            instruction=example.instruction[:180],
            response_preview=example.response[:220],
            rating=example.rating,
            source=example.source,
            quality_score=training_data_service._quality_score(example),
            tags=example.tags[:8],
            created_at=example.created_at,
        )


human_feedback_studio_service = HumanFeedbackStudioService()
