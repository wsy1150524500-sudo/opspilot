from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from ops_agent.core.log_analyzer import LogAnalyzer
from ops_agent.core.models import LogParseOptions


# ── Helper ──────────────────────────────────────────────────────────

def _write_log(tmp_path: Path, lines: list[str]) -> str:
    p = tmp_path / "test.log"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


# ── Property 6: Log match cap ───────────────────────────────────────

@given(max_m=st.integers(min_value=0, max_value=50))
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_property6_match_cap(tmp_path, max_m):
    log_lines = [f"2024-01-15 10:00:{i:02d} ERROR line {i}" for i in range(60)]
    path = _write_log(tmp_path, log_lines)
    options = LogParseOptions(patterns=["ERROR"], max_matches=max_m)
    report = LogAnalyzer().analyze(path, options)

    assert len(report.matches) <= max_m
    assert report.scanned_lines <= report.total_lines


# ── Property 7: Level count integrity ───────────────────────────────

@given(
    n_info=st.integers(min_value=0, max_value=20),
    n_error=st.integers(min_value=0, max_value=20),
    n_debug=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_property7_level_count_integrity(tmp_path, n_info, n_error, n_debug):
    lines = []
    for i in range(n_info):
        lines.append(f"2024-01-15 10:00:{i:02d} INFO info {i}")
    for i in range(n_error):
        lines.append(f"2024-01-15 10:01:{i:02d} ERROR error {i}")
    for i in range(n_debug):
        lines.append(f"2024-01-15 10:02:{i:02d} DEBUG debug {i}")

    if not lines:
        assume(False)

    path = _write_log(tmp_path, lines)
    options = LogParseOptions(patterns=[])
    report = LogAnalyzer().analyze(path, options)

    total_levelled = sum(report.level_counts.values())
    # Every line has a level, so total_levelled should equal scanned_lines
    assert total_levelled == report.scanned_lines


# ── Unit tests ──────────────────────────────────────────────────────

def test_basic_analysis(sample_log_path):
    options = LogParseOptions(patterns=["ERROR"])
    report = LogAnalyzer().analyze(sample_log_path, options)

    assert report.total_lines == 7
    assert report.scanned_lines == 7  # no filters
    assert len(report.matches) == 2   # two ERROR lines
    assert report.matches[0].pattern == "ERROR"
    assert "ERROR" in report.level_counts
    assert report.level_counts["ERROR"] == 2


def test_level_filter(sample_log_path):
    options = LogParseOptions(patterns=[], levels=["ERROR"])
    report = LogAnalyzer().analyze(sample_log_path, options)

    assert report.scanned_lines == 2
    assert report.level_counts.get("INFO") is None
    assert report.level_counts["ERROR"] == 2


def test_since_filter(sample_log_path):
    since = datetime(2024, 1, 15, 10, 0, 3, tzinfo=timezone.utc)
    options = LogParseOptions(patterns=["ERROR"], since=since)
    report = LogAnalyzer().analyze(sample_log_path, options)

    # Only "2024-01-15 10:00:04 ERROR" and later should pass
    assert len(report.matches) == 1


def test_max_matches_truncation(sample_log_path):
    options = LogParseOptions(patterns=["ERROR"], max_matches=1)
    report = LogAnalyzer().analyze(sample_log_path, options)

    assert len(report.matches) == 1


def test_no_patterns_returns_no_matches(sample_log_path):
    options = LogParseOptions(patterns=[])
    report = LogAnalyzer().analyze(sample_log_path, options)

    assert len(report.matches) == 0
    assert report.scanned_lines > 0


def test_level_normalization(sample_log_path):
    options = LogParseOptions(patterns=[], levels=["WARNING"])
    report = LogAnalyzer().analyze(sample_log_path, options)

    assert report.level_counts.get("WARNING", 0) == 1
