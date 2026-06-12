from __future__ import annotations

import time

import anthropic

from ops_agent.ai.errors import ProviderError
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


class AnthropicProvider(LLMProvider):
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        kwargs: dict = {
            "api_key": config.api_key.get_secret_value(),
            "timeout": config.timeout_s,
        }
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self._client = anthropic.Anthropic(**kwargs)

    @property
    def supports_tool_calling(self) -> bool:
        return True

    def chat(
        self, messages: list[ChatMessage], tools: list[ToolDefinition]
    ) -> ChatMessage:
        system_text, wire_messages = self._to_wire(messages)
        wire_tools = self._tools_to_wire(tools) if tools else anthropic.NOT_GIVEN

        try:
            kwargs: dict = {
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "messages": wire_messages,
                "tools": wire_tools,
            }
            if system_text:
                kwargs["system"] = system_text
            response = self._client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise ProviderError(f"Authentication failed: {e}") from e
        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
            raise ProviderError(f"Connection error: {e}") from e
        except anthropic.APIError as e:
            raise ProviderError(f"API error: {e}") from e

        return self._from_wire(response)

    def health_check(self) -> HealthCheckResult:
        start = time.monotonic_ns()
        probe_tool = ToolDefinition(
            name="ping",
            description="Return pong. Used only to verify tool calling.",
            parameters={"type": "object", "properties": {}, "required": []},
        )
        probe_msg = ChatMessage(
            role=Role.USER,
            content="Reply with the word OK. If you can call tools, call ping.",
        )
        try:
            reply = self.chat([probe_msg], [probe_tool])
            elapsed = (time.monotonic_ns() - start) // 1_000_000
            tool_ok = bool(reply.tool_calls and reply.tool_calls[0].name == "ping")
            return HealthCheckResult(
                ok=True,
                provider=self.config.kind,
                model=self.config.model,
                tool_calling=tool_ok,
                latency_ms=elapsed,
            )
        except ProviderError as e:
            elapsed = (time.monotonic_ns() - start) // 1_000_000
            return HealthCheckResult(
                ok=False,
                provider=self.config.kind,
                model=self.config.model,
                latency_ms=elapsed,
                error=str(e),
            )

    @staticmethod
    def _to_wire(
        messages: list[ChatMessage],
    ) -> tuple[str | None, list[dict]]:
        system_text: str | None = None
        wire: list[dict] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_text = msg.content
            elif msg.role == Role.USER:
                wire.append({"role": "user", "content": msg.content or ""})
            elif msg.role == Role.ASSISTANT:
                content_blocks: list[dict] = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                if not content_blocks:
                    content_blocks.append({"type": "text", "text": ""})
                wire.append({"role": "assistant", "content": content_blocks})
            elif msg.role == Role.TOOL:
                wire.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content or "",
                        }
                    ],
                })

        return system_text, wire

    @staticmethod
    def _tools_to_wire(tools: list[ToolDefinition]) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    @staticmethod
    def _from_wire(response) -> ChatMessage:
        text_parts: list[str] = []
        calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)
                )

        return ChatMessage(
            role=Role.ASSISTANT,
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=calls,
        )


# Register at import time
ProviderRegistry.register("anthropic", AnthropicProvider)
