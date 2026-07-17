import math

import pytest

from masterytrace.core.event_schema import ResponseEvent
from masterytrace.models.irt import IrtConfig, IrtModel, probability_correct

_UINT32_MASK = 0xFFFFFFFF


def _make_lcg(seed):
    """
    Deterministic (seeded) linear congruential generator, matching the one
    used for the bundled sample data and the TypeScript test suite's own
    LCG, so synthetic test datasets are fully reproducible without relying
    on `random`.
    """
    state = seed & _UINT32_MASK

    def _next():
        nonlocal state
        state = (state * 1664525 + 1013904223) & _UINT32_MASK
        return state / _UINT32_MASK

    return _next


def _sigmoid(z):
    if z >= 0:
        e = math.exp(-z)
        return 1 / (1 + e)
    e = math.exp(z)
    return e / (1 + e)


_clock = [0]


def _next_timestamp():
    _clock[0] += 1
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return (base + timedelta(seconds=_clock[0])).isoformat().replace("+00:00", "Z")


def event(learner_id, skill_id, correct):
    return ResponseEvent(learner_id=learner_id, skill_id=skill_id, correct=correct, timestamp=_next_timestamp())


class TestProbabilityCorrect:
    def test_equals_half_when_theta_equals_item_difficulty(self):
        assert probability_correct(0.5, 1.2, 0.5) == pytest.approx(0.5, abs=1e-10)

    def test_increases_with_theta_for_fixed_a_b(self):
        low = probability_correct(-1, 1, 0)
        high = probability_correct(1, 1, 0)
        assert high > low


class TestIrtModel:
    def test_implements_the_scoring_model_interface_with_name_irt(self):
        assert IrtModel().name == "irt"

    def test_fits_and_scores_an_empty_event_log_without_error(self):
        model = IrtModel()
        report = model.score(model.fit([]))
        assert report.model == "irt"
        assert report.learners == []

    def test_handles_a_single_response(self):
        model = IrtModel(IrtConfig(iterations=50))
        events = [event("l1", "s1", True)]
        report = model.score(model.fit(events))
        assert len(report.learners) == 1
        assert math.isfinite(report.learners[0].skills[0].value)

    def test_a_learner_who_aces_a_hard_item_gets_a_higher_theta_than_one_who_aces_an_easy_item(self):
        rand = _make_lcg(7)
        events = []

        # Baseline learners answer both items with a mix of correct/
        # incorrect, which is what lets the model tell the easy item and
        # the hard item apart in the first place.
        for b in range(6):
            learner_id = f"baseline-{b}"
            for _ in range(20):
                events.append(event(learner_id, "easy-skill", rand() < 0.7))
            for _ in range(20):
                events.append(event(learner_id, "hard-skill", rand() < 0.3))

        # Two "ace" learners: each answers only one item, always correctly.
        for _ in range(15):
            events.append(event("easy-ace", "easy-skill", True))
        for _ in range(15):
            events.append(event("hard-ace", "hard-skill", True))

        model = IrtModel()
        fitted = model.fit(events)
        easy_ace_theta = next(l.theta for l in fitted.learners if l.learner_id == "easy-ace")
        hard_ace_theta = next(l.theta for l in fitted.learners if l.learner_id == "hard-ace")

        assert hard_ace_theta > easy_ace_theta

        # Sanity-check the item difficulties actually came out easy <
        # hard, confirming the theta gap above reflects item difficulty
        # and not noise.
        easy_b = next(i.b for i in fitted.items if i.skill_id == "easy-skill")
        hard_b = next(i.b for i in fitted.items if i.skill_id == "hard-skill")
        assert hard_b > easy_b

    def test_recovers_approximately_correct_theta_a_b_from_a_synthetic_dataset_with_known_parameters(self):
        # Known ground truth. theta_true has mean 0 and std 1/sqrt(2); the
        # 2PL model is only identified up to theta's location/scale
        # (z = a*(theta-b) is unchanged by shifting theta and b by the
        # same constant, or by scaling theta/b by s while dividing a by
        # s), and IrtModel's fit pins that gauge by normalizing theta to
        # mean 0 / std 1 every iteration. So the values to compare
        # recovered parameters against are the true values passed through
        # that same normalization, not the raw true values themselves --
        # same setup as test/irt.test.ts's recovery check (b).
        theta_true = [-1.0, -0.5, 0.0, 0.5, 1.0]
        a_true = [0.8, 1.0, 1.2, 1.5]
        b_true = [-1.0, -0.3, 0.4, 1.0]
        learner_ids = [f"learner-{i}" for i in range(len(theta_true))]
        skill_ids = [f"skill-{i}" for i in range(len(a_true))]
        repeats_per_pair = 200

        rand = _make_lcg(1234)
        events = []
        for li in range(len(learner_ids)):
            for ii in range(len(skill_ids)):
                p = _sigmoid(a_true[ii] * (theta_true[li] - b_true[ii]))
                for _ in range(repeats_per_pair):
                    events.append(event(learner_ids[li], skill_ids[ii], rand() < p))

        model = IrtModel()
        fitted = model.fit(events)

        true_mean = sum(theta_true) / len(theta_true)
        true_variance = sum((t - true_mean) ** 2 for t in theta_true) / len(theta_true)
        true_std = math.sqrt(true_variance)

        tolerance = 0.3

        for i, learner_id in enumerate(learner_ids):
            recovered_theta = next(l.theta for l in fitted.learners if l.learner_id == learner_id)
            expected_theta = theta_true[i] / true_std
            assert abs(recovered_theta - expected_theta) < tolerance

        for j, skill_id in enumerate(skill_ids):
            item = next(it for it in fitted.items if it.skill_id == skill_id)
            expected_b = b_true[j] / true_std
            expected_a = a_true[j] * true_std
            assert abs(item.b - expected_b) < tolerance
            assert abs(item.a - expected_a) < tolerance

    def test_scores_each_learner_skill_with_the_predicted_probability_of_a_correct_response_attached(self):
        model = IrtModel(IrtConfig(iterations=50))
        events = [event("l1", "s1", True), event("l1", "s1", True)]
        report = model.score(model.fit(events))
        skill = report.learners[0].skills[0]
        assert skill.metric == "ability_theta"
        predicted = skill.details["predicted_probability_correct"]
        assert 0 < predicted < 1
