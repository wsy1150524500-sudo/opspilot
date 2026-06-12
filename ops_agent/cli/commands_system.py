from __future__ import annotations

import json as json_mod

from rich.console import Console
from rich.table import Table

from ops_agent.services.system_service import SystemService

console = Console()


def inspect_system(json_out: bool) -> None:
    snapshot = SystemService().snapshot()

    if json_out:
        console.print_json(snapshot.model_dump_json())
        return

    table = Table(title=f"System Snapshot — {snapshot.hostname}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Collected at", str(snapshot.collected_at))
    table.add_row("CPU %", f"{snapshot.cpu.percent:.1f}%")
    table.add_row("CPU cores", str(snapshot.cpu.core_count))
    table.add_row("Load avg", str(snapshot.cpu.load_avg))
    table.add_row(
        "Memory",
        f"{snapshot.memory.used_mb:.0f}/{snapshot.memory.total_mb:.0f} MB "
        f"({snapshot.memory.percent:.1f}%)",
    )

    for d in snapshot.disks:
        table.add_row(
            f"Disk {d.mountpoint}",
            f"{d.used_gb:.1f}/{d.total_gb:.1f} GB ({d.percent:.1f}%)",
        )

    console.print(table)
