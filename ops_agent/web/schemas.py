from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ops_agent.core.models import HostConfig
from ops_agent.ai.models import ChatMessage


class LogAnalyzeRequest(BaseModel):
    path: str
    patterns: list[str] = Field(default_factory=list)
    levels: list[str] | None = None
    since: datetime | None = None
    max_matches: int = 1000


class BatchRunRequest(BaseModel):
    command: str
    hosts: list[HostConfig] = Field(default_factory=list)
    host_names: list[str] = Field(default_factory=list)


class AiChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
