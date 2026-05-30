from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ceibo_core.agents.registry import agent_registry
from ceibo_core.models.schemas import AgentRole, ChatRequest

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    orchestrator = agent_registry[AgentRole.CORE_ORCHESTRATOR]
    try:
        while True:
            message = await websocket.receive_text()
            response = await orchestrator.handle_chat(ChatRequest(message=message))
            await websocket.send_json(response.model_dump(mode="json"))
    except WebSocketDisconnect:
        return
