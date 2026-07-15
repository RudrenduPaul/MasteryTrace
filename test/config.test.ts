import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { DEFAULT_CONFIG, loadConfig } from '../src/core/config.js';

describe('loadConfig', () => {
  let dir: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'masterytrace-config-'));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('returns DEFAULT_CONFIG when no config file is present', () => {
    expect(loadConfig(dir)).toEqual(DEFAULT_CONFIG);
  });

  it('merges an on-disk masterytrace.config.json over the defaults', () => {
    writeFileSync(join(dir, 'masterytrace.config.json'), JSON.stringify({ irt: { iterations: 42 } }));
    const config = loadConfig(dir);
    expect(config.irt).toEqual({ iterations: 42 });
    expect(config.bkt).toEqual(DEFAULT_CONFIG.bkt);
  });
});
