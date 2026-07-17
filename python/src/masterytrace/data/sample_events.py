"""
Bundled example event log for `masterytrace init`: 3 learners x 3 skills,
6-7 responses each, with a deterministic (seeded) but plausible "improving
over time" pattern per learner. Ported from src/data/sample-events.ts,
including its linear congruential generator, so the bundled sample data
follows the same generation algorithm as the npm package's (the two are
not required to be byte-identical, only algorithmically equivalent, since
each runtime's `Date`/timestamp formatting differs slightly).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List

from ..core.event_schema import ResponseEvent

_UINT32_MASK = 0xFFFFFFFF


def _make_lcg(seed: int) -> Callable[[], float]:
    """
    A small deterministic linear congruential generator, used only to keep
    the bundled sample data reproducible (no random.random()) while still
    looking like a real, slightly noisy response log rather than a
    hand-typed pattern.
    """
    state = seed & _UINT32_MASK

    def _next() -> float:
        nonlocal state
        state = (state * 1664525 + 1013904223) & _UINT32_MASK
        return state / _UINT32_MASK

    return _next


_LEARNERS = ["learner-ada", "learner-brook", "learner-cyrus"]
_SKILLS = ["fractions", "linear-equations", "reading-comprehension"]

# Roughly how likely each learner is to answer correctly on their Nth
# attempt at a skill (index 0 = first attempt), used only to shape the
# bundled sample into a plausible "learning over time" curve.
_LEARNING_CURVES: Dict[str, List[float]] = {
    "learner-ada": [0.3, 0.4, 0.55, 0.7, 0.8, 0.85, 0.9],
    "learner-brook": [0.2, 0.25, 0.3, 0.45, 0.55, 0.65, 0.75],
    "learner-cyrus": [0.5, 0.65, 0.75, 0.85, 0.9, 0.92, 0.95],
}
_DEFAULT_CURVE = [0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9]


def _build_sample_events() -> List[ResponseEvent]:
    rand = _make_lcg(42)
    events: List[ResponseEvent] = []
    start_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=timezone.utc)
    day_offset = 0

    for skill_id in _SKILLS:
        for learner_id in _LEARNERS:
            curve = _LEARNING_CURVES.get(learner_id, _DEFAULT_CURVE)
            attempts = 6 + int(rand() * 2)  # 6 or 7 attempts per learner+skill
            for attempt in range(attempts):
                p_correct = curve[min(attempt, len(curve) - 1)]
                correct = rand() < p_correct
                timestamp = start_date + timedelta(days=day_offset, hours=attempt)
                events.append(
                    ResponseEvent(
                        learner_id=learner_id,
                        skill_id=skill_id,
                        correct=correct,
                        timestamp=timestamp.isoformat().replace("+00:00", "Z"),
                    )
                )
            day_offset += 1

    return events


SAMPLE_EVENTS: List[ResponseEvent] = _build_sample_events()
