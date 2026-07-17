"""
Every CLI command handler returns this shape instead of writing to
stdout/exiting directly, so integration tests can invoke handlers as plain
functions and assert on their output/exit code without spawning a
subprocess. Ported from src/cli/types.ts.

Exit code contract (required so an agent invoking this CLI programmatically
can rely on it): 0 = success, 1 = general/usage error, 2 = validation
error (bad event data).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: Optional[str] = None
