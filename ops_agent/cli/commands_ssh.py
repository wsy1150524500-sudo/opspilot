from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ops_agent.core.config import load_config
from ops_agent.core.models import HostConfig
from ops_agent.services.ssh_service import SSHService
from ops_agent.web.schemas import BatchRunRequest

console = Console()


def ssh_run(
    command: str,
    host_names: list[str],
    config_path: str | None,
    json_out: bool,
) -> None:
    config = load_config(config_path)

    req = BatchRunRequest(
        command=command,
        host_names=host_names,
    )
    results = SSHService().run_batch(req, config)

    if json_out:
        import json as json_mod

        payload = [r.model_dump() for r in results]
        console.print_json(json_mod.dumps(payload))
        return

    table = Table(title=f"SSH Batch Results — `{command}`")
    table.add_column("Host", style="cyan")
    table.add_column("Exit Code")
    table.add_column("Success")
    table.add_column("Duration (ms)")
    table.add_column("Stdout", max_width=60)
    table.add_column("Error", style="red")

    for r in results:
        table.add_row(
            r.host,
            str(r.exit_code),
            "Yes" if r.success else "No",
            str(r.duration_ms),
            (r.stdout or "")[:120],
            r.error or "",
        )

    console.print(table)
