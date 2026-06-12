from __future__ import annotations

"""FakeProvider — test double implementing LLMProvider with scripted responses.

Used by AI-layer tests to exercise AgentRunner without network access.
"""

import json
from typing import Any

from ops_agent.ai.models import (
    ChatMessage,
    HealthCheckResult,
    ProviderConfig,
    ProviderKind,
    Role,
    ToolCall,
    ToolDefinition,
)
from ops_agent.ai.providers.base import LLMProvider
from ops_agent.ai.providers.registry import ProviderRegistry


class FakeProvider(LLMProvider):
    """Returns a scripted sequence of ChatMessages, one per chat() call.

    Each entry can be:
    - ChatMessage with content only (final answer)
    - ChatMessage with tool_calls (triggers tool execution)
    """

    def __init__(
        self,
        config: ProviderConfig | None = None,
        responses: list[ChatMessage] | None = None,
        _supports_tools: bool = True,
    ) -> None:
        if config is None:
            config = ProviderConfig(
                kind=ProviderKind.OPENAI,
                api_key="fake-key",
                model="fake-model",
            )
        super().__init__(config)
        self._responses = list(responses or [])
        self._call_index = 0
        self._supports_tools = _supports_tools
        self.call_log: list[tuple[list[ChatMessage], list[ToolDefinition]]] = []

    @property
    def supports_tool_calling(self) -> bool:
        return self._supports_tools

    def chat(
        self, messages: list[ChatMessage], tools: list[ToolDefinition]
    ) -> ChatMessage:
        self.call_log.append((list(messages), list(tools)))
        if self._call_index < len(self._responses):
            resp = self._responses[self._call_index]
            self._call_index += 1
            return resp
        # Default: return a final answer
        return ChatMessage(role=Role.ASSISTANT, content="[fake] no more scripted responses")

    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(
            ok=True,
            provider=self.config.kind,
            model=self.config.model,
            tool_calling=self._supports_tools,
            latency_ms=10,
        )


def make_tool_call_msg(tool_name: str, arguments: dict[str, Any], call_id: str = "call_1") -> ChatMessage:
    return ChatMessage(
        role=Role.ASSISTANT,
        content=None,
        tool_calls=[ToolCall(id=call_id, name=tool_name, arguments=arguments)],
    )


def make_final_msg(text: str = "Here is my answer.") -> ChatMessage:
    return ChatMessage(role=Role.ASSISTANT, content=text)


# Register fake provider for tests
def ensure_fake_provider() -> None:
    if "fake" not in ProviderRegistry.available():
        ProviderRegistry.register("fake", FakeProvider)
