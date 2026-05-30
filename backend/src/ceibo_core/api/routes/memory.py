from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import (
    KnowledgeItemRecord,
    KnowledgeItemRequest,
    KnowledgeSearchResponse,
    KnowledgeStatus,
    MemoryHealth,
    MemoryRecord,
    MemoryRememberRequest,
    MemorySearchResponse,
)
from ceibo_core.services.memory import knowledge_service, memory_service

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


@router.get("/knowledge/status", response_model=KnowledgeStatus)
async def knowledge_status(db: AsyncSession = Depends(get_db)) -> KnowledgeStatus:
    return await knowledge_service.status(db)


@router.post("/knowledge", response_model=KnowledgeItemRecord)
async def add_knowledge(
    request: KnowledgeItemRequest,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeItemRecord:
    return await knowledge_service.add(db, request)


@router.get("/knowledge", response_model=list[KnowledgeItemRecord])
async def list_knowledge(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeItemRecord]:
    return await knowledge_service.list_recent(db, limit=limit)


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    query: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSearchResponse:
    matches = await knowledge_service.search(db, query=query, limit=limit)
    return KnowledgeSearchResponse(query=query, matches=matches)
