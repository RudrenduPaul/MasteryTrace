import pytest

from masterytrace.core.event_schema import ResponseEvent
from masterytrace.models.bkt import (
    BKT_DEFAULT_PARAMS,
    BktConfig,
    BktModel,
    fit_skill_params_by_grid_search,
    run_forward_recursion,
)


def event(learner_id, skill_id, correct, timestamp):
    return ResponseEvent(learner_id=learner_id, skill_id=skill_id, correct=correct, timestamp=timestamp)


class TestRunForwardRecursion:
    # Worked by hand with p_init=0.4, p_transit=0.3, p_slip=0.1, p_guess=0.2
    # for the response sequence [correct, incorrect, correct, correct, incorrect].
    # Same worked example as test/bkt.test.ts's hand-computed values
    # (see that file's comments for the full step-by-step derivation).
    expected_posteriors = [
        0.75,
        33 / 89,
        2241 / 2633,
        106137 / 108881,
        534801 / 611633,
    ]

    def test_matches_the_hand_computed_posteriors_within_floating_point_tolerance(self):
        posteriors = run_forward_recursion([True, False, True, True, False], BKT_DEFAULT_PARAMS)
        assert len(posteriors) == 5
        for p, expected in zip(posteriors, self.expected_posteriors):
            assert p == pytest.approx(expected, abs=1e-10)

    def test_starts_from_p_init_as_the_implicit_prior_before_any_response(self):
        assert run_forward_recursion([], BKT_DEFAULT_PARAMS) == []

    def test_handles_a_single_response(self):
        posteriors = run_forward_recursion([True], BKT_DEFAULT_PARAMS)
        assert len(posteriors) == 1
        assert posteriors[0] == pytest.approx(0.75, abs=1e-10)

    def test_increases_mastery_monotonically_across_an_all_correct_streak(self):
        posteriors = run_forward_recursion([True, True, True, True, True], BKT_DEFAULT_PARAMS)
        for i in range(1, len(posteriors)):
            assert posteriors[i] > posteriors[i - 1]
        assert posteriors[-1] > 0.99

    def test_keeps_mastery_low_but_non_zero_across_an_all_incorrect_streak(self):
        posteriors = run_forward_recursion([False, False, False, False, False], BKT_DEFAULT_PARAMS)
        assert posteriors[-1] < 0.2
        for p in posteriors:
            assert 0 < p < 1


class TestFitSkillParamsByGridSearch:
    def test_returns_a_bktparams_object_with_all_four_fields_in_valid_ranges(self):
        sequences = [
            [True, True, True, True, True],
            [True, True, False, True, True],
        ]
        fitted = fit_skill_params_by_grid_search(sequences)
        for value in (fitted.p_init, fitted.p_transit, fitted.p_slip, fitted.p_guess):
            assert 0 <= value <= 1

    def test_prefers_a_high_p_init_p_transit_combination_for_an_always_correct_learner(self):
        sequences = [[True, True, True, True, True, True]]
        fitted = fit_skill_params_by_grid_search(sequences)
        assert fitted.p_init >= 0.5


class TestBktModel:
    def test_implements_the_scoring_model_interface_with_name_bkt(self):
        assert BktModel().name == "bkt"

    def test_fits_and_scores_an_empty_event_log_without_error(self):
        model = BktModel()
        report = model.score(model.fit([]))
        assert report.model == "bkt"
        assert report.learners == []

    def test_groups_results_per_learner_and_per_skill_applying_default_params(self):
        events = [
            event("l1", "s1", True, "2026-01-01T00:00:00Z"),
            event("l1", "s1", False, "2026-01-02T00:00:00Z"),
            event("l1", "s2", True, "2026-01-01T00:00:00Z"),
            event("l2", "s1", True, "2026-01-01T00:00:00Z"),
        ]
        model = BktModel()
        report = model.score(model.fit(events))

        assert len(report.learners) == 2
        l1 = next(l for l in report.learners if l.learner_id == "l1")
        assert len(l1.skills) == 2
        l1s1 = next(s for s in l1.skills if s.skill_id == "s1")
        assert l1s1.response_count == 2
        assert l1s1.metric == "posterior_mastery_probability"
        assert 0 < l1s1.value < 1

    def test_processes_events_out_of_input_order_by_chronological_timestamp(self):
        out_of_order = [
            event("l1", "s1", True, "2026-01-03T00:00:00Z"),
            event("l1", "s1", False, "2026-01-01T00:00:00Z"),
            event("l1", "s1", True, "2026-01-02T00:00:00Z"),
        ]
        in_order = [
            event("l1", "s1", False, "2026-01-01T00:00:00Z"),
            event("l1", "s1", True, "2026-01-02T00:00:00Z"),
            event("l1", "s1", True, "2026-01-03T00:00:00Z"),
        ]
        model = BktModel()
        report_a = model.score(model.fit(out_of_order))
        report_b = model.score(model.fit(in_order))
        assert report_a.learners[0].skills[0].value == pytest.approx(report_b.learners[0].skills[0].value, abs=1e-10)

    def test_handles_a_single_response_for_a_learner_skill(self):
        model = BktModel()
        report = model.score(model.fit([event("l1", "s1", True, "2026-01-01T00:00:00Z")]))
        assert report.learners[0].skills[0].response_count == 1
        assert report.learners[0].skills[0].value == pytest.approx(0.75, abs=1e-10)

    def test_applies_a_per_skill_parameter_override(self):
        events = [event("l1", "s1", True, "2026-01-01T00:00:00Z")]
        model = BktModel(BktConfig(skill_params={"s1": {"p_init": 0.9}}))
        fitted = model.fit(events)
        assert fitted.params["s1"].p_init == 0.9

    def test_keeps_two_distinct_learner_skill_pairs_separate_even_with_a_shared_char(self):
        # Regression test mirroring the TS suite: two distinct
        # (learnerId, skillId) pairs must never collide even if one id
        # contains a character that could look like a separator.
        events = [
            event("a ", "b", True, "2026-01-01T00:00:00Z"),
            event("a", " b", False, "2026-01-01T00:00:00Z"),
        ]
        model = BktModel()
        report = model.score(model.fit(events))

        assert len(report.learners) == 2
        learner_a0 = next(l for l in report.learners if l.learner_id == "a ")
        learner_a = next(l for l in report.learners if l.learner_id == "a")
        assert len(learner_a0.skills) == 1
        assert learner_a0.skills[0].skill_id == "b"
        assert len(learner_a.skills) == 1
        assert learner_a.skills[0].skill_id == " b"

    def test_uses_grid_search_fitting_when_config_fit_is_true(self):
        events = [
            event("l1", "s1", True, "2026-01-01T00:00:00Z"),
            event("l1", "s1", True, "2026-01-02T00:00:00Z"),
            event("l1", "s1", True, "2026-01-03T00:00:00Z"),
            event("l2", "s1", True, "2026-01-01T00:00:00Z"),
            event("l2", "s1", True, "2026-01-02T00:00:00Z"),
            event("l2", "s1", True, "2026-01-03T00:00:00Z"),
        ]
        model = BktModel(BktConfig(fit=True))
        fitted = model.fit(events)
        assert fitted.params["s1"].p_init > BKT_DEFAULT_PARAMS.p_init
