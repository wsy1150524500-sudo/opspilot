from __future__ import annotations

import json as json_mod

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ops_agent.ai.agent import AgentRunner
from ops_agent.ai.config import load_ai_config
from ops_agent.ai.models import AgentRunResult
from ops_agent.ai.tools import build_default_registry
from ops_agent.core.config import load_config

console = Console()


def ai_setup(config_path: str | None) -> None:
    from ops_agent.ai.setup_wizard import SetupWizard

    wizard = SetupWizard(config_path=config_path)
    wizard.run()


def ai_chat(
    message: str,
    config_path: str | None,
    hosts_config: str | None,
    show_transcript: bool,
    json_out: bool,
) -> None:
    ai_config = load_ai_config(config_path)
    app_config = load_config(hosts_config)

    # Lazy-import providers
    import ops_agent.ai.providers.openai_provider  # noqa: F401
    import ops_agent.ai.providers.anthropic_provider  # noqa: F401
    import ops_agent.ai.providers.openai_compatible  # noqa: F401

    from ops_agent.ai.providers.registry import ProviderRegistry

    provider = ProviderRegistry.create(ai_config.provider)
    registry = build_default_registry(ai_config, app_config)
    runner = AgentRunner(
        provider=provider,
        registry=registry,
        max_iterations=ai_config.max_iterations,
        system_prompt=ai_config.system_prompt,
    )

    with console.status("[bold green]Thinking..."):
        result = runner.run(message)

    render_run_result(result, show_transcript, json_out)


def render_run_result(
    result: AgentRunResult,
    show_transcript: bool,
    json_out: bool,
) -> None:
    if json_out:
        console.print_json(result.model_dump_json())
        return

    # Final answer
    console.print()
    console.print(Panel(Markdown(result.final_text), title="Answer", style="green"))
    console.print(
        f"  [dim]({result.iterations} iterations, "
        f"stopped: {result.stopped_reason}, "
        f"{len(result.tool_invocations)} tool call(s))[/dim]"
    )

    if show_transcript and result.transcript:
        console.print("\n[bold]Transcript:[/bold]")
        for msg in result.transcript:
            role = msg.role.value.upper()
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    console.print(f"  [cyan]{role}[/cyan] → tool_call: {tc.name}({tc.arguments})")
            elif msg.role.value == "tool":
                console.print(
                    f"  [yellow]{role}[/yellow] [{msg.name}] → {(msg.content or '')[:200]}"
                )
            elif msg.content:
                console.print(f"  [cyan]{role}[/cyan] → {msg.content[:300]}")
