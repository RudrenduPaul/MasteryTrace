import { existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { SAMPLE_EVENTS } from '../../data/sample-events.js';
import { DEFAULT_CONFIG } from '../../core/config.js';
import { ok } from '../format.js';
import type { CommandResult } from '../types.js';

export interface InitOptions {
  json: boolean;
  force: boolean;
}

export const EVENTS_SAMPLE_FILENAME = 'events.json';
export const CONFIG_FILENAME = 'masterytrace.config.json';

/**
 * Scaffolds a bundled sample `events.json` (3 learners x 3 skills, several
 * responses each) and a default `masterytrace.config.json` in `cwd`. Existing
 * files are left untouched unless `--force` is passed.
 */
export function runInit(cwd: string, options: InitOptions): CommandResult {
  const eventsPath = join(cwd, EVENTS_SAMPLE_FILENAME);
  const configPath = join(cwd, CONFIG_FILENAME);

  const created: string[] = [];
  const skipped: string[] = [];

  if (!options.force && existsSync(eventsPath)) {
    skipped.push(EVENTS_SAMPLE_FILENAME);
  } else {
    writeFileSync(eventsPath, `${JSON.stringify(SAMPLE_EVENTS, null, 2)}\n`, 'utf-8');
    created.push(EVENTS_SAMPLE_FILENAME);
  }

  if (!options.force && existsSync(configPath)) {
    skipped.push(CONFIG_FILENAME);
  } else {
    writeFileSync(configPath, `${JSON.stringify(DEFAULT_CONFIG, null, 2)}\n`, 'utf-8');
    created.push(CONFIG_FILENAME);
  }

  const lines: string[] = [];
  if (created.length > 0) lines.push(`Created: ${created.join(', ')}`);
  if (skipped.length > 0) {
    lines.push(`Skipped (already exists, use --force to overwrite): ${skipped.join(', ')}`);
  }
  lines.push("Next: run 'masterytrace record events.json' to load it, then 'masterytrace score'.");

  return ok(options.json, { created, skipped }, `${lines.join('\n')}\n`);
}
