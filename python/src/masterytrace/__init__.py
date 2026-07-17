"""
MasteryTrace: Mastery Measurement API and CLI. Fits Bayesian Knowledge
Tracing (BKT) and 2-parameter logistic Item Response Theory (IRT) models
to learner response logs and reports per-learner, per-skill mastery
estimates.

Re-exports mirror src/index.ts's re-export surface (core/*, models/*,
adapters/*) so `from masterytrace import ...` covers the same public API
as the npm package's `from 'masterytrace-cli'`.
"""
from .adapters.generic_adapter import GenericAdapter, generic_adapter, parse_csv
from .core.config import DEFAULT_CONFIG, MasteryTraceConfig, load_config
from .core.engine import EngineConfig, EngineResult, ModelSelector, run_scoring
from .core.event_schema import EventValidationError, ResponseEvent, parse_response_events
from .core.scoring_model import FittedModel, MasteryLearnerEntry, MasteryReport, MasterySkillEntry, ScoringModel
from .models.bkt import (
    BKT_DEFAULT_PARAMS,
    BktConfig,
    BktFittedModel,
    BktModel,
    BktParams,
    fit_skill_params_by_grid_search,
    run_forward_recursion,
)
from .models.irt import (
    IrtConfig,
    IrtFittedModel,
    IrtItemParams,
    IrtLearnerResult,
    IrtModel,
    probability_correct,
)

__version__ = "0.1.0"

__all__ = [
    "GenericAdapter",
    "generic_adapter",
    "parse_csv",
    "DEFAULT_CONFIG",
    "MasteryTraceConfig",
    "load_config",
    "EngineConfig",
    "EngineResult",
    "ModelSelector",
    "run_scoring",
    "EventValidationError",
    "ResponseEvent",
    "parse_response_events",
    "FittedModel",
    "MasteryLearnerEntry",
    "MasteryReport",
    "MasterySkillEntry",
    "ScoringModel",
    "BKT_DEFAULT_PARAMS",
    "BktConfig",
    "BktFittedModel",
    "BktModel",
    "BktParams",
    "fit_skill_params_by_grid_search",
    "run_forward_recursion",
    "IrtConfig",
    "IrtFittedModel",
    "IrtItemParams",
    "IrtLearnerResult",
    "IrtModel",
    "probability_correct",
]
