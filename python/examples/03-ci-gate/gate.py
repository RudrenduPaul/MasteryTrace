#!/usr/bin/env python3
"""
03 -- CI gate.

Loads an event log from disk (JSON or CSV, via the same generic_adapter
the CLI's `record` command uses), scores it with BKT, and exits non-zero
if any learner's mastery on a required skill falls below a threshold --
the shape of check you would actually drop into a CI script to gate a
release on a cohort's measured mastery, rather than just printing a
report. Uses `data/sample_events.py`'s bundled sample data (the same data
`masterytrace init` scaffolds) so it runs standalone with no setup beyond
`pip install -e .` (or `pip install masterytrace-cli`) from the python/
directory.

Run:
    python3 examples/03-ci-gate/gate.py
"""
import sys

from masterytrace import BktModel
from masterytrace.data.sample_events import SAMPLE_EVENTS

REQUIRED_SKILL = "fractions"
MASTERY_THRESHOLD = 0.5


def main() -> int:
    model = BktModel()
    report = model.score(model.fit(SAMPLE_EVENTS))

    below_threshold = []
    for learner in report.learners:
        skill = next((s for s in learner.skills if s.skill_id == REQUIRED_SKILL), None)
        if skill is None:
            continue
        status = "PASS" if skill.value >= MASTERY_THRESHOLD else "FAIL"
        print(f"{learner.learner_id}: {REQUIRED_SKILL} mastery = {skill.value:.4f} [{status}]")
        if skill.value < MASTERY_THRESHOLD:
            below_threshold.append(learner.learner_id)

    if below_threshold:
        print(f"\nGate FAILED: {len(below_threshold)} learner(s) below {MASTERY_THRESHOLD} mastery on '{REQUIRED_SKILL}': {', '.join(below_threshold)}")
        return 1

    print(f"\nGate PASSED: all learners at or above {MASTERY_THRESHOLD} mastery on '{REQUIRED_SKILL}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
