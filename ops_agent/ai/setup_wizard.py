from __future__ import annotations

import typer
from pydantic import SecretStr
from rich.console import Console
from rich.panel import Panel

from ops_agent.ai.config import save_ai_config
from ops_agent.ai.models import AIConfig, ProviderConfig, ProviderKind
from ops_agent.ai.providers.registry import ProviderRegistry

console = Console()

# Lazy-import providers so they register themselves
def _ensure_providers() -> None:
    import ops_agent.ai.providers.openai_provider  # noqa: F401
    import ops_agent.ai.providers.anthropic_provider  # noqa: F401
    import ops_agent.ai.providers.openai_compatible  # noqa: F401


class SetupWizard:
    def __init__(self, config_path: str | None = None) -> None:
        self._config_path = config_path or "config/ai.yaml"

    def run(self) -> AIConfig:
        _ensure_providers()

        console.print(Panel("[bold]AI Agent Setup Wizard[/bold]", style="blue"))

        kind = self._prompt_provider()
        base_url = self._prompt_base_url(kind)
        model = self._prompt_model(kind)
        api_key = self._prompt_api_key()

        provider_cfg = ProviderConfig(
            kind=kind,
            base_url=base_url,
            api_key=SecretStr(api_key),
            model=model,
        )

        console.print("\n[bold]Running connectivity check...[/bold]")
        provider = ProviderRegistry.create(provider_cfg)
        result = self.probe(provider)

        if result.ok:
            console.print(f"  [green]✓[/green] Endpoint reachable (latency {result.latency_ms} ms)")
            console.print("  [green]✓[/green] Authentication OK")
            if result.tool_calling:
                console.print("  [green]✓[/green] Tool calling supported")
            else:
                console.print("  [yellow]⚠[/yellow] Tool calling not confirmed (model may still work)")
        else:
            console.print(f"  [red]✗[/red] Failed: {result.error}")
            console.print("[red]Config NOT saved.[/red]")
            raise typer.Exit(code=1)

        save = typer.confirm("\nSave configuration?", default=True)
        if not save:
            console.print("Config not saved.")
            raise typer.Exit()

        ai_config = AIConfig(provider=provider_cfg)
        save_ai_config(ai_config, self._config_path, store_key_as_env=True)
        console.print(f"[green]Saved to {self._config_path}[/green]")

        env_name = _guess_env_name(kind)
        console.print(
            f"  Set [bold]{env_name}[/bold] in your environment before running."
        )
        return ai_config

    def probe(self, provider) -> object:
        return provider.health_check()

    def _prompt_provider(self) -> ProviderKind:
        available = ProviderRegistry.available()
        console.print("\nAvailable providers:")
        for i, name in enumerate(available, 1):
            console.print(f"  {i}. {name}")

        choice = typer.prompt("Select provider (number or name)", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                return ProviderKind(available[idx])
        except ValueError:
            pass
        return ProviderKind(choice)

    def _prompt_base_url(self, kind: ProviderKind) -> str | None:
        if kind == ProviderKind.OPENAI_COMPATIBLE:
            url = typer.prompt("Base URL (e.g. https://api.deepseek.com/v1)")
            if not url:
                console.print("[red]base_url is required for openai_compatible[/red]")
                raise typer.Exit(code=1)
            return url
        elif kind == ProviderKind.ANTHROPIC:
            use_custom = typer.confirm("Use custom base URL?", default=False)
            if use_custom:
                return typer.prompt("Base URL")
        else:
            use_custom = typer.confirm("Use custom base URL?", default=False)
            if use_custom:
                return typer.prompt("Base URL")
        return None

    def _prompt_model(self, kind: ProviderKind) -> str:
        defaults = {
            ProviderKind.OPENAI: "gpt-4o",
            ProviderKind.ANTHROPIC: "claude-sonnet-4-20250514",
            ProviderKind.OPENAI_COMPATIBLE: "deepseek-chat",
        }
        return typer.prompt("Model name", default=defaults.get(kind, ""))

    def _prompt_api_key(self) -> str:
        return typer.prompt("API key", hide_input=True, confirmation_prompt=False)


def _guess_env_name(kind: ProviderKind) -> str:
    mapping = {
        ProviderKind.OPENAI: "OPENAI_API_KEY",
        ProviderKind.ANTHROPIC: "ANTHROPIC_API_KEY",
        ProviderKind.OPENAI_COMPATIBLE: "COMPAT_API_KEY",
    }
    return mapping.get(kind, "API_KEY")
