"""
Reads `.masterytrace/scores.json` (written by `masterytrace score`) and
prints a per-learner, per-skill mastery table in the requested format.
Ported from src/cli/commands/report.ts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from ..format import fail
from ..types import CommandResult
from .record import STATE_DIR
from .score import SCORES_STATE_FILENAME

ReportFormat = str  # "table" | "json" | "markdown"


@dataclass
class ReportOptions:
    json: bool
    format: ReportFormat


def _build_rows(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for report in result.get("reports", []):
        for learner in report.get("learners", []):
            for skill in learner.get("skills", []):
                rows.append(
                    {
                        "learner_id": learner["learner_id"],
                        "skill_id": skill["skill_id"],
                        "model": report["model"],
                        "metric": skill["metric"],
                        "value": skill["value"],
                        "response_count": skill["response_count"],
                    }
                )
    rows.sort(key=lambda r: (r["learner_id"], r["skill_id"], r["model"]))
    return rows


_TABLE_HEADER = ["learner", "skill", "model", "metric", "value", "responses"]


def _render_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "No scores found.\n"
    data = [
        [r["learner_id"], r["skill_id"], r["model"], r["metric"], f"{r['value']:.4f}", str(r["response_count"])]
        for r in rows
    ]
    widths = [max(len(_TABLE_HEADER[i]), *(len(row[i]) for row in data)) for i in range(len(_TABLE_HEADER))]

    def render_row(cells: List[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [render_row(_TABLE_HEADER), render_row(["-" * w for w in widths])]
    lines.extend(render_row(row) for row in data)
    return "\n".join(lines) + "\n"


def _render_markdown(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "No scores found.\n"
    lines = [
        f"| {' | '.join(_TABLE_HEADER)} |",
        f"| {' | '.join('---' for _ in _TABLE_HEADER)} |",
    ]
    for r in rows:
        lines.append(
            f"| {r['learner_id']} | {r['skill_id']} | {r['model']} | {r['metric']} | {r['value']:.4f} | {r['response_count']} |"
        )
    return "\n".join(lines) + "\n"


def run_report(cwd: str, options: ReportOptions) -> CommandResult:
    scores_path = Path(cwd) / STATE_DIR / SCORES_STATE_FILENAME
    if not scores_path.exists():
        message = f"No scores found at {scores_path}. Run 'masterytrace score' first."
        return fail(1, options.json, {"error": message}, f"{message}\n")

    try:
        result = json.loads(scores_path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 -- mirrors the TS catch-all for parse errors
        return fail(1, options.json, {"error": str(error)}, f"Error reading scores: {error}\n")

    if options.json:
        return CommandResult(exit_code=0, stdout=f"{json.dumps(result)}\n")

    rows = _build_rows(result)
    if options.format == "markdown":
        text = _render_markdown(rows)
    elif options.format == "json":
        text = json.dumps(result, indent=2) + "\n"
    else:
        text = _render_table(rows)

    return CommandResult(exit_code=0, stdout=text)
