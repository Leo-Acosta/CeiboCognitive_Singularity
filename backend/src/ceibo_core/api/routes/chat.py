from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.agents.registry import agent_registry
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import AgentRole, ChatRequest, ChatResponse
from ceibo_core.services.conversations import conversation_store
from ceibo_core.services.event_bus import event_bus
from ceibo_core.services.autobiographical_memory import autobiographical_memory_service
from ceibo_core.services.memory import memory_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
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

    enriched_request = request.model_copy(
        update={
            "session_id": session_id,
            "metadata": {
                **request.metadata,
                "memory_context": memory_context,
            },
        }
    )
    orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]
    response = await orchestrator.handle_chat(enriched_request)

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
    await conversation_store.audit(
        db,
        user_id=request.user_id,
        event_type="chat.completion",
        actor=response.agent.value,
        payload={"session_id": session_id, "trace_id": str(response.trace_id)},
    )
    await event_bus.publish("ceibo.chat.completed", response.model_dump_json().encode())
    return response
