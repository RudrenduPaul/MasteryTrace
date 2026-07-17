import json

from masterytrace.cli.commands.record import RecordOptions, run_record
from masterytrace.cli.commands.score import ScoreOptions, run_score


def _record_sample(tmp_path):
    events_path = tmp_path / "events.json"
    events_path.write_text(
        json.dumps(
            [
                {"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"},
                {"learnerId": "l1", "skillId": "s1", "correct": False, "timestamp": "2026-01-02T00:00:00Z"},
            ]
        ),
        encoding="utf-8",
    )
    run_record(str(tmp_path), str(events_path), RecordOptions(json=False))


def test_returns_exit_code_1_when_no_event_log_has_been_recorded(tmp_path):
    result = run_score(str(tmp_path), ScoreOptions(json=False, model="both"))
    assert result.exit_code == 1


def test_scores_a_recorded_event_log_with_both_models_by_default(tmp_path):
    _record_sample(tmp_path)
    result = run_score(str(tmp_path), ScoreOptions(json=False, model="both"))
    assert result.exit_code == 0
    scores_path = tmp_path / ".masterytrace" / "scores.json"
    assert scores_path.exists()
    scores = json.loads(scores_path.read_text(encoding="utf-8"))
    assert sorted(r["model"] for r in scores["reports"]) == ["bkt", "irt"]


def test_scores_with_only_the_bkt_model_when_requested(tmp_path):
    _record_sample(tmp_path)
    result = run_score(str(tmp_path), ScoreOptions(json=False, model="bkt"))
    assert result.exit_code == 0
    scores = json.loads((tmp_path / ".masterytrace" / "scores.json").read_text(encoding="utf-8"))
    assert [r["model"] for r in scores["reports"]] == ["bkt"]
