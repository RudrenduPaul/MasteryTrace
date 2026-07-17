import pytest

from masterytrace.core.event_schema import EventValidationError, parse_response_events


def test_accepts_a_well_formed_event():
    events = parse_response_events(
        [{"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"}]
    )
    assert len(events) == 1
    e = events[0]
    assert (e.learner_id, e.skill_id, e.correct, e.timestamp) == ("l1", "s1", True, "2026-01-01T00:00:00Z")


def test_accepts_multiple_valid_events_and_preserves_order():
    raw = [
        {"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"},
        {"learnerId": "l1", "skillId": "s1", "correct": False, "timestamp": "2026-01-02T00:00:00Z"},
    ]
    events = parse_response_events(raw)
    assert [e.correct for e in events] == [True, False]


def test_rejects_a_non_array_top_level_value():
    with pytest.raises(EventValidationError):
        parse_response_events({"not": "an array"})


def test_rejects_an_empty_string_learner_id():
    with pytest.raises(EventValidationError):
        parse_response_events([{"learnerId": "", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"}])


def test_rejects_a_missing_skill_id_field():
    with pytest.raises(EventValidationError) as exc_info:
        parse_response_events([{"learnerId": "l1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"}])
    issues = exc_info.value.issues
    assert any("field 'skillId'" in issue for issue in issues)
    assert any(issue.startswith("row 0") for issue in issues)


def test_rejects_a_non_boolean_correct_field():
    with pytest.raises(EventValidationError) as exc_info:
        parse_response_events([{"learnerId": "l1", "skillId": "s1", "correct": "yes", "timestamp": "2026-01-01T00:00:00Z"}])
    assert any("field 'correct'" in issue for issue in exc_info.value.issues)


def test_rejects_an_invalid_non_iso8601_timestamp():
    with pytest.raises(EventValidationError) as exc_info:
        parse_response_events([{"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "not-a-date"}])
    assert any("field 'timestamp'" in issue for issue in exc_info.value.issues)


def test_reports_every_failing_row_and_field_not_just_the_first():
    with pytest.raises(EventValidationError) as exc_info:
        parse_response_events(
            [
                {"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"},
                {"learnerId": "", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"},
                {"learnerId": "l1", "skillId": "s1", "correct": "nope", "timestamp": "bad-timestamp"},
            ]
        )
    issues = exc_info.value.issues
    assert any(issue.startswith("row 1") for issue in issues)
    assert len([issue for issue in issues if issue.startswith("row 2")]) == 2


def test_accepts_an_empty_array_empty_event_log():
    assert parse_response_events([]) == []
