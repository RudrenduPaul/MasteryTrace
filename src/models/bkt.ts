import type { ResponseEvent } from '../core/event-schema.js';
import type {
  FittedModel,
  MasteryLearnerEntry,
  MasteryReport,
  ScoringModel,
} from '../core/scoring-model.js';

export interface BktParams {
  /** Prior probability the learner already knows the skill before any evidence. */
  pInit: number;
  /** Probability of learning the skill on any given opportunity (per response). */
  pTransit: number;
  /** Probability of an incorrect response despite knowing the skill. */
  pSlip: number;
  /** Probability of a correct response despite not knowing the skill. */
  pGuess: number;
}

/** Standard textbook default BKT parameters. */
export const BKT_DEFAULT_PARAMS: BktParams = {
  pInit: 0.4,
  pTransit: 0.3,
  pSlip: 0.1,
  pGuess: 0.2,
};

export interface BktConfig {
  /** Overrides applied on top of BKT_DEFAULT_PARAMS for every skill. */
  defaultParams?: Partial<BktParams>;
  /** Per-skill parameter overrides, keyed by skillId. Wins over `fit`. */
  skillParams?: Record<string, Partial<BktParams>>;
  /**
   * When true, any skill without an explicit `skillParams` override has its
   * parameters fit from the observed data via grid search instead of using
   * fixed defaults.
   */
  fit?: boolean;
}

interface BktSkillResult {
  learnerId: string;
  skillId: string;
  /** P(L_t | observation) after each response, in chronological order. */
  posteriorHistory: number[];
  /** Mastery estimate given all evidence observed so far (last posterior). */
  finalMastery: number;
  responseCount: number;
}

export interface BktFittedModel extends FittedModel {
  modelName: 'bkt';
  params: Record<string, BktParams>;
  results: BktSkillResult[];
}

// A control character that will never legitimately appear in a learnerId or
// skillId, used to join/split the composite grouping key safely.
const LEARNER_SKILL_SEP = '\u0000';

function groupByLearnerSkill(events: ResponseEvent[]): Map<string, ResponseEvent[]> {
  const groups = new Map<string, ResponseEvent[]>();
  for (const event of events) {
    const key = `${event.learnerId}${LEARNER_SKILL_SEP}${event.skillId}`;
    const list = groups.get(key);
    if (list) {
      list.push(event);
    } else {
      groups.set(key, [event]);
    }
  }
  for (const list of groups.values()) {
    list.sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  }
  return groups;
}

function groupBySkill(events: ResponseEvent[]): Map<string, ResponseEvent[]> {
  const groups = new Map<string, ResponseEvent[]>();
  for (const event of events) {
    const list = groups.get(event.skillId);
    if (list) {
      list.push(event);
    } else {
      groups.set(event.skillId, [event]);
    }
  }
  return groups;
}

interface ForwardRecursionDetail {
  /** P(L_t | observation) after each response. */
  posteriorHistory: number[];
  /** Predicted P(correct) at each step, computed from the pre-update prior. */
  predictedProbabilities: number[];
}

/**
 * Runs the BKT forward recursion for one chronologically ordered sequence
 * of responses, given fixed parameters:
 *
 *   P(L_0) = pInit
 *   after correct:   P(L_t|obs) = P(L_t)*(1-pSlip) / [P(L_t)*(1-pSlip) + (1-P(L_t))*pGuess]
 *   after incorrect: P(L_t|obs) = P(L_t)*pSlip     / [P(L_t)*pSlip     + (1-P(L_t))*(1-pGuess)]
 *   P(L_{t+1}) = P(L_t|obs) + (1 - P(L_t|obs)) * pTransit
 *
 * Also records, for each step, the predicted P(correct) computed from the
 * pre-update prior (used by the grid-search fit routine to score candidate
 * parameters against observed outcomes).
 */
function runForwardRecursionDetailed(
  responses: boolean[],
  params: BktParams,
): ForwardRecursionDetail {
  const { pInit, pTransit, pSlip, pGuess } = params;
  let priorL = pInit;
  const posteriorHistory: number[] = [];
  const predictedProbabilities: number[] = [];

  for (const correct of responses) {
    predictedProbabilities.push(priorL * (1 - pSlip) + (1 - priorL) * pGuess);

    let posterior: number;
    if (correct) {
      const numerator = priorL * (1 - pSlip);
      const denominator = numerator + (1 - priorL) * pGuess;
      posterior = denominator === 0 ? priorL : numerator / denominator;
    } else {
      const numerator = priorL * pSlip;
      const denominator = numerator + (1 - priorL) * (1 - pGuess);
      posterior = denominator === 0 ? priorL : numerator / denominator;
    }
    posteriorHistory.push(posterior);
    priorL = posterior + (1 - posterior) * pTransit;
  }

  return { posteriorHistory, predictedProbabilities };
}

