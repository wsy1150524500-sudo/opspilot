from __future__ import annotations

import re
from datetime import datetime, timezone

from ops_agent.core.models import LogMatch, LogParseOptions, LogReport

# Common log format: 2024-01-15 10:30:45 or ISO-8601 variants
_TIMESTAMP_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)
_LEVEL_RE = re.compile(
    r"\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b", re.IGNORECASE
)


class _ParsedLine:
    __slots__ = ("timestamp", "level", "content", "line_no")

    def __init__(
        self,
        line_no: int,
        timestamp: datetime | None,
        level: str | None,
        content: str,
    ) -> None:
        self.line_no = line_no
        self.timestamp = timestamp
        self.level = level
        self.content = content


class LogAnalyzer:
    def analyze(self, path: str, options: LogParseOptions) -> LogReport:
        total = 0
        scanned = 0
        level_counts: dict[str, int] = {}
        matches: list[LogMatch] = []

        level_filter = (
            {lv.upper() for lv in options.levels} if options.levels else None
        )
        compiled_patterns = [re.compile(p) for p in options.patterns]

        with open(path, encoding="utf-8", errors="replace") as fh:
            for line_no, raw_line in enumerate(fh, start=1):
                line = raw_line.rstrip("\n\r")
                total += 1
                parsed = self._parse_line(line, line_no)

                if (
                    options.since is not None
                    and parsed.timestamp is not None
                    and parsed.timestamp < options.since
                ):
                    continue

                if level_filter is not None and (
                    parsed.level is None or parsed.level not in level_filter
                ):
                    continue

                scanned += 1
                if parsed.level is not None:
                    level_counts[parsed.level] = (
                        level_counts.get(parsed.level, 0) + 1
                    )

                if len(matches) < options.max_matches:
                    for pat_re, pat_str in zip(compiled_patterns, options.patterns):
                        if pat_re.search(line):
                            matches.append(
                                LogMatch(
                                    line_number=line_no,
                                    timestamp=parsed.timestamp,
                                    level=parsed.level,
                                    pattern=pat_str,
                                    content=line,
                                )
                            )
                            if len(matches) >= options.max_matches:
                                break

        return LogReport(
            source_path=path,
            total_lines=total,
            scanned_lines=scanned,
            level_counts=level_counts,
            matches=matches,
            summary=self._build_summary(level_counts, matches),
        )

    def _parse_line(self, line: str, line_no: int) -> _ParsedLine:
        timestamp = None
        ts_match = _TIMESTAMP_RE.search(line)
        if ts_match:
            try:
                ts_str = ts_match.group(1).replace("Z", "+00:00")
                timestamp = datetime.fromisoformat(ts_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except (ValueError, IndexError):
                pass

        level = None
        lv_match = _LEVEL_RE.search(line)
        if lv_match:
            level = lv_match.group(1).upper()
            if level == "WARN":
                level = "WARNING"

        return _ParsedLine(
            line_no=line_no, timestamp=timestamp, level=level, content=line
        )

    def _matches(self, parsed: _ParsedLine, options: LogParseOptions) -> list[str]:
        matched: list[str] = []
        for pat in options.patterns:
            if re.search(pat, parsed.content):
                matched.append(pat)
        return matched

    @staticmethod
    def _build_summary(
        level_counts: dict[str, int], matches: list[LogMatch]
    ) -> str:
        parts: list[str] = []
        if level_counts:
            parts.append(
                "Levels: "
                + ", ".join(f"{k}={v}" for k, v in sorted(level_counts.items()))
            )
        parts.append(f"{len(matches)} match(es) found")
        return "; ".join(parts)
