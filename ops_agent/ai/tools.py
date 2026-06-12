from __future__ import annotations

from ops_agent.ai.models import AIConfig
from ops_agent.ai.tool_registry import Tool, ToolRegistry
from ops_agent.core.models import AppConfig
from ops_agent.services.log_service import LogService
from ops_agent.services.ssh_service import SSHService
from ops_agent.services.system_service import SystemService
from ops_agent.web.schemas import BatchRunRequest, LogAnalyzeRequest


def build_default_registry(
    ai_config: AIConfig, app_config: AppConfig
) -> ToolRegistry:
    registry = ToolRegistry()

    # 1. inspect_system
    def _inspect_system(args: dict) -> object:
        return SystemService().snapshot()

    registry.register(
        Tool(
            name="inspect_system",
            description="Collect local CPU, memory, and disk metrics. Returns a SystemSnapshot.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
            handler=_inspect_system,
        )
    )

    # 2. analyze_logs
    def _analyze_logs(args: dict) -> object:
        req = LogAnalyzeRequest(
            path=args["path"],
            patterns=args.get("patterns", []),
            levels=args.get("levels"),
            since=args.get("since"),
            max_matches=args.get("max_matches", 1000),
        )
        return LogService().analyze(req)

    registry.register(
        Tool(
            name="analyze_logs",
            description="Scan a log file for patterns/levels and return counts, matches, and a summary.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the log file"},
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Regex patterns to match",
                    },
                    "levels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by log level (e.g. ERROR, WARN)",
                    },
                    "since": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Only include lines at or after this ISO timestamp",
                    },
                    "max_matches": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 1000,
                        "description": "Maximum number of matches to return",
                    },
                },
                "required": ["path"],
            },
            handler=_analyze_logs,
        )
    )

    # 3. ssh_run (only if enabled)
    if ai_config.ssh_tool_enabled:
        allowlist = set(ai_config.ssh_command_allowlist)

        def _ssh_run(args: dict) -> object:
            command = args["command"]
            if allowlist and command not in allowlist:
                raise ValueError("command not allowed")
            host_names = args.get("host_names", [])
            req = BatchRunRequest(
                command=command,
                host_names=host_names,
            )
            return SSHService().run_batch(req, app_config)

        registry.register(
            Tool(
                name="ssh_run",
                description="Run a command on remote hosts via SSH. Returns per-host results.",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute",
                        },
                        "host_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Host names from the inventory config",
                        },
                    },
                    "required": ["command"],
                },
                handler=_ssh_run,
            )
        )

    return registry
