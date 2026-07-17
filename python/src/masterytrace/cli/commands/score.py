"""
Fits and scores the stored event log (`.masterytrace/events.json`,
written by `masterytrace record`) with the requested model(s), writing
the unified report(s) to `.masterytrace/scores.json`. Ported from
src/cli/commands/score.ts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ...core.config import bkt_config_from_dict, irt_config_from_dict, load_config
from ...core.engine import EngineConfig, ModelSelector, run_scoring
from ...core.event_schema import EventValidationError, parse_response_events
from ..format import fail, ok
from ..json_encode import to_jsonable
from ..types import CommandResult
from .record import EVENTS_STATE_FILENAME, STATE_DIR

SCORES_STATE_FILENAME = "scores.json"


@dataclass
class ScoreOptions:
    json: bool
    model: ModelSelector


def run_score(cwd: str, options: ScoreOptions) -> CommandResult:
    events_path = Path(cwd) / STATE_DIR / EVENTS_STATE_FILENAME
    if not events_path.exists():
        message = f"No stored event log found at {events_path}. Run 'masterytrace record <path>' first."
        return fail(1, options.json, {"error": message}, f"{message}\n")

    try:
        raw = json.loads(events_path.read_text(encoding="utf-8"))
        events = parse_response_events(raw)
    except EventValidationError as error:
        return fail(
            2,
            options.json,
            {"error": str(error), "issues": error.issues},
            f"Validation error:\n{error}\n",
        )
    except Exception as error:  # noqa: BLE001 -- mirrors the TS catch-all for parse errors
        return fail(1, options.json, {"error": str(error)}, f"Error: {error}\n")

    raw_config = load_config(cwd)
    config = EngineConfig(
        bkt=bkt_config_from_dict(raw_config.get("bkt")),
        irt=irt_config_from_dict(raw_config.get("irt")),
    )
    result = run_scoring(events, options.model, config)

    scores_path = Path(cwd) / STATE_DIR / SCORES_STATE_FILENAME
    scores_path.write_text(json.dumps(to_jsonable(result), indent=2) + "\n", encoding="utf-8")

    return ok(
        options.json,
        {"model": options.model, "eventCount": len(events), "storedAt": str(scores_path)},
        f"Scored {len(events)} event(s) with model(s): {options.model}\nWrote {scores_path}\n",
    )
