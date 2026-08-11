"""MCP server exposing the masterytrace CLI as a single generic tool.

Built on the official ``mcp`` Python SDK's ``MCPServer`` interface (SDK
>=2.0.0). Rather than re-implementing every masterytrace subcommand as its
own MCP tool, this wraps the installed ``masterytrace`` console script in
one generic ``run`` tool that shells out to it -- so any subcommand or flag
the CLI supports (including ones added to it after this module was
written) is already reachable over MCP with no server-side changes.

Every tool handler here is wrapped so it can never raise: subprocess
launch failures, timeouts, non-zero exit codes, and non-JSON stdout are
all converted into a result dict (an ``{"error": ...}`` shape, or a
best-effort raw-output shape) instead of propagating as an exception.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from mcp.server import MCPServer

_CLI_BIN = "masterytrace"
_TIMEOUT_SECONDS = 60

_FALLBACK_DESCRIPTION = (
    "Run the masterytrace CLI (Bayesian Knowledge Tracing / 2PL Item "
    "Response Theory mastery measurement) with the given argument list "
    "and return its output.\n\n"
    "Subcommands: init [--force], record <path>, "
    "score [--model bkt|irt|both], report [--format table|json|markdown]. "
    "Global flags: --json, --version, --help."
)


def _resolve_cli_help() -> str:
    """Best-effort fetch of the real `masterytrace --help` text, used to
    populate the `run` tool's description at import time. Falls back to a
    static summary if the CLI binary isn't on PATH or the call fails for
    any reason -- this must never raise on import."""
    cli_path = shutil.which(_CLI_BIN)
    if cli_path is None:
        return _FALLBACK_DESCRIPTION
    try:
        completed = subprocess.run(
            [cli_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return _FALLBACK_DESCRIPTION
    help_text = completed.stdout.strip()
    if completed.returncode != 0 or not help_text:
        return _FALLBACK_DESCRIPTION
    return help_text


_TOOL_DESCRIPTION = (
    'Run the masterytrace CLI with the given argv list (e.g. '
    '["score", "--model", "bkt"]) and return its result. Equivalent to '
    "running `masterytrace <args...>` in a shell; stdout is parsed as "
    "JSON when possible.\n\n" + _resolve_cli_help()
)

mcp = MCPServer("masterytrace")


@mcp.tool(description=_TOOL_DESCRIPTION)
def run(args: list[str]) -> dict[str, Any]:
    """Shell out to the installed `masterytrace` CLI with `args` and
    return its result as a dict. Never raises: launch failures, timeouts,
    non-zero exit codes, and non-JSON stdout are all captured in the
    return value rather than propagated as an exception.

    Example: run(["score", "--model", "bkt", "--json"]) fits a BKT model
    against the stored event log and returns the parsed JSON report.
    """
    cli_path = shutil.which(_CLI_BIN)
    if cli_path is None:
        return {"error": f"'{_CLI_BIN}' not found on PATH"}

    try:
        completed = subprocess.run(
            [cli_path, *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
    except OSError as exc:
        return {"error": f"failed to launch {_CLI_BIN}: {exc}"}
    except subprocess.TimeoutExpired:
        return {"error": f"{_CLI_BIN} timed out after {_TIMEOUT_SECONDS}s"}

    if completed.returncode != 0:
        return {
            "error": f"{_CLI_BIN} exited with code {completed.returncode}",
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    stdout = completed.stdout.strip()
    if not stdout:
        return {"stdout": completed.stdout, "stderr": completed.stderr}

    try:
        return {"result": json.loads(stdout)}
    except json.JSONDecodeError:
        return {"stdout": completed.stdout, "stderr": completed.stderr}


def main() -> None:
    """Entry point for the `masterytrace-mcp` console script."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
