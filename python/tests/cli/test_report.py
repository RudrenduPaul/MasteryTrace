import json

from masterytrace.cli.commands.record import RecordOptions, run_record
from masterytrace.cli.commands.report import ReportOptions, run_report
from masterytrace.cli.commands.score import ScoreOptions, run_score


def _record_and_score(tmp_path):
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
    run_score(str(tmp_path), ScoreOptions(json=False, model="both"))


def test_returns_exit_code_1_when_no_scores_exist(tmp_path):
    result = run_report(str(tmp_path), ReportOptions(json=False, format="table"))
    assert result.exit_code == 1


def test_renders_a_table_by_default(tmp_path):
    _record_and_score(tmp_path)
    result = run_report(str(tmp_path), ReportOptions(json=False, format="table"))
    assert result.exit_code == 0
    assert "learner" in result.stdout
    assert "l1" in result.stdout


def test_renders_markdown_when_requested(tmp_path):
    _record_and_score(tmp_path)
    result = run_report(str(tmp_path), ReportOptions(json=False, format="markdown"))
    assert result.exit_code == 0
    assert "|" in result.stdout


def test_renders_json_when_requested(tmp_path):
    _record_and_score(tmp_path)
    result = run_report(str(tmp_path), ReportOptions(json=False, format="json"))
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert "reports" in parsed
