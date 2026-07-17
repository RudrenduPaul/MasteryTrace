#!/usr/bin/env python3
"""
01 -- basic BKT fit.

The simplest possible use of the library: build a small response log for
one learner attempting one skill, fit a BktModel, and print the posterior
mastery trajectory after each response. No files, no CLI -- just the
library API.

Run:
    python3 examples/01-basic-bkt-fit/fit_bkt.py
"""
from masterytrace import BktModel, ResponseEvent

TIMESTAMPS = [
    "2026-01-01T09:00:00Z",
    "2026-01-01T09:05:00Z",
    "2026-01-01T09:10:00Z",
    "2026-01-02T09:00:00Z",
    "2026-01-02T09:05:00Z",
]
# A learner who starts shaky and improves: wrong, wrong, right, right, right.
RESULTS = [False, False, True, True, True]


def main() -> None:
    events = [
        ResponseEvent(learner_id="learner-1", skill_id="long-division", correct=correct, timestamp=timestamp)
        for correct, timestamp in zip(RESULTS, TIMESTAMPS)
    ]

    model = BktModel()
    fitted = model.fit(events)
    report = model.score(fitted)

    print(f"Model: {report.model}")
    skill_params = fitted.params["long-division"]
    print(
        f"Parameters used: p_init={skill_params.p_init}, p_transit={skill_params.p_transit}, "
        f"p_slip={skill_params.p_slip}, p_guess={skill_params.p_guess}"
    )

    skill = report.learners[0].skills[0]
    print(f"\nlearner-1 / long-division -- final mastery: {skill.value:.4f} ({skill.response_count} responses)")
    print("Posterior after each response:")
    for i, posterior in enumerate(skill.details["posterior_history"]):
        outcome = "correct" if RESULTS[i] else "incorrect"
        print(f"  response {i + 1} ({outcome}): P(mastery) = {posterior:.4f}")


if __name__ == "__main__":
    main()
