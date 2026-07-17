"""
A single learner response event: one attempt by one learner at one skill,
scored correct/incorrect, at a point in time.

This is the only unit of data every scoring model and adapter in
MasteryTrace operates on. Ported from src/core/event-schema.ts, which uses
`zod` for validation; this port hand-rolls the equivalent field checks
(learnerId/skillId non-empty strings, correct a bool, timestamp a parseable
ISO 8601 string) to avoid a validation-library dependency the TypeScript
side has but the Python side does not need for four fields.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List


@dataclass(frozen=True)
class ResponseEvent:
    learner_id: str
    skill_id: str
    correct: bool
    timestamp: str


class EventValidationError(Exception):
    """
    Raised when an event log fails validation. `issues` lists every
    field/row failure found, so a caller (or the CLI) can report all
    problems at once instead of stopping at the first one -- matching the
    TypeScript EventValidationError contract exactly (same field name,
    same "row N: field 'x' - message" issue format).
    """

    def __init__(self, message: str, issues: List[str]) -> None:
        super().__init__(message)
        self.issues = issues


def _is_valid_iso8601(value: str) -> bool:
    """
    Mirrors `!Number.isNaN(Date.parse(value))` closely enough for the
    timestamps this project actually produces and accepts (ISO 8601,
    optionally with a trailing 'Z'). datetime.fromisoformat() is stricter
    than JS's Date.parse() about some non-standard formats, but every
    timestamp MasteryTrace itself generates (sample data, CLI-recorded
    logs) is a real ISO 8601 string, so this does not reject valid
    MasteryTrace data.
    """
    if not isinstance(value, str) or value == "":
        return False
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(candidate)
        return True
    except ValueError:
        return False


def _validate_row(row: Any, index: int, issues: List[str]) -> ResponseEvent | None:
    if not isinstance(row, dict):
        issues.append(f"row {index}: field '(row)' - expected an object")
        return None

    ok = True

    learner_id = row.get("learnerId")
    if not isinstance(learner_id, str):
        issues.append(f"row {index}: field 'learnerId' - learnerId must be a string")
        ok = False
    elif len(learner_id) < 1:
        issues.append(f"row {index}: field 'learnerId' - learnerId must be a non-empty string")
        ok = False

    skill_id = row.get("skillId")
    if not isinstance(skill_id, str):
        issues.append(f"row {index}: field 'skillId' - skillId must be a string")
        ok = False
    elif len(skill_id) < 1:
        issues.append(f"row {index}: field 'skillId' - skillId must be a non-empty string")
        ok = False

    correct = row.get("correct")
    if not isinstance(correct, bool):
        issues.append(f"row {index}: field 'correct' - correct must be a boolean")
        ok = False

    timestamp = row.get("timestamp")
    if not isinstance(timestamp, str):
        issues.append(f"row {index}: field 'timestamp' - timestamp must be an ISO 8601 date string")
        ok = False
    elif not _is_valid_iso8601(timestamp):
        issues.append(f"row {index}: field 'timestamp' - timestamp must be a valid ISO 8601 date string")
        ok = False

    if not ok:
        return None
    return ResponseEvent(learner_id=learner_id, skill_id=skill_id, correct=correct, timestamp=timestamp)


def parse_response_events(raw: Any) -> List[ResponseEvent]:
    """
    Parses an unknown value (typically json.load output or rows decoded
    from CSV) into a validated list of ResponseEvent. Every row is
    checked; on failure the error lists every failing row/field, not just
    the first.
    """
    if not isinstance(raw, list):
        raise EventValidationError(
            "Event log must be a JSON array of response events (row 0: expected array, got "
            f"{type(raw).__name__})",
            ["row 0: expected an array of response events"],
        )

    events: List[ResponseEvent] = []
    issues: List[str] = []

    for index, row in enumerate(raw):
        event = _validate_row(row, index, issues)
        if event is not None:
            events.append(event)

    if issues:
        plural = "" if len(issues) == 1 else "s"
        raise EventValidationError(
            f"Event log failed validation ({len(issues)} issue{plural}):\n" + "\n".join(issues),
            issues,
        )

    return events
