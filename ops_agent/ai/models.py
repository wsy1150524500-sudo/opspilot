from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator


class ProviderKind(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


class ProviderConfig(BaseModel):
    kind: ProviderKind
    base_url: str | None = None
    api_key: SecretStr
    model: str
    timeout_s: int = Field(default=30, ge=1)
    max_tokens: int = Field(default=1024, ge=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    extra_headers: dict[str, str] = Field(default_factory=dict)


class AIConfig(BaseModel):
    provider: ProviderConfig
    max_iterations: int = Field(default=8, ge=1, le=50)
    system_prompt: str | None = None
    ssh_tool_enabled: bool = False
    ssh_command_allowlist: list[str] = Field(default_factory=list)


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ChatMessage(BaseModel):
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolResult(BaseModel):
    tool_call_id: str
    name: str
    ok: bool
    content: str
    error: str | None = None


class HealthCheckResult(BaseModel):
    ok: bool
    provider: ProviderKind
    model: str
    tool_calling: bool = False
    latency_ms: int = 0
    error: str | None = None


class AgentRunResult(BaseModel):
    final_text: str
    iterations: int
    transcript: list[ChatMessage]
    tool_invocations: list[ToolResult]
    stopped_reason: Literal["final_answer", "max_iterations", "error"]
