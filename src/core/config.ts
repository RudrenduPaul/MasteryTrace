import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { BktConfig } from '../models/bkt.js';
import type { IrtConfig } from '../models/irt.js';

/**
 * Project-level configuration read from `masterytrace.config.json` in the
 * current directory (scaffolded by `masterytrace init`). Both sections are
 * optional; anything omitted falls back to each model's own defaults.
 */
export interface MasteryTraceConfig {
  bkt?: BktConfig;
  irt?: IrtConfig;
}

/** The config `masterytrace init` writes out and `loadConfig` falls back to when no config file is present. */
export const DEFAULT_CONFIG: MasteryTraceConfig = {
  bkt: { fit: false },
  irt: {},
};

export const CONFIG_FILENAME = 'masterytrace.config.json';

/**
 * Loads `masterytrace.config.json` from `cwd` if present, merging it over
 * DEFAULT_CONFIG; otherwise returns DEFAULT_CONFIG unchanged.
 */
export function loadConfig(cwd: string): MasteryTraceConfig {
  const configPath = join(cwd, CONFIG_FILENAME);
  if (!existsSync(configPath)) {
    return DEFAULT_CONFIG;
  }
  const raw = JSON.parse(readFileSync(configPath, 'utf-8')) as MasteryTraceConfig;
  return { ...DEFAULT_CONFIG, ...raw };
}
