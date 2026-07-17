"""
Scaffolds a bundled sample `events.json` (3 learners x 3 skills, several
responses each) and a default `masterytrace.config.json` in `cwd`.
Ported from src/cli/commands/init.ts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ...core.config import DEFAULT_CONFIG
from ...data.sample_events import SAMPLE_EVENTS
from ..format import ok
from ..json_encode import to_jsonable
from ..types import CommandResult

EVENTS_SAMPLE_FILENAME = "events.json"
CONFIG_FILENAME = "masterytrace.config.json"


@dataclass
class InitOptions:
    json: bool
    force: bool


def run_init(cwd: str, options: InitOptions) -> CommandResult:
    """
    Existing files are left untouched unless `--force` is passed.
    """
    events_path = Path(cwd) / EVENTS_SAMPLE_FILENAME
    config_path = Path(cwd) / CONFIG_FILENAME

    created = []
    skipped = []

    if not options.force and events_path.exists():
        skipped.append(EVENTS_SAMPLE_FILENAME)
    else:
        events_path.write_text(json.dumps(to_jsonable(SAMPLE_EVENTS), indent=2) + "\n", encoding="utf-8")
        created.append(EVENTS_SAMPLE_FILENAME)

    if not options.force and config_path.exists():
        skipped.append(CONFIG_FILENAME)
    else:
        config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
        created.append(CONFIG_FILENAME)

    lines = []
    if created:
        lines.append(f"Created: {', '.join(created)}")
    if skipped:
        lines.append(f"Skipped (already exists, use --force to overwrite): {', '.join(skipped)}")
    lines.append("Next: run 'masterytrace record events.json' to load it, then 'masterytrace score'.")

    return ok(options.json, {"created": created, "skipped": skipped}, "\n".join(lines) + "\n")
