from __future__ import annotations

from ceibo_core.models.schemas import DialogueAnalysis, DialogueOrchestrationTrace, SpokenResponsePlan


class SpokenResponsePlannerService:
    """Plans how a text response should be shaped for spoken delivery."""

    def plan(
        self,
        *,
        analysis: DialogueAnalysis,
        dialogue_trace: DialogueOrchestrationTrace | None = None,
        complexity: str = "medium",
    ) -> SpokenResponsePlan:
        speech = dialogue_trace.speech_cognition_trace if dialogue_trace else None
        emotional = dialogue_trace.emotional_state_trace if dialogue_trace else None
        needs_steps = bool(
            (speech and "step_by_step_request" in speech.speech_markers)
            or (emotional and emotional.should_offer_step_by_step)
            or analysis.intent == "technical_build"
        )
        urgent = bool((speech and speech.urgency_markers) or analysis.urgency_score >= 0.4)
        low_clarity = bool(speech and speech.clarity_level in {"low", "medium"})
        should_confirm = bool(speech and (speech.should_request_repetition or low_clarity))

        response_mode = self._response_mode(analysis)
        style = self._style(response_mode, needs_steps, emotional)
        pace = "slow" if (needs_steps or low_clarity or (emotional and emotional.should_slow_down)) else "normal"
        if urgent and not low_clarity:
            pace = "measured"

        return SpokenResponsePlan(
            response_mode=response_mode,
            spoken_style=style,
            pace=pace,
            structure="numbered_steps" if needs_steps else "short_paragraphs",
            should_summarize_first=needs_steps or complexity == "high",
            should_use_short_sentences=True,
            should_confirm_understanding=should_confirm,
            should_offer_next_step=True,
            max_sentence_length="short" if needs_steps or low_clarity else "medium",
            avoid_overload=True,
            safety_notes=[
                "do not infer clinical state from speech",
                "avoid false emotionality",
                "do not simulate therapeutic bond",
            ],
        )

    def _response_mode(self, analysis: DialogueAnalysis) -> str:
        if analysis.intent in {"technical_build", "practical_tool_query"}:
            return "technical_explanation"
        if analysis.intent in {"memory_update", "memory_control"}:
            return "preference_confirmation"
        if analysis.cognitive_route == "human_dialogue":
            return "conversational_response"
        return "general_explanation"

    def _style(self, response_mode: str, needs_steps: bool, emotional) -> str:
        if needs_steps and emotional and emotional.primary_state in {"frustration", "confusion"}:
            return "calm_clear_step_by_step"
        if needs_steps:
            return "clear_step_by_step"
        if response_mode == "preference_confirmation":
            return "brief_confirming"
        if emotional and emotional.primary_state == "enthusiasm":
            return "concise_energetic"
        return "clear_natural"


spoken_response_planner_service = SpokenResponsePlannerService()
