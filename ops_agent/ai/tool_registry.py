from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ops_agent.ai.models import ToolCall, ToolDefinition, ToolResult


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def schemas(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name=t.name,
                description=t.description,
                parameters=t.parameters,
            )
            for t in self._tools.values()
        ]

    def dispatch(self, call: ToolCall) -> ToolResult:
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                ok=False,
                content="",
                error=f"unknown tool: {call.name}",
            )

        try:
            output = tool.handler(call.arguments)
            if hasattr(output, "model_dump_json"):
                payload = output.model_dump_json()
            elif isinstance(output, (dict, list)):
                payload = json.dumps(output, default=str)
            else:
                payload = json.dumps(output, default=str)
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                ok=True,
                content=payload,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                ok=False,
                content="",
                error=str(e),
            )
