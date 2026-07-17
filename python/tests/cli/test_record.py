import json

from masterytrace.cli.commands.record import RecordOptions, run_record


def test_validates_and_stores_a_json_event_log(tmp_path):
    events_path = tmp_path / "events.json"
    events_path.write_text(
        json.dumps([{"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"}]),
        encoding="utf-8",
    )
    result = run_record(str(tmp_path), str(events_path), RecordOptions(json=False))
    assert result.exit_code == 0
    stored = tmp_path / ".masterytrace" / "events.json"
    assert stored.exists()
    stored_events = json.loads(stored.read_text(encoding="utf-8"))
    assert len(stored_events) == 1


def test_replaces_a_previously_stored_event_log(tmp_path):
    first_path = tmp_path / "first.json"
    first_path.write_text(
        json.dumps([{"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"}]),
        encoding="utf-8",
    )
    second_path = tmp_path / "second.json"
    second_path.write_text(json.dumps([]), encoding="utf-8")

    run_record(str(tmp_path), str(first_path), RecordOptions(json=False))
    result = run_record(str(tmp_path), str(second_path), RecordOptions(json=False))
    assert result.exit_code == 0
    stored = json.loads((tmp_path / ".masterytrace" / "events.json").read_text(encoding="utf-8"))
    assert stored == []


def test_returns_exit_code_2_for_a_validation_error(tmp_path):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps([{"learnerId": "", "skillId": "s1", "correct": True, "timestamp": "x"}]), encoding="utf-8")
    result = run_record(str(tmp_path), str(bad_path), RecordOptions(json=False))
    assert result.exit_code == 2


def test_returns_exit_code_1_for_a_missing_file(tmp_path):
    result = run_record(str(tmp_path), str(tmp_path / "does-not-exist.json"), RecordOptions(json=False))
    assert result.exit_code == 1
