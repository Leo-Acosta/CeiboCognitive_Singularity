from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ceibo_core.models.schemas import SpeechCognitionTrace


@dataclass(frozen=True)
class SpeechCognitionInput:
    raw_transcript: str
    language: str = "es-AR"
    transcription_confidence: float = 1.0
    audio_metadata: dict[str, Any] = field(default_factory=dict)
    detected_pauses: list[float] = field(default_factory=list)
    duration_seconds: float | None = None
    source: str = "simulated"


class HumanSpeechCognitionLayerService:
    """Turns human speech transcripts into safe cognitive input.

    This service is ASR-provider agnostic. It does not read microphone input and
    does not infer clinical or personality traits from voice.
    """

    disfluency_tokens = ("eh", "em", "mmm", "este", "tipo", "o sea", "digamos")
    urgency_tokens = ("urgente", "ya", "ahora", "rapido", "rápido", "inmediato")
    confusion_tokens = ("no entiendo", "me perdi", "me perdí", "no me queda claro", "explicamelo")
    frustration_tokens = ("no anda", "no funciona", "podrido", "harto", "probé", "probe", "tres veces")
    step_tokens = ("despacio", "paso a paso", "explicame bien", "no me tires todo junto")
    vague_tokens = ("eso", "esto", "algo", "cosa", "ahi", "ahí", "arreglalo")

    def process(self, speech_input: SpeechCognitionInput | dict[str, Any]) -> SpeechCognitionTrace:
        if isinstance(speech_input, dict):
            speech_input = SpeechCognitionInput(**speech_input)
        raw = speech_input.raw_transcript.strip()
        normalized = self._normalize(raw)
        speech_markers = self._markers(normalized)
        disfluencies = self._disfluencies(normalized)
        urgency = [token for token in self.urgency_tokens if token in normalized]
        clarity = self._clarity_level(normalized, speech_input.transcription_confidence, disfluencies)
        ambiguity = self._ambiguity_level(normalized, speech_input.transcription_confidence)
        should_repeat = speech_input.transcription_confidence < 0.58 or clarity == "low"
        should_slow = bool(urgency or self._contains(normalized, self.confusion_tokens + self.frustration_tokens))

        return SpeechCognitionTrace(
            raw_transcript=raw,
            normalized_transcript=normalized,
            language=speech_input.language,
            transcription_confidence=round(max(0, min(1, speech_input.transcription_confidence)), 2),
            source=speech_input.source,
            audio_metadata=self._safe_audio_metadata(speech_input.audio_metadata),
            speech_markers=speech_markers,
            possible_disfluencies=disfluencies,
            detected_pauses=speech_input.detected_pauses[:8],
            duration_seconds=speech_input.duration_seconds,
            urgency_markers=urgency[:5],
            clarity_level=clarity,
            ambiguity_level=ambiguity,
            handoff_to_dialogue_orchestrator=not should_repeat,
            recommended_processing_mode="request_repetition" if should_repeat else "dialogue_orchestrator",
            should_request_repetition=should_repeat,
            should_slow_down_response=should_slow or any(pause >= 1.2 for pause in speech_input.detected_pauses),
            safety_notes=self._safety_notes(should_repeat),
        )

    def _markers(self, normalized: str) -> list[str]:
        markers: list[str] = []
        if self._contains(normalized, self.confusion_tokens):
            markers.append("explicit_confusion")
        if self._contains(normalized, self.frustration_tokens):
            markers.append("explicit_frustration")
        if self._contains(normalized, self.step_tokens):
            markers.append("step_by_step_request")
        if self._contains(normalized, self.urgency_tokens):
            markers.append("urgency")
        if normalized.endswith("?"):
            markers.append("question")
        return markers

    def _disfluencies(self, normalized: str) -> list[str]:
        return [token for token in self.disfluency_tokens if f" {token} " in f" {normalized} "][:6]

    def _clarity_level(self, normalized: str, confidence: float, disfluencies: list[str]) -> str:
        if not normalized or confidence < 0.58:
            return "low"
        if confidence < 0.78 or len(disfluencies) >= 3:
            return "medium"
        if self._contains(normalized, self.confusion_tokens):
            return "medium"
        return "clear"

    def _ambiguity_level(self, normalized: str, confidence: float) -> str:
        vague_count = sum(1 for token in self.vague_tokens if token in normalized)
        if confidence < 0.58 or vague_count >= 3:
            return "high"
        if confidence < 0.78 or vague_count >= 1:
            return "medium"
        return "low"

    def _safe_audio_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        allowed = {"sample_rate", "channels", "codec", "provider", "model"}
        return {key: metadata[key] for key in allowed if key in metadata}

    def _safety_notes(self, should_repeat: bool) -> list[str]:
        notes = [
            "do not infer clinical state from speech",
            "do not infer personality from voice",
            "do not store momentary speech emotion as memory",
        ]
        if should_repeat:
            notes.append("low confidence transcript requires confirmation")
        return notes

    def _normalize(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def _contains(self, value: str, needles: Iterable[str]) -> bool:
        return any(needle in value for needle in needles)


human_speech_cognition_layer_service = HumanSpeechCognitionLayerService()
