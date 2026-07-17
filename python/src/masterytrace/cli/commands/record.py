"""
Validates and loads an event log (JSON or CSV, chosen by file extension)
and stores it to `.masterytrace/events.json`. Storing always *replaces*
any previously stored log in v0.1 (there is no append/merge mode yet).
Ported from src/cli/commands/record.ts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ...adapters.generic_adapter import generic_adapter
from ...core.event_schema import EventValidationError
from ..format import fail, ok
from ..json_encode import to_jsonable
from ..types import CommandResult

STATE_DIR = ".masterytrace"
EVENTS_STATE_FILENAME = "events.json"


@dataclass
class RecordOptions:
    json: bool


def run_record(cwd: str, event_log_path: str, options: RecordOptions) -> CommandResult:
    try:
        events = generic_adapter.load(event_log_path)
    except EventValidationError as error:
        return fail(
            2,
            options.json,
            {"error": str(error), "issues": error.issues},
            f"Validation error:\n{error}\n",
        )
    except Exception as error:  # noqa: BLE001 -- mirrors the TS catch-all for I/O/parse errors
        return fail(1, options.json, {"error": str(error)}, f"Error: {error}\n")

    state_dir = Path(cwd) / STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / EVENTS_STATE_FILENAME
    state_path.write_text(json.dumps(to_jsonable(events), indent=2) + "\n", encoding="utf-8")

    return ok(
        options.json,
        {"eventCount": len(events), "storedAt": str(state_path)},
        f"Stored {len(events)} event(s) to {state_path}\n"
        "(record replaces any previously stored event log; see --help for details.)\n",
    )
