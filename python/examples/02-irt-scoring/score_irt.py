#!/usr/bin/env python3
"""
02 -- IRT scoring across skills of different difficulty.

Builds a response log for several learners across an "easy" and a "hard"
skill, fits a 2PL IrtModel, and prints each learner's ability estimate
(theta) alongside each skill's fitted discrimination/difficulty. This
mirrors the shape of the library's own recovery test (see
tests/test_irt.py): learners who aggregate more evidence on both skills
let the model tell the two skills apart, and a learner who only ever
answers the hard skill correctly should come out with a higher ability
estimate than one who only ever answers the easy skill correctly.

Run:
    python3 examples/02-irt-scoring/score_irt.py
"""
import random

from masterytrace import IrtModel, ResponseEvent

_TIMESTAMP_CLOCK = [0]


def _next_timestamp() -> str:
    from datetime import datetime, timedelta, timezone

    _TIMESTAMP_CLOCK[0] += 1
    base = datetime(2026, 2, 1, tzinfo=timezone.utc)
    return (base + timedelta(minutes=_TIMESTAMP_CLOCK[0])).isoformat().replace("+00:00", "Z")


def main() -> None:
    rand = random.Random(42)
    events = []

    # Baseline learners answer both skills with a realistic mix of
    # correct/incorrect -- this is what lets the model tell the easy
    # skill and the hard skill apart in the first place.
    for learner_num in range(6):
        learner_id = f"baseline-{learner_num}"
        for _ in range(15):
            events.append(
                ResponseEvent(learner_id=learner_id, skill_id="easy-arithmetic", correct=rand.random() < 0.75, timestamp=_next_timestamp())
            )
        for _ in range(15):
            events.append(
                ResponseEvent(learner_id=learner_id, skill_id="hard-calculus", correct=rand.random() < 0.35, timestamp=_next_timestamp())
            )

    # Two standout learners: one aces the easy skill, one aces the hard skill.
    for _ in range(12):
        events.append(ResponseEvent(learner_id="easy-ace", skill_id="easy-arithmetic", correct=True, timestamp=_next_timestamp()))
    for _ in range(12):
        events.append(ResponseEvent(learner_id="hard-ace", skill_id="hard-calculus", correct=True, timestamp=_next_timestamp()))

    model = IrtModel()
    fitted = model.fit(events)

    print("Skill parameters (discrimination a, difficulty b):")
    for item in fitted.items:
        print(f"  {item.skill_id}: a={item.a:.3f}, b={item.b:.3f}")

    print("\nLearner ability estimates (theta):")
    for learner in sorted(fitted.learners, key=lambda l: l.theta):
        print(f"  {learner.learner_id}: theta={learner.theta:.3f} ({learner.response_count} responses)")

    easy_ace_theta = next(l.theta for l in fitted.learners if l.learner_id == "easy-ace")
    hard_ace_theta = next(l.theta for l in fitted.learners if l.learner_id == "hard-ace")
    print(
        f"\nhard-ace theta ({hard_ace_theta:.3f}) > easy-ace theta ({easy_ace_theta:.3f}): "
        f"{hard_ace_theta > easy_ace_theta} (acing the harder skill implies higher ability)"
    )


if __name__ == "__main__":
    main()
