from fastapi import APIRouter

from ceibo_core.models.schemas import DevCorePlanRequest, DevCorePlanResponse, DevCoreStatus
from ceibo_core.services.devcore import devcore_service

router = APIRouter(prefix="/devcore", tags=["devcore"])


@router.get("/status", response_model=DevCoreStatus)
async def devcore_status() -> DevCoreStatus:
    return devcore_service.status()


@router.post("/plan", response_model=DevCorePlanResponse)
async def plan_devcore_change(request: DevCorePlanRequest) -> DevCorePlanResponse:
    return devcore_service.plan(request)
