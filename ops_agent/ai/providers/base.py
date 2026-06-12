from __future__ import annotations

from abc import ABC, abstractmethod

from ops_agent.ai.models import (
    ChatMessage,
    HealthCheckResult,
    ProviderConfig,
    ToolDefinition,
)


class LLMProvider(ABC):
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def chat(
        self, messages: list[ChatMessage], tools: list[ToolDefinition]
    ) -> ChatMessage:
        """Send a single chat turn and return the assistant's normalized reply."""

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """Perform a minimal probe verifying url + key and tool-calling if possible."""

    @property
    @abstractmethod
    def supports_tool_calling(self) -> bool: ...
