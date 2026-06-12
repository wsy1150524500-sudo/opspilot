from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ops_agent.ai.agent import AgentRunner
from ops_agent.ai.models import AgentRunResult
from ops_agent.web.deps import get_agent_runner
from ops_agent.web.schemas import AiChatRequest

router = APIRouter(tags=["ai"])

# TODO: This endpoint lets a remote caller drive an LLM that can call ops
# tools (including SSH if enabled). Before any non-local deployment, add
# authentication (API key / OAuth), tighten CORS, and keep SSH tooling
# disabled or strictly allowlisted.


def _get_runner_dependency() -> AgentRunner:
    try:
        return get_agent_runner()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI agent not configured: {e}",
        )


@router.post("/ai/chat", response_model=AgentRunResult)
def ai_chat_endpoint(
    req: AiChatRequest,
    runner: AgentRunner = Depends(_get_runner_dependency),
) -> AgentRunResult:
    return runner.run(req.message, history=req.history)
