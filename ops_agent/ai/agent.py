from __future__ import annotations

from ops_agent.ai.errors import ProviderError
from ops_agent.ai.models import (
    AgentRunResult,
    ChatMessage,
    Role,
    ToolResult,
)
from ops_agent.ai.providers.base import LLMProvider
from ops_agent.ai.tool_registry import ToolRegistry


class AgentRunner:
    def __init__(
        self,
        provider: LLMProvider,
        registry: ToolRegistry,
        max_iterations: int = 8,
        system_prompt: str | None = None,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._max_iterations = max_iterations
        self._system_prompt = system_prompt

    def run(
        self,
        user_message: str,
        history: list[ChatMessage] | None = None,
    ) -> AgentRunResult:
        if not user_message:
            raise ValueError("user_message must be non-empty")
        if self._max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")

        if not self._provider.supports_tool_calling:
            return AgentRunResult(
                final_text="Selected model does not support tool calling.",
                iterations=0,
                transcript=[],
                tool_invocations=[],
                stopped_reason="error",
            )

        messages = self._initial_messages(user_message, history)
        tools = self._registry.schemas()
        invocations: list[ToolResult] = []

        for iteration in range(1, self._max_iterations + 1):
            try:
                reply = self._provider.chat(messages, tools)
            except ProviderError as e:
                return AgentRunResult(
                    final_text=f"Provider error: {e}",
                    iterations=iteration,
                    transcript=list(messages),
                    tool_invocations=invocations,
                    stopped_reason="error",
                )

            messages.append(reply)

            if not reply.tool_calls:
                return AgentRunResult(
                    final_text=reply.content or "",
                    iterations=iteration,
                    transcript=list(messages),
                    tool_invocations=invocations,
                    stopped_reason="final_answer",
                )

            tool_messages = self._execute_tool_calls(reply.tool_calls)
            for tm, tr in tool_messages:
                messages.append(tm)
                invocations.append(tr)

        return AgentRunResult(
            final_text="Reached max iterations without a final answer.",
            iterations=self._max_iterations,
            transcript=list(messages),
            tool_invocations=invocations,
            stopped_reason="max_iterations",
        )

    def _initial_messages(
        self,
        user_message: str,
        history: list[ChatMessage] | None,
    ) -> list[ChatMessage]:
        msgs: list[ChatMessage] = []
        if self._system_prompt:
            msgs.append(ChatMessage(role=Role.SYSTEM, content=self._system_prompt))
        if history:
            msgs.extend(history)
        msgs.append(ChatMessage(role=Role.USER, content=user_message))
        return msgs

    def _execute_tool_calls(
        self, calls
    ) -> list[tuple[ChatMessage, ToolResult]]:
        results: list[tuple[ChatMessage, ToolResult]] = []
        for call in calls:
            tr = self._registry.dispatch(call)
            content = tr.content if tr.ok else f"ERROR: {tr.error}"
            msg = ChatMessage(
                role=Role.TOOL,
                tool_call_id=tr.tool_call_id,
                name=tr.name,
                content=content,
            )
            results.append((msg, tr))
        return results
