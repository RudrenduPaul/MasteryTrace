import type { ResponseEvent } from './event-schema.js';

/**
 * A single per-skill mastery estimate for one learner, as produced by a
 * scoring model. `metric` names what `value` means so a report consumer
 * (or the CLI's table renderer) can label it correctly without knowing
 * which model produced it.
 */
export interface MasterySkillEntry {
  skillId: string;
  metric: 'posterior_mastery_probability' | 'ability_theta';
  value: number;
  responseCount: number;
  /** Model-specific extra detail (e.g. BKT's per-response trajectory, IRT's item a/b and predicted probability). */
  details?: Record<string, unknown>;
}

export interface MasteryLearnerEntry {
  learnerId: string;
  skills: MasterySkillEntry[];
}

/**
 * The unified shape every ScoringModel.score() returns, regardless of which
 * psychometric model produced it. This is what lets the engine and CLI treat
 * BKT and IRT interchangeably.
 */
export interface MasteryReport {
  model: string;
  generatedAt: string;
  learners: MasteryLearnerEntry[];
  meta?: Record<string, unknown>;
}

/**
 * Opaque fitted-model artifact produced by ScoringModel.fit(). Each model
 * implementation defines its own concrete shape (parameters + computed
 * per-learner/per-skill results); `score()` on that same instance knows how
 * to turn it into a MasteryReport.
 */
export interface FittedModel {
  modelName: string;
}

/**
 * Common interface both BKT and IRT implement, so an engine or CLI can fit
 * and score either model (or both) through the same code path.
 */
export interface ScoringModel<F extends FittedModel = FittedModel> {
  readonly name: string;
  fit(events: ResponseEvent[]): F;
  score(fittedModel: F): MasteryReport;
}
