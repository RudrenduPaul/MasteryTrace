"""
Converts the library's dataclass return values (ResponseEvent,
MasteryReport, EngineResult, BktParams, ...) into plain JSON-serializable
dicts for `.masterytrace/*.json` state files and `--json` CLI output.

Two different conventions are used deliberately, matching each value's
role:

- `ResponseEvent` (the event-log wire format read by `parse_response_events`
  and produced by `masterytrace init`/`record`) always serializes to
  **camelCase** (`learnerId`, `skillId`, ...): this is the shared,
  cross-distribution event-log contract with the npm CLI, and
  `parse_response_events` itself only recognizes these camelCase keys, so
  an event log this CLI writes must stay readable by this CLI (and by the
  npm CLI) without a key-casing mismatch.
- Everything else (scores, reports, engine results) serializes to
  **snake_case**, matching Python naming convention -- see
  python/README.md's "deliberate naming divergence" note. These values
  are never fed back through `parse_response_events`, so there is no
  cross-format contract to preserve.
"""
from __future__ import annotations

import dataclasses
from typing import Any, List

from ..core.event_schema import ResponseEvent


def response_event_to_dict(event: ResponseEvent) -> dict:
    return {
        "learnerId": event.learner_id,
        "skillId": event.skill_id,
        "correct": event.correct,
        "timestamp": event.timestamp,
    }


def response_events_to_jsonable(events: List[ResponseEvent]) -> List[dict]:
    return [response_event_to_dict(e) for e in events]


def to_jsonable(value: Any) -> Any:
    if isinstance(value, ResponseEvent):
        return response_event_to_dict(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: to_jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value
