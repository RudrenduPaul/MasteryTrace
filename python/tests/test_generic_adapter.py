import json
import os

import pytest

from masterytrace.adapters.generic_adapter import MAX_EVENT_LOG_BYTES, generic_adapter, parse_csv
from masterytrace.core.event_schema import EventValidationError


class TestParseCsv:
    def test_parses_a_well_formed_csv_into_raw_event_shaped_rows(self):
        csv = "learner_id,skill_id,correct,timestamp\n" "l1,s1,true,2026-01-01T00:00:00Z\n" "l1,s1,false,2026-01-02T00:00:00Z\n"
        rows = parse_csv(csv)
        assert len(rows) == 2
        assert rows[0] == {"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"}
        assert rows[1]["correct"] is False

    def test_accepts_1_0_as_boolean_correct_values(self):
        csv = "learner_id,skill_id,correct,timestamp\nl1,s1,1,2026-01-01T00:00:00Z\nl1,s1,0,2026-01-02T00:00:00Z\n"
        rows = parse_csv(csv)
        assert rows[0]["correct"] is True
        assert rows[1]["correct"] is False

    def test_is_tolerant_of_column_reordering_keyed_by_header(self):
        csv = "timestamp,correct,skill_id,learner_id\n2026-01-01T00:00:00Z,true,s1,l1\n"
        rows = parse_csv(csv)
        assert rows[0]["learnerId"] == "l1"
        assert rows[0]["skillId"] == "s1"

    def test_returns_an_empty_list_for_an_empty_or_header_only_file(self):
        assert parse_csv("") == []
        assert parse_csv("learner_id,skill_id,correct,timestamp\n") == []

    def test_raises_when_a_required_column_is_missing(self):
        with pytest.raises(ValueError, match="missing required column"):
            parse_csv("learner_id,skill_id,timestamp\nl1,s1,2026-01-01T00:00:00Z\n")

    def test_does_not_silently_coerce_an_unrecognized_correct_value_to_false(self):
        csv = "learner_id,skill_id,correct,timestamp\nl1,s1,maybe,2026-01-01T00:00:00Z\n"
        rows = parse_csv(csv)
        assert rows[0]["correct"] == "maybe"
        assert rows[0]["correct"] is not False


class TestGenericAdapter:
    def test_loads_and_validates_a_json_event_log(self, tmp_path):
        path = tmp_path / "events.json"
        path.write_text(
            json.dumps([{"learnerId": "l1", "skillId": "s1", "correct": True, "timestamp": "2026-01-01T00:00:00Z"}]),
            encoding="utf-8",
        )
        events = generic_adapter.load(str(path))
        assert len(events) == 1
        assert events[0].learner_id == "l1"

    def test_loads_and_validates_a_csv_event_log(self, tmp_path):
        path = tmp_path / "events.csv"
        path.write_text("learner_id,skill_id,correct,timestamp\nl1,s1,true,2026-01-01T00:00:00Z\n", encoding="utf-8")
        events = generic_adapter.load(str(path))
        assert len(events) == 1
        e = events[0]
        assert (e.learner_id, e.skill_id, e.correct, e.timestamp) == ("l1", "s1", True, "2026-01-01T00:00:00Z")

    def test_raises_event_validation_error_for_malformed_json_event_data(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps([{"learnerId": "l1", "correct": True, "timestamp": "nope"}]), encoding="utf-8")
        with pytest.raises(EventValidationError):
            generic_adapter.load(str(path))

    def test_raises_event_validation_error_for_malformed_csv_event_data(self, tmp_path):
        path = tmp_path / "bad.csv"
        path.write_text("learner_id,skill_id,correct,timestamp\nl1,s1,notabool,not-a-date\n", encoding="utf-8")
        with pytest.raises(EventValidationError):
            generic_adapter.load(str(path))

    def test_raises_for_a_csv_row_with_unrecognized_correct_value_even_with_valid_timestamp(self, tmp_path):
        path = tmp_path / "bad-correct.csv"
        path.write_text("learner_id,skill_id,correct,timestamp\nl1,s1,maybe,2026-01-01T00:00:00Z\n", encoding="utf-8")
        with pytest.raises(EventValidationError):
            generic_adapter.load(str(path))

    def test_refuses_to_read_a_file_larger_than_the_event_log_size_limit(self, tmp_path):
        path = tmp_path / "huge.json"
        # Sparse file: seeking past the end and writing one byte extends
        # the file length without needing real gigabyte-scale I/O, same
        # trick the TS test's ftruncateSync uses.
        with open(path, "wb") as f:
            f.seek(MAX_EVENT_LOG_BYTES)
            f.write(b"\0")
        with pytest.raises(ValueError, match=r"exceeds the .* MB event log size limit"):
            generic_adapter.load(str(path))

    def test_refuses_to_read_a_symlinked_path(self, tmp_path):
        target_path = tmp_path / "real.json"
        target_path.write_text("[]", encoding="utf-8")
        link_path = tmp_path / "link.json"
        os.symlink(target_path, link_path)
        with pytest.raises(ValueError, match=r"(?i)symlink"):
            generic_adapter.load(str(link_path))

    def test_handles_an_empty_json_array(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("[]", encoding="utf-8")
        assert generic_adapter.load(str(path)) == []

    def test_refuses_to_read_a_path_that_is_not_a_regular_file(self, tmp_path):
        with pytest.raises(ValueError, match=r"(?i)not a regular file"):
            generic_adapter.load(str(tmp_path))
