from __future__ import annotations

from ops_agent.core.log_analyzer import LogAnalyzer
from ops_agent.core.models import LogParseOptions, LogReport
from ops_agent.web.schemas import LogAnalyzeRequest


class LogService:
    def analyze(self, req: LogAnalyzeRequest) -> LogReport:
        options = LogParseOptions(
            patterns=req.patterns,
            levels=req.levels,
            since=req.since,
            max_matches=req.max_matches,
        )
        return LogAnalyzer().analyze(req.path, options)
