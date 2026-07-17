"""
Item Response Theory (2-parameter logistic) scoring model. Faithful port
of src/models/irt.ts -- same joint maximum-likelihood estimation via batch
gradient ascent, same L2 regularization, same per-iteration gauge-fixing
(re-centering theta to mean 0 / std 1). The TypeScript original hand-rolls
this with a `Float64Array` and plain loops rather than calling into an
external optimizer (there is no scipy.optimize equivalent in play here to
port to); this port mirrors that with plain Python lists so the algorithm
stays line-for-line auditable against the original rather than being
rewritten in vectorized numpy, which could silently change rounding/
iteration order.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..core.event_schema import ResponseEvent
from ..core.scoring_model import FittedModel, MasteryLearnerEntry, MasteryReport, MasterySkillEntry


@dataclass(frozen=True)
class IrtItemParams:
    skill_id: str
    a: float
    """Discrimination. Higher means the item separates high/low ability learners more sharply."""
    b: float
    """Difficulty, on the same scale as theta. Higher means a harder skill."""


@dataclass(frozen=True)
class IrtLearnerResult:
    learner_id: str
    theta: float
    """Estimated ability."""
    response_count: int


@dataclass
class IrtConfig:
    iterations: int = 500
    """Number of gradient-ascent iterations to run."""
    learning_rate: float = 0.5
    """Learning rate for the gradient-ascent updates."""
    regularization: float = 0.01
    """
    L2 regularization strength pulling theta and b toward 0 and a toward 1.
    This is what keeps the joint MLE finite for learners/items with a
    perfect (all-correct or all-incorrect) response record, where the
    unregularized likelihood is maximized at +/-infinity.
    """


@dataclass
class IrtResponseTriple:
    learner_id: str
    skill_id: str
    correct: bool


@dataclass
class IrtFittedModel(FittedModel):
    items: List[IrtItemParams] = field(default_factory=list)
    learners: List[IrtLearnerResult] = field(default_factory=list)
    responses: List[IrtResponseTriple] = field(default_factory=list)


def _sigmoid(z: float) -> float:
    """Numerically stable logistic sigmoid."""
    if z >= 0:
        e = math.exp(-z)
        return 1.0 / (1.0 + e)
    e = math.exp(z)
    return e / (1.0 + e)


def probability_correct(theta: float, a: float, b: float) -> float:
    """P(correct) under the 2-parameter logistic model."""
    return _sigmoid(a * (theta - b))


@dataclass
class _JmleResult:
    theta: Dict[str, float]
    a: Dict[str, float]
    b: Dict[str, float]


def _fit_jmle(
    learner_ids: List[str],
    item_ids: List[str],
    responses: List[tuple],
    config: IrtConfig,
) -> _JmleResult:
    """
    Joint maximum-likelihood estimation for the 2PL IRT model via batch
    gradient ascent on the log-likelihood, with a small L2 prior
    (regularizing theta/b toward 0 and a toward 1) that keeps estimates
    finite for learners or skills with an all-correct or all-incorrect
    record.

    The 2PL model is only identified up to an additive shift and
    multiplicative scale of theta (z = a*(theta-b) is unchanged by
    shifting theta and b by the same constant, or by scaling theta/b by s
    while dividing a by s). To pin down a single solution, after every
    iteration the theta distribution is re-centered to mean 0 and
    re-scaled to standard deviation 1, applying the matching inverse
    transform to b and a so every predicted probability is left exactly
    unchanged. This is the standard way JMLE implementations fix the
    person-parameter scale.
    """
    n_learners = len(learner_ids)
    n_items = len(item_ids)

    theta = [0.0] * n_learners
    a = [1.0] * n_items
    b = [0.0] * n_items

    iterations = config.iterations
    learning_rate = config.learning_rate
    regularization = config.regularization

    # Gradients are averaged per learner/item (not summed) so the
    # effective step size does not depend on how many responses a learner
    # or item happens to have -- with raw summed gradients, a learner with
    # hundreds of responses would take enormous steps relative to one with
    # a handful, making a single learning_rate unstable across datasets of
    # different size.
    response_count_by_learner = [0.0] * n_learners
    response_count_by_item = [0.0] * n_items
    for learner_index, item_index, _correct in responses:
        response_count_by_learner[learner_index] += 1
        response_count_by_item[item_index] += 1

    for _ in range(iterations):
        grad_theta = [0.0] * n_learners
        grad_a = [0.0] * n_items
        grad_b = [0.0] * n_items

        for learner_index, item_index, correct in responses:
            th = theta[learner_index]
            ai = a[item_index]
            bi = b[item_index]
            p = _sigmoid(ai * (th - bi))
            residual = (1.0 if correct else 0.0) - p  # dLogLik/dz

            grad_theta[learner_index] += ai * residual
            grad_b[item_index] -= ai * residual
            grad_a[item_index] += (th - bi) * residual

        for i in range(n_learners):
            count = response_count_by_learner[i] or 1.0
            grad = grad_theta[i] / count - regularization * theta[i]
            theta[i] = theta[i] + learning_rate * grad

        for j in range(n_items):
            count = response_count_by_item[j] or 1.0
            grad_bj = grad_b[j] / count - regularization * b[j]
            b[j] = b[j] + learning_rate * grad_bj
            grad_aj = grad_a[j] / count - regularization * (a[j] - 1.0)
            next_a = a[j] + learning_rate * grad_aj
            # Discrimination must stay positive; floor it well away from zero.
            a[j] = max(next_a, 0.05)

        # Fix the theta location/scale gauge freedom (see docstring above).
        mean = sum(theta) / n_learners if n_learners else 0.0
        variance = sum((t - mean) ** 2 for t in theta) / n_learners if n_learners else 0.0
        std = math.sqrt(variance)
        if std > 1e-6:
            theta = [(t - mean) / std for t in theta]
            for j in range(n_items):
                b[j] = (b[j] - mean) / std
                a[j] = a[j] * std

    theta_map = {learner_ids[i]: theta[i] for i in range(n_learners)}
    a_map = {item_ids[j]: a[j] for j in range(n_items)}
    b_map = {item_ids[j]: b[j] for j in range(n_items)}
    return _JmleResult(theta=theta_map, a=a_map, b=b_map)


class IrtModel:
    """
    Item Response Theory (2-parameter logistic) scoring model. Treats
    each distinct skillId as one "item": every response event for a skill
    is an observation of that item, and the model jointly estimates one
    ability (theta) per learner and one (discrimination, difficulty) pair
    per skill. Implements the ScoringModel protocol so it is
    interchangeable with BKT.
    """

    name = "irt"

    def __init__(self, config: Optional[IrtConfig] = None) -> None:
        self.config = config or IrtConfig()

    def fit(self, events: List[ResponseEvent]) -> IrtFittedModel:
        learner_ids: List[str] = []
        seen_learners = set()
        item_ids: List[str] = []
        seen_items = set()
        for e in events:
            if e.learner_id not in seen_learners:
                seen_learners.add(e.learner_id)
                learner_ids.append(e.learner_id)
            if e.skill_id not in seen_items:
                seen_items.add(e.skill_id)
                item_ids.append(e.skill_id)

        learner_index = {lid: i for i, lid in enumerate(learner_ids)}
        item_index = {sid: i for i, sid in enumerate(item_ids)}

        responses = [(learner_index[e.learner_id], item_index[e.skill_id], e.correct) for e in events]

        response_counts: Dict[str, int] = {}
        for e in events:
            response_counts[e.learner_id] = response_counts.get(e.learner_id, 0) + 1

        if not learner_ids or not item_ids:
            return IrtFittedModel(model_name="irt", items=[], learners=[], responses=[])

        fitted = _fit_jmle(learner_ids, item_ids, responses, self.config)

        items = [IrtItemParams(skill_id=sid, a=fitted.a.get(sid, 1.0), b=fitted.b.get(sid, 0.0)) for sid in item_ids]
        learners = [
            IrtLearnerResult(
                learner_id=lid,
                theta=fitted.theta.get(lid, 0.0),
                response_count=response_counts.get(lid, 0),
            )
            for lid in learner_ids
        ]

        return IrtFittedModel(
            model_name="irt",
            items=items,
            learners=learners,
            responses=[IrtResponseTriple(learner_id=e.learner_id, skill_id=e.skill_id, correct=e.correct) for e in events],
        )

    def score(self, fitted_model: IrtFittedModel) -> MasteryReport:
        items_by_skill = {item.skill_id: item for item in fitted_model.items}
        skill_ids_by_learner: Dict[str, List[str]] = {}
        seen_pairs = set()
        response_count_by_learner_skill: Dict[str, int] = {}

        for response in fitted_model.responses:
            key = f"{response.learner_id}::{response.skill_id}"
            pair_key = (response.learner_id, response.skill_id)
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                skill_ids_by_learner.setdefault(response.learner_id, []).append(response.skill_id)
            response_count_by_learner_skill[key] = response_count_by_learner_skill.get(key, 0) + 1

        learners: List[MasteryLearnerEntry] = []
        for learner_result in fitted_model.learners:
            skill_ids = skill_ids_by_learner.get(learner_result.learner_id, [])
            skills: List[MasterySkillEntry] = []
            for skill_id in skill_ids:
                item = items_by_skill.get(skill_id)
                a = item.a if item else 1.0
                b = item.b if item else 0.0
                key = f"{learner_result.learner_id}::{skill_id}"
                skills.append(
                    MasterySkillEntry(
                        skill_id=skill_id,
                        metric="ability_theta",
                        value=learner_result.theta,
                        response_count=response_count_by_learner_skill.get(key, 0),
                        details={
                            "item_discrimination": a,
                            "item_difficulty": b,
                            "predicted_probability_correct": probability_correct(learner_result.theta, a, b),
                        },
                    )
                )
            learners.append(MasteryLearnerEntry(learner_id=learner_result.learner_id, skills=skills))

        return MasteryReport(
            model="irt",
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            learners=learners,
            meta={"items": fitted_model.items},
        )
