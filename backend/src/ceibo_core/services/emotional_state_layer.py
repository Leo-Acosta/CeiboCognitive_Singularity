from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ceibo_core.models.schemas import DialogueAnalysis, EmotionalStateTrace


@dataclass(frozen=True)
class EmotionalSignal:
    state: str
    weight: float
    evidence: str


class EmotionalStateLayerService:
    """Prudent conversational emotion signal layer.

    This layer does not diagnose, profile, or persist emotions. It only extracts
    weak conversational signals that can help CEIBO adjust tone and pacing for
    the current response.
    """

    forbidden_states = {
        "depression",
        "anxiety_disorder",
        "personality_disorder",
        "trauma",
        "unstable_personality",
        "clinical_diagnosis",
    }

    def assess(
        self,
        *,
        user_message: str,
        analysis: DialogueAnalysis,
        conversation_context: list[str] | None = None,
    ) -> EmotionalStateTrace:
        normalized = self._normalize(user_message)
        signals = self._signals(normalized, analysis)
        if not signals:
            return self._neutral_trace(analysis)

        scores: dict[str, float] = {}
        evidence_by_state: dict[str, list[str]] = {}
        for signal in signals:
            if signal.state in self.forbidden_states:
                continue
            scores[signal.state] = scores.get(signal.state, 0) + signal.weight
            evidence_by_state.setdefault(signal.state, []).append(signal.evidence)

        if not scores:
            return self._neutral_trace(analysis)

        primary_state = max(scores.items(), key=lambda item: item[1])[0]
        secondary_states = [
            state
            for state, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
            if state != primary_state and score >= 0.35
        ][:3]
        confidence = self._confidence(scores[primary_state], analysis)
        intensity = self._intensity(scores[primary_state], analysis)
        evidence = self._compact_evidence(evidence_by_state, primary_state, secondary_states)
        style = self._style(primary_state, secondary_states, analysis)
        should_ask = analysis.ambiguity_score >= 0.55 or "confusion" in {primary_state, *secondary_states}
        should_step = primary_state in {"frustration", "confusion", "urgency", "doubt"} or analysis.intent == "technical_build"
        should_slow = primary_state in {"frustration", "confusion", "anger", "fatigue", "doubt"}

        return EmotionalStateTrace(
            primary_state=primary_state,
            secondary_states=secondary_states,
            confidence=confidence,
            intensity=intensity,
            evidence=evidence,
            recommended_response_style=style,
            should_slow_down=should_slow,
            should_ask_clarifying_question=should_ask,
            should_offer_step_by_step=should_step,
            should_avoid_memory=self._should_avoid_memory(primary_state, secondary_states, analysis),
            safety_notes=self._safety_notes(primary_state, secondary_states, analysis),
        )

    def _signals(self, normalized: str, analysis: DialogueAnalysis) -> list[EmotionalSignal]:
        signals: list[EmotionalSignal] = []
        self._add_if_contains(
            signals,
            normalized,
            ("no anda", "no funciona", "nunca anda", "podrido", "harto", "frustrado", "trabado"),
            "frustration",
            0.7,
            "user reports repeated failure or blockage",
        )
        self._add_if_contains(
            signals,
            normalized,
            ("me perdi", "me perdí", "no entiendo", "confundido", "explicamelo bien", "no me queda claro"),
            "confusion",
            0.65,
            "user asks for clarity or reports confusion",
        )
        if "de ahora en adelante" not in normalized:
            self._add_if_contains(
                signals,
                normalized,
                ("urgente", "ya", "ahora", "rapido", "rápido", "inmediato"),
                "urgency",
                0.55,
                "user uses time pressure wording",
            )
        self._add_if_contains(
            signals,
            normalized,
            ("excelente", "perfecto", "me encanta", "buenisimo", "buenísimo", "vamos", "genial"),
            "enthusiasm",
            0.45,
            "user uses positive or energetic wording",
        )
        self._add_if_contains(
            signals,
            normalized,
            ("cansado", "agotado", "sin energia", "sin energía"),
            "fatigue",
            0.55,
            "user reports low energy conversationally",
        )
        self._add_if_contains(
            signals,
            normalized,
            ("no se", "no sé", "duda", "quizas", "quizás", "capaz", "tal vez"),
            "doubt",
            0.45,
            "user expresses uncertainty",
        )
        self._add_if_contains(
            signals,
            normalized,
            ("enojo", "enojado", "molesto", "bronca", "idiota", "inutil", "inútil", "mierda"),
            "anger",
            0.55,
            "user uses anger or aggressive wording",
        )
        self._add_if_contains(
            signals,
            normalized,
            ("me preocupa", "ansioso", "nervioso", "me apura", "tengo miedo"),
            "conversational_anxiety",
            0.45,
            "user signals concern or pressure in conversation",
        )
        self._add_if_contains(
            signals,
            normalized,
            ("gracias", "listo", "sirvio", "sirvió", "bien ahi", "bien ahí"),
            "satisfaction",
            0.4,
            "user signals satisfaction or closure",
        )
        self._add_if_contains(
            signals,
            normalized,
            ("no quiero", "prefiero que no", "no me convence", "resisto", "me cuesta"),
            "resistance",
            0.45,
            "user resists or pushes back",
        )
        if analysis.irony_likelihood >= 0.55 or self._contains(normalized, ("jaja", "jeje", "si claro", "claro seguro")):
            signals.append(EmotionalSignal("emotional_irony", 0.6, "irony or sarcasm markers are present"))
        if analysis.urgency_score >= 0.4:
            signals.append(EmotionalSignal("urgency", 0.35, "dialogue analysis detected urgency"))
        if analysis.emotional_tone == "frustracion_o_preocupacion":
            signals.append(EmotionalSignal("frustration", 0.35, "dialogue tone suggests frustration or concern"))
        if analysis.emotional_tone == "agresivo":
            signals.append(EmotionalSignal("anger", 0.45, "dialogue tone suggests aggressive wording"))
        return signals

    def _neutral_trace(self, analysis: DialogueAnalysis) -> EmotionalStateTrace:
        should_ask = analysis.ambiguity_score >= 0.55
        return EmotionalStateTrace(
            primary_state="neutral",
            secondary_states=[],
            confidence=0.45,
            intensity="low",
            evidence=["no strong emotional signal detected"],
            recommended_response_style="clear_neutral",
            should_slow_down=False,
            should_ask_clarifying_question=should_ask,
            should_offer_step_by_step=analysis.intent == "technical_build",
            should_avoid_memory=analysis.memory_policy != "candidate_autobiographical_memory",
            safety_notes=["weak signal only", "do not infer personality or diagnosis"],
        )

    def _confidence(self, primary_score: float, analysis: DialogueAnalysis) -> float:
        confidence = 0.35 + primary_score * 0.45
        if analysis.ambiguity_score >= 0.6:
            confidence -= 0.08
        return round(max(0.25, min(0.86, confidence)), 2)

    def _intensity(self, primary_score: float, analysis: DialogueAnalysis) -> str:
        score = primary_score + analysis.urgency_score * 0.3
        if score >= 1.15:
            return "high"
        if score >= 0.65:
            return "medium"
        return "low"

    def _style(self, primary_state: str, secondary_states: list[str], analysis: DialogueAnalysis) -> str:
        states = {primary_state, *secondary_states}
        if {"frustration", "confusion"} <= states:
            return "calm_step_by_step"
        if "frustration" in states:
            return "calm_step_by_step"
        if "urgency" in states:
            return "direct_prioritized"
        if "anger" in states:
            return "calm_less_confrontational"
        if "enthusiasm" in states:
            return "concise_energetic"
        if "fatigue" in states:
            return "low_cognitive_load"
        if "doubt" in states or "confusion" in states:
            return "clarifying_step_by_step"
        if "emotional_irony" in states:
            return "light_reflective_not_literal"
        if analysis.intent == "technical_build":
            return "technical_step_by_step"
        return "clear_neutral"

    def _should_avoid_memory(
        self,
        primary_state: str,
        secondary_states: list[str],
        analysis: DialogueAnalysis,
    ) -> bool:
        if analysis.memory_policy == "candidate_autobiographical_memory":
            return False
        transient_states = {
            "frustration",
            "confusion",
            "urgency",
            "enthusiasm",
            "fatigue",
            "doubt",
            "anger",
            "conversational_anxiety",
            "satisfaction",
            "resistance",
            "emotional_irony",
        }
        return primary_state in transient_states or bool(transient_states & set(secondary_states))

    def _safety_notes(
        self,
        primary_state: str,
        secondary_states: list[str],
        analysis: DialogueAnalysis,
    ) -> list[str]:
        notes = ["do not diagnose", "do not store transient emotional state"]
        states = {primary_state, *secondary_states}
        if "conversational_anxiety" in states:
            notes.append("treat anxiety wording as conversational signal only")
        if "emotional_irony" in states:
            notes.append("do not overinterpret sarcasm")
        if analysis.safety_class != "normal":
            notes.append("respect safety supervisor classification")
        return notes

    def _compact_evidence(
        self,
        evidence_by_state: dict[str, list[str]],
        primary_state: str,
        secondary_states: list[str],
    ) -> list[str]:
        evidence: list[str] = []
        for state in [primary_state, *secondary_states]:
            for item in evidence_by_state.get(state, []):
                if item not in evidence:
                    evidence.append(item)
        return evidence[:4]

    def _add_if_contains(
        self,
        signals: list[EmotionalSignal],
        normalized: str,
        needles: tuple[str, ...],
        state: str,
        weight: float,
        evidence: str,
    ) -> None:
        if self._contains(normalized, needles):
            signals.append(EmotionalSignal(state, weight, evidence))

    def _normalize(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def _contains(self, value: str, needles: Iterable[str]) -> bool:
        return any(needle in value for needle in needles)


emotional_state_layer_service = EmotionalStateLayerService()
