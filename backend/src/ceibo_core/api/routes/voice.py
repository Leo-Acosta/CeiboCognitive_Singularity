from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ceibo_core.core.security import get_auth_context
from ceibo_core.db.session import get_db
from ceibo_core.models.schemas import (
    AuthContext,
    SecurityAction,
    VoiceAuthorizationRequest,
    VoiceAuthorizationResponse,
    VoiceCommandRequest,
    VoiceCommandResponse,
    VoiceStatusResponse,
)
from ceibo_core.services.audit import audit_trail_service
from ceibo_core.services.voice_control import voice_control_service

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/status", response_model=VoiceStatusResponse)
async def voice_status(auth: AuthContext = Depends(get_auth_context)) -> VoiceStatusResponse:
    return voice_control_service.status()


@router.post("/authorize", response_model=VoiceAuthorizationResponse)
async def authorize_voice(
    request: VoiceAuthorizationRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> VoiceAuthorizationResponse:
    response = voice_control_service.authorize(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="voice.authorization",
        actor="ceibo_voice",
        action=SecurityAction.READ_STATUS,
        allowed=response.authorized,
        payload={
            "voice_user_id": request.user_id,
            "mode": response.mode,
            "authorized": response.authorized,
        },
    )
    return response


@router.post("/command", response_model=VoiceCommandResponse)
async def voice_command(
    request: VoiceCommandRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> VoiceCommandResponse:
    response = voice_control_service.command(request)
    await audit_trail_service.record(
        db,
        auth=auth,
        event_type="voice.command",
        actor="ceibo_voice",
        action=SecurityAction.RUN_DEVCORE_PLAN,
        allowed=response.accepted,
        payload={
            "voice_user_id": request.user_id,
            "accepted": response.accepted,
            "authorized": response.authorized,
            "requires_authorization": response.requires_authorization,
            "command": response.command,
        },
    )
    return response
