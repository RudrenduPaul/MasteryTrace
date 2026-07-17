from datetime import datetime

import pytest

from masterytrace.core.engine import EngineConfig, run_scoring
from masterytrace.core.event_schema import ResponseEvent
from masterytrace.models.bkt import BktConfig

EVENTS = [
    ResponseEvent(learner_id="l1", skill_id="s1", correct=True, timestamp="2026-01-01T00:00:00Z"),
    ResponseEvent(learner_id="l1", skill_id="s1", correct=False, timestamp="2026-01-02T00:00:00Z"),
    ResponseEvent(learner_id="l2", skill_id="s1", correct=True, timestamp="2026-01-01T00:00:00Z"),
]


def test_defaults_to_running_both_models():
    result = run_scoring(EVENTS)
    assert sorted(r.model for r in result.reports) == ["bkt", "irt"]


def test_runs_only_bkt_when_selector_is_bkt():
    result = run_scoring(EVENTS, "bkt")
    assert len(result.reports) == 1
    assert result.reports[0].model == "bkt"


def test_runs_only_irt_when_selector_is_irt():
    result = run_scoring(EVENTS, "irt")
    assert len(result.reports) == 1
    assert result.reports[0].model == "irt"


def test_passes_per_model_config_through_to_the_underlying_models():
    result = run_scoring(EVENTS, "bkt", EngineConfig(bkt=BktConfig(default_params={"p_init": 0.9})))
    bkt_report = result.reports[0]
    assert bkt_report.meta["params"]["s1"].p_init == 0.9


def test_produces_an_iso8601_generated_at_timestamp():
    result = run_scoring(EVENTS)
    # Trailing 'Z' is stripped to feed a stdlib-parseable ISO string.
    datetime.fromisoformat(result.generated_at.replace("Z", "+00:00"))


def test_handles_an_empty_event_log_for_both_models():
    result = run_scoring([], "both")
    assert len(result.reports) == 2
    for report in result.reports:
        assert report.learners == []
