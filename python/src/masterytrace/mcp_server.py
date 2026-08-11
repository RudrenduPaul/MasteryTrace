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
    "Invoke the installed `masterytrace` CLI (Bayesian Knowledge Tracing "
    "and 2-parameter-logistic Item Response Theory mastery scoring for "
    "learner response-event logs) with a raw argv list, and return its "
    "parsed result, so an agent can scaffold, record, score, and report "
    "on mastery data without a separate shell step.\n\n"
    "Call this to turn a log of learner response events (learnerId, "
    "skillId, correct, timestamp) into per-learner, per-skill mastery "
    "estimates, or to inspect scores already computed in the current "
    "working directory. Typical order: `init` in a fresh directory to "
    "scaffold a sample events.json and config, `record` to load a real "
    "JSON or CSV event log, `score` to fit BKT and/or IRT against the "
    "stored log, `report` to read the fitted scores back out. Do not "
    "call `record` if you need to preserve a prior event log: it always "
    "replaces `.masterytrace/events.json` wholesale, there is no append "
    "mode, so merge old and new events yourself before calling it. No "
    "API keys or network access are required.\n\n"
    "Every call runs a real local subprocess against the `masterytrace` "
    "binary on PATH with a 60-second timeout, so results are "
    "synchronous. `init`, `record`, and `score` write JSON files under "
    "a `.masterytrace/` directory relative to the process's current "
    "working directory; `report`, `--version`, and `--help` are "
    "read-only. There is no network access at any point. `init` is "
    "idempotent by default (skips files that already exist) unless "
    "`--force` is passed, which overwrites them; `record` and `score` "
    "are not idempotent in that sense, each run fully replaces the "
    "previous stored file. On failure (binary not found, non-zero "
    "exit, or a timeout) this tool never raises: it returns an "
    '`{"error": ...}` dict, usually with the raw `stdout`/`stderr` '
    "attached for diagnosis. The underlying CLI's own exit codes are 0 "
    "success, 1 general/usage error (bad flag, missing file), 2 "
    "event-log validation error.\n\n"
    "`args` is a list[str] of raw argv tokens appended after the "
    "`masterytrace` binary, exactly as you would type them on a "
    "command line split into tokens (no shell quoting). Real examples: "
    '["init", "--force"] scaffolds or overwrites a sample event log '
    'and config in the cwd; ["record", "events.json"] validates and '
    'loads a JSON or CSV event log; ["score", "--model", "bkt", '
    '"--json"] fits only the BKT model against the stored log and '
    'forces machine-readable JSON; ["report", "--format", "json"] '
    "reads the fitted scores back as structured JSON instead of the "
    'default table. Pass ["--help"] or ["<subcommand>", "--help"] as '
    "args to fetch the CLI's own live help text for anything not "
    "covered here.\n\n"
    "The return value is always a dict. On success with parseable JSON "
    'stdout it is {"result": <parsed JSON>}; for `score --json` that '
    'JSON is {"model", "eventCount", "storedAt"}, and for `report '
    "--format json` it is {\"generated_at\", \"reports\": [{\"model\": "
    '"bkt"|"irt", "learners": [{"learner_id", "skills": [{"skill_id", '
    '"metric", "value", "response_count", "details"}]}], "meta"}]}. '
    "When stdout is not valid JSON (e.g. the default human-readable "
    'table from `report`, or `init`\'s status lines) the dict is '
    '{"stdout": ..., "stderr": ...} instead.\n\n'
    "Full live `masterytrace --help` output at import time:\n\n"
    + _resolve_cli_help()
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
