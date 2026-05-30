from fastapi import APIRouter

from ceibo_core.models.schemas import MemoryHealth, MemoryRecord, MemoryRememberRequest, MemorySearchResponse
from ceibo_core.services.memory import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/health", response_model=MemoryHealth)
async def memory_health() -> MemoryHealth:
    return await memory_service.status()


@router.post("/remember", response_model=MemoryRecord)
async def remember(request: MemoryRememberRequest) -> MemoryRecord:
    return await memory_service.remember(
        session_id=request.session_id,
        text=request.content,
        user_id=request.user_id,
        metadata=request.metadata,
    )


@router.get("/search", response_model=MemorySearchResponse)
async def search_memory(session_id: str, query: str, limit: int = 5) -> MemorySearchResponse:
    matches = await memory_service.retrieve(session_id=session_id, query=query, limit=limit)
    return MemorySearchResponse(session_id=session_id, query=query, matches=matches)
