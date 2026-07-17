"""
Exercises the CLI's argument-parsing/dispatch layer (masterytrace.cli.
index.run_cli) end to end, in-process, mirroring test/cli-e2e.test.ts's
subprocess-based coverage of the same init -> record -> score -> report
pipeline and exit-code contract. Run in-process (rather than as a real
subprocess against an installed console script) so the suite has no
build/install step as a prerequisite; the actual installed console script
is verified separately as part of the packaging gate (see
CONTRIBUTING.md's "build and verify a real install" section).
"""
import json

from masterytrace.cli.index import run_cli


def test_help_output_lists_all_four_subcommands(capsys):
    exit_code = run_cli(["masterytrace", "--help"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "init" in captured.out
    assert "record" in captured.out
    assert "score" in captured.out
    assert "report" in captured.out


def test_runs_the_full_pipeline_with_exit_code_0_at_each_step(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert run_cli(["masterytrace", "init"]) == 0
    assert run_cli(["masterytrace", "record", "events.json"]) == 0
    assert run_cli(["masterytrace", "score"]) == 0
    capsys.readouterr()
    assert run_cli(["masterytrace", "report"]) == 0
    captured = capsys.readouterr()
    assert "learner" in captured.out


def test_exits_1_when_scoring_before_any_event_log_has_been_recorded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert run_cli(["masterytrace", "score"]) == 1


def test_exits_2_for_a_validation_error_via_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bad.json").write_text(
        json.dumps([{"learnerId": "", "skillId": "s", "correct": True, "timestamp": "x"}]), encoding="utf-8"
    )
    exit_code = run_cli(["masterytrace", "--json", "record", "bad.json"])
    assert exit_code == 2
    captured = capsys.readouterr()
    json.loads(captured.out)  # must be valid JSON
