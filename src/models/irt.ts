import type { ResponseEvent } from '../core/event-schema.js';
import type {
  FittedModel,
  MasteryLearnerEntry,
  MasteryReport,
  ScoringModel,
} from '../core/scoring-model.js';

export interface IrtItemParams {
  skillId: string;
  /** Discrimination. Higher means the item separates high/low ability learners more sharply. */
  a: number;
  /** Difficulty, on the same scale as theta. Higher means a harder skill. */
  b: number;
}

export interface IrtLearnerResult {
  learnerId: string;
  /** Estimated ability. */
  theta: number;
  responseCount: number;
}

export interface IrtConfig {
  /** Number of gradient-ascent iterations to run. */
  iterations?: number;
  /** Learning rate for the gradient-ascent updates. */
  learningRate?: number;
  /**
   * L2 regularization strength pulling theta and b toward 0 and a toward 1.
   * This is what keeps the joint MLE finite for learners/items with a
   * perfect (all-correct or all-incorrect) response record, where the
   * unregularized likelihood is maximized at +/-infinity.
   */
  regularization?: number;
}

const DEFAULT_IRT_CONFIG: Required<IrtConfig> = {
  iterations: 500,
  learningRate: 0.5,
  regularization: 0.01,
};

export interface IrtFittedModel extends FittedModel {
  modelName: 'irt';
  items: IrtItemParams[];
  learners: IrtLearnerResult[];
  /** Raw (learner, item, correct) triples the fit converged against, for score() to attach predictions. */
  responses: { learnerId: string; skillId: string; correct: boolean }[];
}

/** Numerically stable logistic sigmoid. */
function sigmoid(z: number): number {
  if (z >= 0) {
    const e = Math.exp(-z);
    return 1 / (1 + e);
  }
  const e = Math.exp(z);
  return e / (1 + e);
}

/** P(correct) under the 2-parameter logistic model. */
export function probabilityCorrect(theta: number, a: number, b: number): number {
  return sigmoid(a * (theta - b));
}

interface JmleResult {
  theta: Map<string, number>;
  a: Map<string, number>;
  b: Map<string, number>;
}

/**
 * Joint maximum-likelihood estimation for the 2PL IRT model via batch
 * gradient ascent on the log-likelihood, with a small L2 prior (regularizing
 * theta/b toward 0 and a toward 1) that keeps estimates finite for learners
 * or skills with an all-correct or all-incorrect record.
 *
 * The 2PL model is only identified up to an additive shift and multiplicative
 * scale of theta (z = a*(theta-b) is unchanged by shifting theta and b by the
 * same constant, or by scaling theta/b by s while dividing a by s). To pin
 * down a single solution, after every iteration the theta distribution is
 * re-centered to mean 0 and re-scaled to standard deviation 1, applying the
 * matching inverse transform to b and a so every predicted probability is
 * left exactly unchanged. This is the standard way JMLE implementations fix
 * the person-parameter scale.
 */
function fitJmle(
  learnerIds: string[],
  itemIds: string[],
  responses: { learnerIndex: number; itemIndex: number; correct: boolean }[],
  config: Required<IrtConfig>,
): JmleResult {
  const theta = new Float64Array(learnerIds.length).fill(0);
  const a = new Float64Array(itemIds.length).fill(1);
  const b = new Float64Array(itemIds.length).fill(0);

  const { iterations, learningRate, regularization } = config;

  // Gradients are averaged per learner/item (not summed) so the effective
  // step size does not depend on how many responses a learner or item
  // happens to have -- with raw summed gradients, a learner with hundreds
  // of responses would take enormous steps relative to one with a handful,
  // making a single learningRate unstable across datasets of different size.
  const responseCountByLearner = new Float64Array(learnerIds.length);
  const responseCountByItem = new Float64Array(itemIds.length);
  for (const { learnerIndex, itemIndex } of responses) {
    responseCountByLearner[learnerIndex] = (responseCountByLearner[learnerIndex] ?? 0) + 1;
    responseCountByItem[itemIndex] = (responseCountByItem[itemIndex] ?? 0) + 1;
  }

  for (let iter = 0; iter < iterations; iter += 1) {
    const gradTheta = new Float64Array(learnerIds.length);
    const gradA = new Float64Array(itemIds.length);
    const gradB = new Float64Array(itemIds.length);

    for (const { learnerIndex, itemIndex, correct } of responses) {
      const th = theta[learnerIndex] ?? 0;
      const ai = a[itemIndex] ?? 1;
      const bi = b[itemIndex] ?? 0;
      const p = sigmoid(ai * (th - bi));
      const residual = (correct ? 1 : 0) - p; // dLogLik/dz

      gradTheta[learnerIndex] = (gradTheta[learnerIndex] ?? 0) + ai * residual;
      gradB[itemIndex] = (gradB[itemIndex] ?? 0) - ai * residual;
      gradA[itemIndex] = (gradA[itemIndex] ?? 0) + (th - bi) * residual;
    }

    for (let i = 0; i < learnerIds.length; i += 1) {
      const count = responseCountByLearner[i] || 1;
      const grad = (gradTheta[i] ?? 0) / count - regularization * (theta[i] ?? 0);
      theta[i] = (theta[i] ?? 0) + learningRate * grad;
    }
    for (let j = 0; j < itemIds.length; j += 1) {
      const count = responseCountByItem[j] || 1;
      const gradBj = (gradB[j] ?? 0) / count - regularization * (b[j] ?? 0);
      b[j] = (b[j] ?? 0) + learningRate * gradBj;
      const gradAj = (gradA[j] ?? 0) / count - regularization * ((a[j] ?? 1) - 1);
      const nextA = (a[j] ?? 1) + learningRate * gradAj;
      // Discrimination must stay positive; floor it well away from zero.
      a[j] = Math.max(nextA, 0.05);
    }

    // Fix the theta location/scale gauge freedom (see docstring above).
    let mean = 0;
    for (let i = 0; i < theta.length; i += 1) mean += theta[i] ?? 0;
    mean /= theta.length || 1;
    let variance = 0;
    for (let i = 0; i < theta.length; i += 1) variance += ((theta[i] ?? 0) - mean) ** 2;
    variance /= theta.length || 1;
    const std = Math.sqrt(variance);
    if (std > 1e-6) {
      for (let i = 0; i < theta.length; i += 1) {
        theta[i] = ((theta[i] ?? 0) - mean) / std;
      }
      for (let j = 0; j < itemIds.length; j += 1) {
        b[j] = ((b[j] ?? 0) - mean) / std;
        a[j] = (a[j] ?? 1) * std;
      }
    }
  }

  const thetaMap = new Map<string, number>();
  learnerIds.forEach((id, i) => thetaMap.set(id, theta[i] ?? 0));
  const aMap = new Map<string, number>();
  const bMap = new Map<string, number>();
  itemIds.forEach((id, j) => {
    aMap.set(id, a[j] ?? 1);
    bMap.set(id, b[j] ?? 0);
  });

  return { theta: thetaMap, a: aMap, b: bMap };
}

