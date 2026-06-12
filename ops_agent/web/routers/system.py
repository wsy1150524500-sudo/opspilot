from __future__ import annotations

from fastapi import APIRouter, Depends

from ops_agent.core.models import SystemSnapshot
from ops_agent.web.deps import get_system_service
from ops_agent.services.system_service import SystemService

router = APIRouter(tags=["system"])


@router.get("/system", response_model=SystemSnapshot)
def get_system(
    svc: SystemService = Depends(get_system_service),
) -> SystemSnapshot:
    return svc.snapshot()
