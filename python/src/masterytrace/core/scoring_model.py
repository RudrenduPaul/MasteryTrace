"""
The unified report/model shapes both BKT and IRT produce, letting the
engine and CLI treat either psychometric model interchangeably. Ported
from src/core/scoring-model.ts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, TypeVar


@dataclass
class MasterySkillEntry:
    """
    A single per-skill mastery estimate for one learner, as produced by a
    scoring model. `metric` names what `value` means so a report consumer
    (or the CLI's table renderer) can label it correctly without knowing
    which model produced it: 'posterior_mastery_probability' (BKT) or
    'ability_theta' (IRT).
    """

    skill_id: str
    metric: str
    value: float
    response_count: int
    details: Optional[Dict[str, Any]] = None


@dataclass
class MasteryLearnerEntry:
    learner_id: str
    skills: List[MasterySkillEntry] = field(default_factory=list)


@dataclass
class MasteryReport:
    """
    The unified shape every ScoringModel.score() returns, regardless of
    which psychometric model produced it.
    """

    model: str
    generated_at: str
    learners: List[MasteryLearnerEntry] = field(default_factory=list)
    meta: Optional[Dict[str, Any]] = None


@dataclass
class FittedModel:
    """Opaque fitted-model artifact produced by ScoringModel.fit()."""

    model_name: str


F = TypeVar("F", bound=FittedModel)


class ScoringModel(Protocol[F]):
    """
    Common interface both BKT and IRT implement, so an engine or CLI can
    fit and score either model (or both) through the same code path.
    """

    name: str

    def fit(self, events: List[Any]) -> F: ...

    def score(self, fitted_model: F) -> MasteryReport: ...
