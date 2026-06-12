from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class CpuStats(BaseModel):
    percent: float = Field(ge=0, le=100)
    per_core: list[float]
    load_avg: tuple[float, float, float]
    core_count: int


class MemoryStats(BaseModel):
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float = Field(ge=0, le=100)


class DiskStats(BaseModel):
    mountpoint: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float = Field(ge=0, le=100)

    @field_validator("total_gb", "used_gb", "free_gb")
    @classmethod
    def non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("disk size must be >= 0")
        return v


class SystemSnapshot(BaseModel):
    hostname: str
    collected_at: datetime
    cpu: CpuStats
    memory: MemoryStats
    disks: list[DiskStats]


class LogMatch(BaseModel):
    line_number: int
    timestamp: datetime | None = None
    level: str | None = None
    pattern: str
    content: str


class LogReport(BaseModel):
    source_path: str
    total_lines: int
    scanned_lines: int
    level_counts: dict[str, int]
    matches: list[LogMatch]
    summary: str


class CommandResult(BaseModel):
    host: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    success: bool
    error: str | None = None

    @model_validator(mode="after")
    def check_success_consistency(self) -> CommandResult:
        expected = self.exit_code == 0 and self.error is None
        if self.success != expected:
            raise ValueError(
                f"success must be {expected} when exit_code={self.exit_code} "
                f"and error={self.error!r}"
            )
        return self

    @classmethod
    def make(
        cls,
        host: str,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: int,
        error: str | None = None,
    ) -> CommandResult:
        return cls(
            host=host,
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            success=(exit_code == 0 and error is None),
            error=error,
        )


class HostConfig(BaseModel):
    name: str
    hostname: str
    port: int = 22
    username: str
    password: str | None = None
    key_path: str | None = None

    @model_validator(mode="after")
    def check_auth(self) -> HostConfig:
        if not self.password and not self.key_path:
            raise ValueError(
                "HostConfig must provide either password or key_path"
            )
        return self

    @field_validator("key_path")
    @classmethod
    def expand_key_path(cls, v: str | None) -> str | None:
        if v is not None:
            return os.path.expanduser(v)
        return v


class AppConfig(BaseModel):
    hosts: list[HostConfig] = Field(default_factory=list)
    ssh_timeout_s: int = 15
    max_concurrency: int = Field(default=10, ge=1)


class LogParseOptions(BaseModel):
    patterns: list[str] = Field(default_factory=list)
    levels: list[str] | None = None
    since: datetime | None = None
    max_matches: int = Field(default=1000, ge=0)
