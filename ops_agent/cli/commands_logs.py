from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.table import Table

from ops_agent.core.models import LogParseOptions
from ops_agent.services.log_service import LogService
from ops_agent.web.schemas import LogAnalyzeRequest

console = Console()


def analyze_logs(
    path: str,
    pattern: list[str],
    level: list[str],
    since: str | None,
    max_matches: int,
    json_out: bool,
) -> None:
    since_dt: datetime | None = None
    if since:
        since_dt = datetime.fromisoformat(since)

    req = LogAnalyzeRequest(
        path=path,
        patterns=pattern,
        levels=level if level else None,
        since=since_dt,
        max_matches=max_matches,
    )
    report = LogService().analyze(req)

    if json_out:
        console.print_json(report.model_dump_json())
        return

    table = Table(title=f"Log Report — {report.source_path}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total lines", str(report.total_lines))
    table.add_row("Scanned lines", str(report.scanned_lines))
    table.add_row("Matches", str(len(report.matches)))
    table.add_row("Summary", report.summary)

    for lv, cnt in sorted(report.level_counts.items()):
        table.add_row(f"  {lv}", str(cnt))

    console.print(table)

    if report.matches:
        mtable = Table(title="Matches")
        mtable.add_column("Line", style="dim")
        mtable.add_column("Level")
        mtable.add_column("Pattern", style="yellow")
        mtable.add_column("Content", style="white", max_width=80)
        for m in report.matches:
            mtable.add_row(
                str(m.line_number),
                m.level or "-",
                m.pattern,
                m.content[:120],
            )
        console.print(mtable)
