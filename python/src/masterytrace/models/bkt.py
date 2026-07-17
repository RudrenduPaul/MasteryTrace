"""
Bayesian Knowledge Tracing (BKT) scoring model. Faithful port of
src/models/bkt.ts -- same forward-recursion formulas, same coarse grid
search fitting routine, same default parameters and grid values. No
numerical library is used: BKT's per-response update is four scalar
arithmetic operations, exactly what the TypeScript original does with
plain numbers, so a numpy/scipy dependency would buy nothing here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..core.event_schema import ResponseEvent
from ..core.scoring_model import FittedModel, MasteryLearnerEntry, MasteryReport, MasterySkillEntry


@dataclass(frozen=True)
class BktParams:
    """
    pInit: prior probability the learner already knows the skill before
      any evidence.
    pTransit: probability of learning the skill on any given opportunity
      (per response).
    pSlip: probability of an incorrect response despite knowing the skill.
    pGuess: probability of a correct response despite not knowing the
      skill.
    """

    p_init: float
    p_transit: float
    p_slip: float
    p_guess: float


BKT_DEFAULT_PARAMS = BktParams(p_init=0.4, p_transit=0.3, p_slip=0.1, p_guess=0.2)


@dataclass
class BktConfig:
    default_params: Optional[Dict[str, float]] = None
    skill_params: Optional[Dict[str, Dict[str, float]]] = None
    fit: bool = False


@dataclass
class BktSkillResult:
    learner_id: str
    skill_id: str
    posterior_history: List[float]
    final_mastery: float
    response_count: int


@dataclass
class BktFittedModel(FittedModel):
    params: Dict[str, BktParams] = field(default_factory=dict)
    results: List[BktSkillResult] = field(default_factory=list)


def _group_by_learner_skill(
    events: List[ResponseEvent],
) -> Dict[str, Dict[str, List[ResponseEvent]]]:
    """
    Groups events by learnerId, then by skillId, sorting each learner+
    skill's events into chronological order. Nested dicts (rather than a
    joined string key) are used deliberately: learnerId and skillId are
    arbitrary user-supplied strings with no character restrictions, so any
    chosen separator could in principle also appear inside an id and
    corrupt the grouping. Nesting sidesteps that entirely -- same
    rationale, same fix, as the TypeScript original.
    """
    groups: Dict[str, Dict[str, List[ResponseEvent]]] = {}
    for event in events:
        by_skill = groups.setdefault(event.learner_id, {})
        by_skill.setdefault(event.skill_id, []).append(event)

    for by_skill in groups.values():
        for skill_id, event_list in by_skill.items():
            by_skill[skill_id] = sorted(event_list, key=lambda e: _parse_timestamp(e.timestamp))
    return groups


def _parse_timestamp(value: str) -> datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(candidate)


def _group_by_skill(events: List[ResponseEvent]) -> Dict[str, List[ResponseEvent]]:
    groups: Dict[str, List[ResponseEvent]] = {}
    for event in events:
        groups.setdefault(event.skill_id, []).append(event)
    return groups


@dataclass
class _ForwardRecursionDetail:
    posterior_history: List[float]
    predicted_probabilities: List[float]


def _run_forward_recursion_detailed(responses: List[bool], params: BktParams) -> _ForwardRecursionDetail:
    """
    Runs the BKT forward recursion for one chronologically ordered
    sequence of responses, given fixed parameters:

      P(L_0) = pInit
      after correct:   P(L_t|obs) = P(L_t)*(1-pSlip) / [P(L_t)*(1-pSlip) + (1-P(L_t))*pGuess]
      after incorrect: P(L_t|obs) = P(L_t)*pSlip     / [P(L_t)*pSlip     + (1-P(L_t))*(1-pGuess)]
      P(L_{t+1}) = P(L_t|obs) + (1 - P(L_t|obs)) * pTransit
    """
    prior_l = params.p_init
    posterior_history: List[float] = []
    predicted_probabilities: List[float] = []

    for correct in responses:
        predicted_probabilities.append(prior_l * (1 - params.p_slip) + (1 - prior_l) * params.p_guess)

        if correct:
            numerator = prior_l * (1 - params.p_slip)
            denominator = numerator + (1 - prior_l) * params.p_guess
            posterior = prior_l if denominator == 0 else numerator / denominator
        else:
            numerator = prior_l * params.p_slip
            denominator = numerator + (1 - prior_l) * (1 - params.p_guess)
            posterior = prior_l if denominator == 0 else numerator / denominator

        posterior_history.append(posterior)
        prior_l = posterior + (1 - posterior) * params.p_transit

    return _ForwardRecursionDetail(posterior_history=posterior_history, predicted_probabilities=predicted_probabilities)


def run_forward_recursion(responses: List[bool], params: BktParams) -> List[float]:
    """
    Runs the BKT forward recursion for one chronologically ordered
    sequence of responses and returns the posterior mastery probability
    P(L_t | obs) after each response. Exported directly (in addition to
    being used inside BktModel) so the recursion math can be
    unit-tested against a hand-computed worked example.
    """
    return _run_forward_recursion_detailed(responses, params).posterior_history


_GRID_PROBABILITY = [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]
# pSlip/pGuess are kept below 0.5 by construction: a "skill" parameter
# above that would mean the mechanism is more often wrong than right,
# which is not a meaningful slip/guess rate in practice.
_GRID_LOW_PROBABILITY = [0.02, 0.1, 0.2, 0.3, 0.4]


def fit_skill_params_by_grid_search(sequences: List[List[bool]]) -> BktParams:
    """
    Coarse grid search over (pInit, pTransit, pSlip, pGuess) for one
    skill's pooled response sequences, minimizing total squared error
    between the model's pre-update predicted-correct probability and the
    actual observed outcome at each step. This is intentionally a simple,
    dependency-free fitting routine (not a full EM/Baum-Welch
    implementation) that is good enough to noticeably improve on the
    textbook defaults for a given dataset -- same trade-off the
    TypeScript original documents and makes.
    """
    best = BKT_DEFAULT_PARAMS
    best_error = float("inf")

    for p_init in _GRID_PROBABILITY:
        for p_transit in _GRID_PROBABILITY:
            for p_slip in _GRID_LOW_PROBABILITY:
                for p_guess in _GRID_LOW_PROBABILITY:
                    params = BktParams(p_init=p_init, p_transit=p_transit, p_slip=p_slip, p_guess=p_guess)
                    error = 0.0
                    for sequence in sequences:
                        detail = _run_forward_recursion_detailed(sequence, params)
                        for i, correct in enumerate(sequence):
                            predicted = detail.predicted_probabilities[i] if i < len(detail.predicted_probabilities) else 0.0
                            actual = 1.0 if correct else 0.0
                            error += (predicted - actual) ** 2
                    if error < best_error:
                        best_error = error
                        best = params

    return best


class BktModel:
    """
    Bayesian Knowledge Tracing scoring model. Implements the ScoringModel
    protocol so it is interchangeable with IRT from the engine's point of
    view.
    """

    name = "bkt"

    def __init__(self, config: Optional[BktConfig] = None) -> None:
        self.config = config or BktConfig()

    def fit(self, events: List[ResponseEvent]) -> BktFittedModel:
        by_skill = _group_by_skill(events)
        by_learner_skill = _group_by_learner_skill(events)

        params: Dict[str, BktParams] = {}
        for skill_id in by_skill:
            override = (self.config.skill_params or {}).get(skill_id)
            if override:
                merged = {
                    "p_init": BKT_DEFAULT_PARAMS.p_init,
                    "p_transit": BKT_DEFAULT_PARAMS.p_transit,
                    "p_slip": BKT_DEFAULT_PARAMS.p_slip,
                    "p_guess": BKT_DEFAULT_PARAMS.p_guess,
                }
                merged.update(self.config.default_params or {})
                merged.update(override)
                params[skill_id] = BktParams(**merged)
            elif self.config.fit:
                sequences: List[List[bool]] = []
                for by_skill_for_learner in by_learner_skill.values():
                    event_list = by_skill_for_learner.get(skill_id)
                    if event_list:
                        sequences.append([e.correct for e in event_list])
                params[skill_id] = fit_skill_params_by_grid_search(sequences)
            else:
                merged = {
                    "p_init": BKT_DEFAULT_PARAMS.p_init,
                    "p_transit": BKT_DEFAULT_PARAMS.p_transit,
                    "p_slip": BKT_DEFAULT_PARAMS.p_slip,
                    "p_guess": BKT_DEFAULT_PARAMS.p_guess,
                }
                merged.update(self.config.default_params or {})
                params[skill_id] = BktParams(**merged)

        results: List[BktSkillResult] = []
        for learner_id, by_skill_for_learner in by_learner_skill.items():
            for skill_id, event_list in by_skill_for_learner.items():
                skill_params = params.get(skill_id, BKT_DEFAULT_PARAMS)
                posterior_history = run_forward_recursion([e.correct for e in event_list], skill_params)
                results.append(
                    BktSkillResult(
                        learner_id=learner_id,
                        skill_id=skill_id,
                        posterior_history=posterior_history,
                        final_mastery=posterior_history[-1] if posterior_history else skill_params.p_init,
                        response_count=len(event_list),
                    )
                )

        return BktFittedModel(model_name="bkt", params=params, results=results)

    def score(self, fitted_model: BktFittedModel) -> MasteryReport:
        learner_map: Dict[str, MasteryLearnerEntry] = {}

        for result in fitted_model.results:
            entry = learner_map.get(result.learner_id)
            if entry is None:
                entry = MasteryLearnerEntry(learner_id=result.learner_id, skills=[])
                learner_map[result.learner_id] = entry
            entry.skills.append(
                MasterySkillEntry(
                    skill_id=result.skill_id,
                    metric="posterior_mastery_probability",
                    value=result.final_mastery,
                    response_count=result.response_count,
                    details={
                        "posterior_history": result.posterior_history,
                        "params": fitted_model.params.get(result.skill_id),
                    },
                )
            )

        return MasteryReport(
            model="bkt",
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            learners=list(learner_map.values()),
            meta={"params": fitted_model.params},
        )
