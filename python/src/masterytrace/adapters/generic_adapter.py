"""
A source of response events: reads a JSON array of response events, or a
CSV file with columns `learner_id,skill_id,correct,timestamp`, chosen by
file extension. Ported from src/adapters/generic-adapter.ts, including its
size guard and its symlink refusal.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, List, Union

from ..core.event_schema import ResponseEvent, parse_response_events

# Event logs are small structured records (a handful of fields per
# response event); there is no legitimate reason for one to approach this
# size. This guard exists for the case where masterytrace is invoked
# programmatically (e.g. by another agent/tool) on a file it did not
# choose itself: without it, an oversized file is read fully into memory
# and handed to json.loads before any validation runs, which can exhaust
# memory or hang the process well before the "not valid event data" error
# a bad file should produce.
MAX_EVENT_LOG_BYTES = 100 * 1024 * 1024  # 100 MB

_CSV_COLUMNS = ("learner_id", "skill_id", "correct", "timestamp")


def _assert_readable_regular_file(path: Union[str, Path]) -> None:
    """
    os.lstat (not os.stat) never follows a symlink, so a symlink at
    `path` is caught here even if its target is a regular file elsewhere
    on disk.
    """
    stats = os.lstat(path)
    import stat as stat_module

    if stat_module.S_ISLNK(stats.st_mode):
        raise ValueError(f"Refusing to read '{path}': symlinks are not supported for event log paths.")
    if not stat_module.S_ISREG(stats.st_mode):
        raise ValueError(f"Refusing to read '{path}': not a regular file.")
    if stats.st_size > MAX_EVENT_LOG_BYTES:
        size_mb = stats.st_size / (1024 * 1024)
        limit_mb = MAX_EVENT_LOG_BYTES / (1024 * 1024)
        raise ValueError(
            f"Refusing to read '{path}': file is {size_mb:.1f} MB, which exceeds the {limit_mb:.0f} MB event log size limit."
        )


def _parse_csv_boolean(raw: str) -> Union[bool, str]:
    """
    Parses a CSV `correct` cell into a boolean. Only recognizes
    `true`/`false` and `1`/`0` (case-insensitive, trimmed); anything else
    is returned as the original raw string rather than silently guessed.
    That matters: coercing every unrecognized value to False would make a
    typo, an empty cell from a shifted column, or a "yes"/"no" export
    format silently record as an incorrect response instead of surfacing
    as bad data. Returning the raw string instead lets it fail
    ResponseEvent validation's `correct` boolean check with a clear,
    row-numbered validation error, exactly like malformed JSON input does.
    """
    normalized = raw.strip().lower()
    if normalized in ("true", "1"):
        return True
    if normalized in ("false", "0"):
        return False
    return raw


def parse_csv(content: str) -> List[Any]:
    """
    Parses the fixed-column CSV format (`learner_id,skill_id,correct,
    timestamp`) into the raw row shape event-schema expects, so it goes
    through the same validation as JSON input. Deliberately hand-rolled
    rather than pulling in a CSV library: the format has no quoting/
    escaping requirements (skill and learner ids are plain identifiers),
    so a dependency would buy nothing.
    """
    lines = [line for line in content.splitlines() if line.strip()]
    if not lines:
        return []

    header = [h.strip() for h in lines[0].split(",")]
    column_index = {name: i for i, name in enumerate(header)}
    for required in _CSV_COLUMNS:
        if required not in column_index:
            raise ValueError(
                f"CSV event log is missing required column '{required}'. Expected header: {','.join(_CSV_COLUMNS)}"
            )

    rows: List[Any] = []
    for line in lines[1:]:
        cells = line.split(",")

        def cell(name: str) -> str:
            index = column_index.get(name)
            if index is None or index >= len(cells):
                return ""
            return cells[index].strip()

        rows.append(
            {
                "learnerId": cell("learner_id"),
                "skillId": cell("skill_id"),
                "correct": _parse_csv_boolean(cell("correct")),
                "timestamp": cell("timestamp"),
            }
        )
    return rows


class GenericAdapter:
    """
    The only event-log adapter shipped in v0.1: reads a JSON array of
    response events, or a CSV file with columns
    `learner_id,skill_id,correct,timestamp`, chosen by file extension.
    """

    name = "generic"

    def load(self, path: Union[str, Path]) -> List[ResponseEvent]:
        _assert_readable_regular_file(path)
        content = Path(path).read_text(encoding="utf-8")
        extension = Path(path).suffix.lower()

        if extension == ".csv":
            raw: Any = parse_csv(content)
        else:
            raw = json.loads(content)

        return parse_response_events(raw)


generic_adapter = GenericAdapter()
