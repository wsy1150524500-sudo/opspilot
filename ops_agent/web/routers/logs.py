from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ops_agent.core.models import LogReport
from ops_agent.web.deps import get_log_service
from ops_agent.web.schemas import LogAnalyzeRequest
from ops_agent.services.log_service import LogService

router = APIRouter(tags=["logs"])


@router.post("/logs/analyze", response_model=LogReport)
def analyze_logs(
    req: LogAnalyzeRequest,
    svc: LogService = Depends(get_log_service),
) -> LogReport:
    try:
        return svc.analyze(req)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Log file not found: {req.path}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
