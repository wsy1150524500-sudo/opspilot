from __future__ import annotations

from fastapi import APIRouter, Depends

from ops_agent.core.models import CommandResult
from ops_agent.web.deps import get_config, get_ssh_service
from ops_agent.web.schemas import BatchRunRequest
from ops_agent.services.ssh_service import SSHService

router = APIRouter(tags=["ssh"])

# TODO: This endpoint executes arbitrary commands on remote hosts.
# Before any non-local deployment, add authentication (API key / OAuth)
# and restrict CORS origins. Credentials should come from server-side
# config (config/hosts.yaml) rather than request bodies where possible.


@router.post("/ssh/run", response_model=list[CommandResult])
def run_batch(
    req: BatchRunRequest,
    svc: SSHService = Depends(get_ssh_service),
) -> list[CommandResult]:
    config = get_config()
    return svc.run_batch(req, config)
