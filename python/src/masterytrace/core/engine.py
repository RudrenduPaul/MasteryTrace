"""
Orchestrates the scoring pipeline: given a validated event log, runs
whichever model(s) were requested and returns their reports together.
Ported from src/core/engine.ts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Literal, Optional

from ..models.bkt import BktConfig, BktModel
from ..models.irt import IrtConfig, IrtModel
from .event_schema import ResponseEvent
from .scoring_model import MasteryReport

ModelSelector = Literal["bkt", "irt", "both"]


@dataclass
class EngineConfig:
    bkt: Optional[BktConfig] = None
    irt: Optional[IrtConfig] = None


@dataclass
class EngineResult:
    generated_at: str
    reports: List[MasteryReport] = field(default_factory=list)


def run_scoring(
    events: List[ResponseEvent],
    selector: ModelSelector = "both",
    config: Optional[EngineConfig] = None,
) -> EngineResult:
    """
    Runs whichever model(s) were requested and returns their reports
    together. This is the single place that knows how to wire the engine
    config into concrete model instances; callers (CLI or library
    consumers) only pick a model selector and pass raw events.
    """
    config = config or EngineConfig()
    reports: List[MasteryReport] = []

    if selector in ("bkt", "both"):
        model = BktModel(config.bkt)
        reports.append(model.score(model.fit(events)))

    if selector in ("irt", "both"):
        model = IrtModel(config.irt)
        reports.append(model.score(model.fit(events)))

    return EngineResult(generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), reports=reports)