/**
 * Item Response Theory (2-parameter logistic) scoring model. Treats each
 * distinct skillId as one "item": every response event for a skill is an
 * observation of that item, and the model jointly estimates one ability
 * (theta) per learner and one (discrimination, difficulty) pair per skill.
 * Implements the ScoringModel interface so it is interchangeable with BKT.
 */
export class IrtModel implements ScoringModel<IrtFittedModel> {
  public readonly name = 'irt';

  private readonly config: Required<IrtConfig>;

  constructor(config: IrtConfig = {}) {
    this.config = { ...DEFAULT_IRT_CONFIG, ...config };
  }

  fit(events: ResponseEvent[]): IrtFittedModel {
    const learnerIds = [...new Set(events.map((e) => e.learnerId))];
    const itemIds = [...new Set(events.map((e) => e.skillId))];
    const learnerIndex = new Map(learnerIds.map((id, i) => [id, i]));
    const itemIndex = new Map(itemIds.map((id, i) => [id, i]));

    const responses = events.map((e) => ({
      learnerIndex: learnerIndex.get(e.learnerId) ?? 0,
      itemIndex: itemIndex.get(e.skillId) ?? 0,
      correct: e.correct,
    }));

    const responseCounts = new Map<string, number>();
    for (const e of events) {
      responseCounts.set(e.learnerId, (responseCounts.get(e.learnerId) ?? 0) + 1);
    }

    if (learnerIds.length === 0 || itemIds.length === 0) {
      return {
        modelName: 'irt',
        items: [],
        learners: [],
        responses: [],
      };
    }

    const { theta, a, b } = fitJmle(learnerIds, itemIds, responses, this.config);

    const items: IrtItemParams[] = itemIds.map((skillId) => ({
      skillId,
      a: a.get(skillId) ?? 1,
      b: b.get(skillId) ?? 0,
    }));

    const learners: IrtLearnerResult[] = learnerIds.map((learnerId) => ({
      learnerId,
      theta: theta.get(learnerId) ?? 0,
      responseCount: responseCounts.get(learnerId) ?? 0,
    }));

    return {
      modelName: 'irt',
      items,
      learners,
      responses: events.map((e) => ({
        learnerId: e.learnerId,
        skillId: e.skillId,
        correct: e.correct,
      })),
    };
  }

  score(fittedModel: IrtFittedModel): MasteryReport {
    const itemsBySkill = new Map(fittedModel.items.map((item) => [item.skillId, item]));
    const skillIdsByLearner = new Map<string, Set<string>>();
    const responseCountByLearnerSkill = new Map<string, number>();

    for (const response of fittedModel.responses) {
      const set = skillIdsByLearner.get(response.learnerId) ?? new Set<string>();
      set.add(response.skillId);
      skillIdsByLearner.set(response.learnerId, set);

      const key = `${response.learnerId}::${response.skillId}`;
      responseCountByLearnerSkill.set(key, (responseCountByLearnerSkill.get(key) ?? 0) + 1);
    }

    const learners: MasteryLearnerEntry[] = fittedModel.learners.map((learnerResult) => {
      const skillIds = [...(skillIdsByLearner.get(learnerResult.learnerId) ?? [])];
      const skills = skillIds.map((skillId) => {
        const item = itemsBySkill.get(skillId);
        const a = item?.a ?? 1;
        const b = item?.b ?? 0;
        const key = `${learnerResult.learnerId}::${skillId}`;
        return {
          skillId,
          metric: 'ability_theta' as const,
          value: learnerResult.theta,
          responseCount: responseCountByLearnerSkill.get(key) ?? 0,
          details: {
            itemDiscrimination: a,
            itemDifficulty: b,
            predictedProbabilityCorrect: probabilityCorrect(learnerResult.theta, a, b),
          },
        };
      });
      return { learnerId: learnerResult.learnerId, skills };
    });

    return {
      model: 'irt',
      generatedAt: new Date().toISOString(),
      learners,
      meta: { items: fittedModel.items },
    };
  }
}