/**
 * Runs the BKT forward recursion for one chronologically ordered sequence
 * of responses and returns the posterior mastery probability P(L_t | obs)
 * after each response. Exported directly (in addition to being used inside
 * BktModel) so the recursion math can be unit-tested against a hand-computed
 * worked example.
 */
export function runForwardRecursion(responses: boolean[], params: BktParams): number[] {
  return runForwardRecursionDetailed(responses, params).posteriorHistory;
}

const GRID_PROBABILITY = [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95];
// pSlip/pGuess are kept below 0.5 by construction: a "skill" parameter above
// that would mean the mechanism is more often wrong than right, which is not
// a meaningful slip/guess rate in practice.
const GRID_LOW_PROBABILITY = [0.02, 0.1, 0.2, 0.3, 0.4];

/**
 * Coarse grid search over (pInit, pTransit, pSlip, pGuess) for one skill's
 * pooled response sequences, minimizing total squared error between the
 * model's pre-update predicted-correct probability and the actual observed
 * outcome at each step. This is intentionally a simple, dependency-free
 * fitting routine (not a full EM/Baum-Welch implementation) that is good
 * enough to noticeably improve on the textbook defaults for a given dataset.
 */
export function fitSkillParamsByGridSearch(sequences: boolean[][]): BktParams {
  let best: BktParams = { ...BKT_DEFAULT_PARAMS };
  let bestError = Infinity;

  for (const pInit of GRID_PROBABILITY) {
    for (const pTransit of GRID_PROBABILITY) {
      for (const pSlip of GRID_LOW_PROBABILITY) {
        for (const pGuess of GRID_LOW_PROBABILITY) {
          const params: BktParams = { pInit, pTransit, pSlip, pGuess };
          let error = 0;
          for (const sequence of sequences) {
            const { predictedProbabilities } = runForwardRecursionDetailed(sequence, params);
            for (let i = 0; i < sequence.length; i += 1) {
              const predicted = predictedProbabilities[i] ?? 0;
              const actual = sequence[i] ? 1 : 0;
              error += (predicted - actual) ** 2;
            }
          }
          if (error < bestError) {
            bestError = error;
            best = params;
          }
        }
      }
    }
  }

  return best;
}

/**
 * Bayesian Knowledge Tracing scoring model. Implements the ScoringModel
 * interface so it is interchangeable with IRT from the engine's point of
 * view.
 */
export class BktModel implements ScoringModel<BktFittedModel> {
  public readonly name = 'bkt';

  constructor(private readonly config: BktConfig = {}) {}

  fit(events: ResponseEvent[]): BktFittedModel {
    const bySkill = groupBySkill(events);
    const byLearnerSkill = groupByLearnerSkill(events);

    const params: Record<string, BktParams> = {};
    for (const skillId of bySkill.keys()) {
      const override = this.config.skillParams?.[skillId];
      if (override) {
        params[skillId] = { ...BKT_DEFAULT_PARAMS, ...this.config.defaultParams, ...override };
      } else if (this.config.fit) {
        const sequences: boolean[][] = [];
        const suffix = `${LEARNER_SKILL_SEP}${skillId}`;
        for (const [key, list] of byLearnerSkill.entries()) {
          if (key.endsWith(suffix)) {
            sequences.push(list.map((e) => e.correct));
          }
        }
        params[skillId] = fitSkillParamsByGridSearch(sequences);
      } else {
        params[skillId] = { ...BKT_DEFAULT_PARAMS, ...this.config.defaultParams };
      }
    }

    const results: BktSkillResult[] = [];
    for (const [key, list] of byLearnerSkill.entries()) {
      const [learnerId, skillId] = key.split(LEARNER_SKILL_SEP) as [string, string];
      const skillParams = params[skillId] ?? BKT_DEFAULT_PARAMS;
      const posteriorHistory = runForwardRecursion(
        list.map((e) => e.correct),
        skillParams,
      );
      results.push({
        learnerId,
        skillId,
        posteriorHistory,
        finalMastery: posteriorHistory[posteriorHistory.length - 1] ?? skillParams.pInit,
        responseCount: list.length,
      });
    }

    return { modelName: 'bkt', params, results };
  }

  score(fittedModel: BktFittedModel): MasteryReport {
    const learnerMap = new Map<string, MasteryLearnerEntry>();

    for (const result of fittedModel.results) {
      let entry = learnerMap.get(result.learnerId);
      if (!entry) {
        entry = { learnerId: result.learnerId, skills: [] };
        learnerMap.set(result.learnerId, entry);
      }
      entry.skills.push({
        skillId: result.skillId,
        metric: 'posterior_mastery_probability',
        value: result.finalMastery,
        responseCount: result.responseCount,
        details: {
          posteriorHistory: result.posteriorHistory,
          params: fittedModel.params[result.skillId],
        },
      });
    }

    return {
      model: 'bkt',
      generatedAt: new Date().toISOString(),
      learners: [...learnerMap.values()],
      meta: { params: fittedModel.params },
    };
  }
}
