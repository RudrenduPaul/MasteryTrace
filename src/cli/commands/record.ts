import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { genericAdapter } from '../../adapters/generic-adapter.js';
import { EventValidationError } from '../../core/event-schema.js';
import { fail, ok } from '../format.js';
import type { CommandResult } from '../types.js';

export interface RecordOptions {
  json: boolean;
}

export const STATE_DIR = '.masterytrace';
export const EVENTS_STATE_FILENAME = 'events.json';

/**
 * Validates and loads an event log (JSON or CSV, chosen by file extension)
 * and stores it to `.masterytrace/events.json`. Storing always *replaces*
 * any previously stored log in v0.1 (there is no append/merge mode yet).
 */
export function runRecord(cwd: string, eventLogPath: string, options: RecordOptions): CommandResult {
  let events;
  try {
    events = genericAdapter.load(eventLogPath);
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

  const stateDir = join(cwd, STATE_DIR);
  mkdirSync(stateDir, { recursive: true });
  const statePath = join(stateDir, EVENTS_STATE_FILENAME);
  writeFileSync(statePath, `${JSON.stringify(events, null, 2)}\n`, 'utf-8');

  return ok(
    options.json,
    { eventCount: events.length, storedAt: statePath },
    `Stored ${events.length} event(s) to ${statePath}\n` +
      '(record replaces any previously stored event log; see --help for details.)\n',
  );
}
