import json

from masterytrace.cli.commands.init import InitOptions, run_init
from masterytrace.core.event_schema import parse_response_events


def test_scaffolds_a_valid_sample_events_json_and_a_config_file(tmp_path):
    result = run_init(str(tmp_path), InitOptions(json=False, force=False))
    assert result.exit_code == 0
    assert (tmp_path / "events.json").exists()
    assert (tmp_path / "masterytrace.config.json").exists()

    raw = json.loads((tmp_path / "events.json").read_text(encoding="utf-8"))
    events = parse_response_events(raw)
    assert len(events) > 0

    learner_count = len({e.learner_id for e in events})
    skill_count = len({e.skill_id for e in events})
    assert learner_count >= 3
    assert skill_count >= 3


def test_does_not_overwrite_existing_files_without_force(tmp_path):
    (tmp_path / "events.json").write_text('"sentinel"', encoding="utf-8")
    result = run_init(str(tmp_path), InitOptions(json=False, force=False))
    assert result.exit_code == 0
    assert "Skipped" in result.stdout
    assert (tmp_path / "events.json").read_text(encoding="utf-8") == '"sentinel"'


def test_overwrites_existing_files_when_force_is_passed(tmp_path):
    (tmp_path / "events.json").write_text('"sentinel"', encoding="utf-8")
    result = run_init(str(tmp_path), InitOptions(json=False, force=True))
    assert result.exit_code == 0
    assert (tmp_path / "events.json").read_text(encoding="utf-8") != '"sentinel"'


def test_skips_both_files_when_both_already_exist_and_force_not_passed(tmp_path):
    (tmp_path / "events.json").write_text('"sentinel"', encoding="utf-8")
    (tmp_path / "masterytrace.config.json").write_text('"sentinel"', encoding="utf-8")
    result = run_init(str(tmp_path), InitOptions(json=False, force=False))
    assert result.exit_code == 0
    assert not any(line.startswith("Created:") for line in result.stdout.splitlines())
    assert "Skipped" in result.stdout


def test_emits_machine_readable_json_when_json_is_set(tmp_path):
    result = run_init(str(tmp_path), InitOptions(json=True, force=False))
    parsed = json.loads(result.stdout)
    assert sorted(parsed["created"]) == ["events.json", "masterytrace.config.json"]
