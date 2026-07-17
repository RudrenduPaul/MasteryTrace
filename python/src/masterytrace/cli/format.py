"""Builds successful/failing CommandResults, choosing JSON or human text output. Ported from src/cli/format.ts."""
from __future__ import annotations

import json
from typing import Any

from .types import CommandResult


def ok(as_json: bool, json_payload: Any, text: str) -> CommandResult:
    return CommandResult(exit_code=0, stdout=f"{json.dumps(json_payload)}\n" if as_json else text)


def fail(exit_code: int, as_json: bool, json_payload: Any, text: str) -> CommandResult:
    if as_json:
        return CommandResult(exit_code=exit_code, stdout=f"{json.dumps(json_payload)}\n")
    return CommandResult(exit_code=exit_code, stdout="", stderr=text)
