from fastapi import APIRouter, Depends

from ceibo_core.core.security import require_permission
from ceibo_core.models.schemas import CognitionState, SecurityAction
from ceibo_core.services.cognition import cognition_service

router = APIRouter(prefix="/cognition", tags=["cognition"])


@router.get("/state", response_model=CognitionState)
async def cognition_state(
    _allowed=Depends(require_permission(SecurityAction.READ_STATUS)),
) -> CognitionState:
    return await cognition_service.state()
