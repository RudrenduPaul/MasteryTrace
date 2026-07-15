import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { EventValidationError, parseResponseEvents, type ResponseEvent } from '../../core/event-schema.js';
import { runScoring, type ModelSelector } from '../../core/engine.js';
import { loadConfig } from '../../core/config.js';
import { fail, ok } from '../format.js';
import type { CommandResult } from '../types.js';
import { EVENTS_STATE_FILENAME, STATE_DIR } from './record.js';

export interface ScoreOptions {
  json: boolean;
  model: ModelSelector;
}

export const SCORES_STATE_FILENAME = 'scores.json';

/**
 * Fits and scores the stored event log (`.masterytrace/events.json`,
 * written by `masterytrace record`) with the requested model(s), writing
 * the unified report(s) to `.masterytrace/scores.json`.
 */
export function runScore(cwd: string, options: ScoreOptions): CommandResult {
  const eventsPath = join(cwd, STATE_DIR, EVENTS_STATE_FILENAME);
  if (!existsSync(eventsPath)) {
    const message = `No stored event log found at ${eventsPath}. Run 'masterytrace record <path>' first.`;
    return fail(1, options.json, { error: message }, `${message}\n`);
  }

  let events: ResponseEvent[];
  try {
    const raw: unknown = JSON.parse(readFileSync(eventsPath, 'utf-8'));
    events = parseResponseEvents(raw);
  } catch (error) {
    if (error instanceof EventValidationError) {
      return fail(
        2,
        options.json,
        { error: error.message, issues: error.issues },
        `Validation error:\n${error.message}\n`,
      );
    }
    const message = error instanceof Error ? error.message : String(error);
    return fail(1, options.json, { error: message }, `Error: ${message}\n`);
  }

  const config = loadConfig(cwd);
  const result = runScoring(events, options.model, config);

  const scoresPath = join(cwd, STATE_DIR, SCORES_STATE_FILENAME);
  writeFileSync(scoresPath, `${JSON.stringify(result, null, 2)}\n`, 'utf-8');

  return ok(
    options.json,
    { model: options.model, eventCount: events.length, storedAt: scoresPath },
    `Scored ${events.length} event(s) with model(s): ${options.model}\nWrote ${scoresPath}\n`,
  );
}
