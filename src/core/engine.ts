import type { ResponseEvent } from './event-schema.js';
import type { MasteryReport } from './scoring-model.js';
import { BktModel, type BktConfig } from '../models/bkt.js';
import { IrtModel, type IrtConfig } from '../models/irt.js';

export type ModelSelector = 'bkt' | 'irt' | 'both';

export interface EngineConfig {
  bkt?: BktConfig;
  irt?: IrtConfig;
}

export interface EngineResult {
  generatedAt: string;
  reports: MasteryReport[];
}

/**
 * Orchestrates the scoring pipeline: given a validated event log, runs
 * whichever model(s) were requested and returns their reports together.
 * This is the single place that knows how to wire the engine config into
 * concrete model instances; callers (CLI or library consumers) only pick a
 * model selector and pass raw events.
 */
export function runScoring(
  events: ResponseEvent[],
  selector: ModelSelector = 'both',
  config: EngineConfig = {},
): EngineResult {
  const reports: MasteryReport[] = [];

  if (selector === 'bkt' || selector === 'both') {
    const model = new BktModel(config.bkt);
    reports.push(model.score(model.fit(events)));
  }

  if (selector === 'irt' || selector === 'both') {
    const model = new IrtModel(config.irt);
    reports.push(model.score(model.fit(events)));
  }

  return { generatedAt: new Date().toISOString(), reports };
}
