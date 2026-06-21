from __future__ import annotations

from typing import List

from ceibo_core.models.schemas import SpeechCognitionTrace
from ceibo_core.services.dialogue_orchestrator import dialogue_orchestrator_service


class HumanConversationService:
    async def respond(
        self,
        user_message: str,
        conversation_history: List[dict] | None = None,
        memory_context: str | None = None,
        mode: str = "human_persona",
        speech_cognition_trace: SpeechCognitionTrace | dict | None = None,
    ) -> dict:
        result = await dialogue_orchestrator_service.respond(
            user_message=user_message,
            conversation_history=conversation_history,
            memory_context=memory_context,
            mode=mode,
            speech_cognition_trace=speech_cognition_trace,
        )
        return {
            "response": result.response,
            "safety_checked": result.trace.safety_checked,
            "dialogue_trace": result.trace.model_dump(mode="json"),
        }


human_conversation_service = HumanConversationService()
