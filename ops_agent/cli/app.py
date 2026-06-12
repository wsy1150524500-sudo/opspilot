from __future__ import annotations

import json as json_mod

import typer
from rich.console import Console

from ops_agent.cli.commands_system import inspect_system
from ops_agent.cli.commands_logs import analyze_logs
from ops_agent.cli.commands_ssh import ssh_run
from ops_agent.cli.commands_ai import ai_setup, ai_chat

app = typer.Typer(help="CLI Ops Agent — system inspection, log analysis, SSH batch management")
console = Console()

# Sub-groups
inspect_app = typer.Typer(help="Inspect local system resources")
analyze_app = typer.Typer(help="Analyze log files")
ssh_app = typer.Typer(help="SSH batch operations")

app.add_typer(inspect_app, name="inspect")
app.add_typer(analyze_app, name="analyze")
app.add_typer(ssh_app, name="ssh")

# AI sub-app
ai_app = typer.Typer(help="Natural-language AI operations agent")
app.add_typer(ai_app, name="ai")


@inspect_app.command("system")
def _inspect_system(
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Collect and display local CPU / memory / disk metrics."""
    inspect_system(json_out)


@analyze_app.command("logs")
def _analyze_logs(
    path: str = typer.Argument(..., help="Path to the log file"),
    pattern: list[str] = typer.Option([], "--pattern", "-p", help="Regex patterns to match"),
    level: list[str] = typer.Option([], "--level", "-l", help="Filter by log level"),
    since: str | None = typer.Option(None, "--since", "-s", help="ISO timestamp lower bound"),
    max_matches: int = typer.Option(1000, "--max-matches", help="Maximum matches to collect"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Stream and analyze a log file."""
    analyze_logs(path, pattern, level, since, max_matches, json_out)


@ssh_app.command("run")
def _ssh_run(
    command: str = typer.Argument(..., help="Command to execute on remote hosts"),
    host: list[str] = typer.Option([], "--host", "-h", help="Ad-hoc host names from config"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to hosts YAML config"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run a command across multiple hosts via SSH."""
    ssh_run(command, host, config, json_out)


@ai_app.command("setup")
def _ai_setup(
    config: str | None = typer.Option(None, "--config", "-c", help="AI config YAML path"),
) -> None:
    """Interactively configure the LLM provider and run a connectivity check."""
    ai_setup(config)


@ai_app.command("chat")
def _ai_chat(
    message: str = typer.Argument(..., help="Natural-language request"),
    config: str | None = typer.Option(None, "--config", "-c", help="AI config YAML"),
    hosts_config: str | None = typer.Option(None, "--hosts-config", help="Hosts YAML"),
    show_transcript: bool = typer.Option(False, "--show-transcript"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Send a natural-language request to the AI agent."""
    ai_chat(message, config, hosts_config, show_transcript, json_out)


@ai_app.command("ask")
def _ai_ask(
    message: str = typer.Argument(..., help="Natural-language request"),
    config: str | None = typer.Option(None, "--config", "-c", help="AI config YAML"),
    hosts_config: str | None = typer.Option(None, "--hosts-config", help="Hosts YAML"),
    show_transcript: bool = typer.Option(False, "--show-transcript"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Alias for 'ai chat'."""
    ai_chat(message, config, hosts_config, show_transcript, json_out)


def run() -> None:
    app()
