from __future__ import annotations

import json
import time

import openai

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


class OpenAIProvider(LLMProvider):
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client = openai.OpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url,
            timeout=config.timeout_s,
        )

    @property
    def supports_tool_calling(self) -> bool:
        return True

    def chat(
        self, messages: list[ChatMessage], tools: list[ToolDefinition]
    ) -> ChatMessage:
        wire_messages = self._to_wire(messages)
        wire_tools = self._tools_to_wire(tools) if tools else openai.NOT_GIVEN

        try:
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=wire_messages,
                tools=wire_tools,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
        except openai.AuthenticationError as e:
            raise ProviderError(f"Authentication failed: {e}") from e
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            raise ProviderError(f"Connection error: {e}") from e
        except openai.APIError as e:
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
    def _to_wire(messages: list[ChatMessage]) -> list[dict]:
        wire: list[dict] = []
        for msg in messages:
            if msg.role == Role.TOOL:
                wire.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content or "",
                })
            elif msg.role == Role.ASSISTANT and msg.tool_calls:
                wire.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
            else:
                wire.append({
                    "role": msg.role.value,
                    "content": msg.content or "",
                })
        return wire

    @staticmethod
    def _tools_to_wire(tools: list[ToolDefinition]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    @staticmethod
    def _from_wire(response) -> ChatMessage:
        choice = response.choices[0]
        raw_calls = getattr(choice.message, "tool_calls", None) or []
        calls: list[ToolCall] = []
        for rc in raw_calls:
            try:
                args = json.loads(rc.function.arguments) if rc.function.arguments else {}
            except (json.JSONDecodeError, ValueError):
                args = {}
            calls.append(
                ToolCall(id=rc.id, name=rc.function.name, arguments=args)
            )
        return ChatMessage(
            role=Role.ASSISTANT,
            content=choice.message.content,
            tool_calls=calls,
        )


# Register at import time
ProviderRegistry.register("openai", OpenAIProvider)
