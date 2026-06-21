from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.agents.registry import agent_registry
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import (
    AgentRole,
    ChatRequest,
    ChatResponse,
    CognitiveReflectionRequest,
    SpeechCognitionTrace,
)
from ceibo_core.services.cognitive_reflection import cognitive_reflection_service
from ceibo_core.services.conversations import conversation_store
from ceibo_core.services.event_bus import event_bus
from ceibo_core.services.autobiographical_memory import autobiographical_memory_service
from ceibo_core.services.memory import memory_service
from ceibo_core.core.config import settings
from ceibo_core.services.human_conversation import human_conversation_service
from ceibo_core.services.human_speech_cognition_layer import (
    SpeechCognitionInput,
    human_speech_cognition_layer_service,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
    speech_cognition_trace = _speech_trace_from_metadata(request)
    recent_messages = await conversation_store.recent_messages(db, session_id=session_id)
    semantic_memory = await memory_service.retrieve(session_id=session_id, query=request.message)
    autobiographical_context = await autobiographical_memory_service.context_for(request.message)
    memory_context = [
        *autobiographical_context,
        *recent_messages,
        *[record.content for record in semantic_memory],
    ]

    await conversation_store.append_message(
        db,
        session_id=session_id,
        user_id=request.user_id,
        role="user",
        content=request.message,
        metadata=request.metadata,
    )

    # Enrich request metadata with memory context
    enriched_request = request.model_copy(
        update={
            "session_id": session_id,
            "metadata": {
                **request.metadata,
                "memory_context": memory_context,
            },
        }
    )

    # If CEIBO is configured in human_persona conversation mode, use the human conversation
    # service which builds persona prompts, manages memory and calls the LLM gateway.
    if settings.ceibo_conversation_mode == "human_persona":
        convo_resp = await human_conversation_service.respond(
            user_message=request.message,
            conversation_history=recent_messages,
            memory_context="\n".join(memory_context),
            mode=settings.ceibo_conversation_mode,
            speech_cognition_trace=speech_cognition_trace,
        )
        # Build a ChatResponse-like structure to keep compatibility
        response_text = convo_resp.get("response", "")
        response = ChatResponse(
            response=response_text,
            agent=AgentRole.CORE_ORCHESTRATOR,
            session_id=session_id,
            memory_context=memory_context,
            dialogue_trace=convo_resp.get("dialogue_trace"),
            provider=settings.default_llm_provider,
            model=settings.ollama_chat_model if settings.default_llm_provider == "ollama" else None,
            local_only=settings.local_only_mode,
            safety_checked=True,
        )
    else:
        orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]
        response = await orchestrator.handle_chat(enriched_request)

    # Normalize provider metadata so API clients receive expected runtime fields.
    response = response.model_copy(update={
        "provider": response.provider or settings.default_llm_provider,
        "model": response.model or (settings.ollama_chat_model if settings.default_llm_provider == "ollama" else None),
        "local_only": response.local_only or settings.local_only_mode,
        "safety_checked": response.safety_checked or True,
    })

    await conversation_store.append_message(
        db,
        session_id=session_id,
        user_id=request.user_id,
        role="assistant",
        content=response.response,
        agent=response.agent.value,
        metadata={"trace_id": str(response.trace_id)},
    )
    await memory_service.remember(
        session_id,
        f"user: {request.message}",
        user_id=request.user_id,
        metadata={"role": "user"},
    )
    await memory_service.remember(
        session_id,
        f"assistant: {response.response}",
        user_id=request.user_id,
        metadata={"role": "assistant", "trace_id": str(response.trace_id)},
    )
    dialogue_trace = response.dialogue_trace.model_dump(mode="json") if response.dialogue_trace else None
    reflection_metadata = {
        "trace_id": str(response.trace_id),
        "agent": response.agent.value,
    }
    reflection_intents: list[str] = []
    if dialogue_trace:
        analysis = dialogue_trace.get("analysis", {})
        reflection_metadata["dialogue_trace"] = dialogue_trace
        reflection_intents.extend(
            item
            for item in (
                analysis.get("intent"),
                analysis.get("cognitive_route"),
                analysis.get("safety_class"),
            )
            if item
        )
        if dialogue_trace.get("tool_used"):
            reflection_intents.append(f"tool:{dialogue_trace['tool_used']}")

    reflection = await cognitive_reflection_service.reflect_after_response(
        CognitiveReflectionRequest(
            prompt=request.message,
            response=response.response,
            source="chat",
            user_id=request.user_id,
            session_id=session_id,
            intents=reflection_intents,
            used_context=bool(memory_context),
            memory_context=memory_context,
            metadata=reflection_metadata,
        )
    )
    await conversation_store.audit(
        db,
        user_id=request.user_id,
        event_type="chat.completion",
        actor=response.agent.value,
        payload={
            "session_id": session_id,
            "trace_id": str(response.trace_id),
            "reflection_id": reflection.reflection_id,
            "reflection_score": reflection.score,
        },
    )
    await event_bus.publish("ceibo.chat.completed", response.model_dump_json().encode())
    return response


def _speech_trace_from_metadata(request: ChatRequest) -> SpeechCognitionTrace | None:
    trace = request.metadata.get("speech_cognition_trace")
    if isinstance(trace, dict):
        try:
            return SpeechCognitionTrace.model_validate(trace)
        except Exception:
            return None

    speech_input = request.metadata.get("speech_input")
    if isinstance(speech_input, dict):
        try:
            payload = {"raw_transcript": request.message, **speech_input}
            return human_speech_cognition_layer_service.process(SpeechCognitionInput(**payload))
        except Exception:
            return None

    if request.metadata.get("source") == "simulated_speech":
        try:
            return human_speech_cognition_layer_service.process(
                SpeechCognitionInput(
                    raw_transcript=request.message,
                    language=str(request.metadata.get("language", "es-AR")),
                    transcription_confidence=float(request.metadata.get("transcription_confidence", 1.0)),
                    source="simulated_speech",
                )
            )
        except Exception:
            return None
    return None
