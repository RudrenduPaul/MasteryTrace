import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { runInit } from '../../src/cli/commands/init.js';
import { parseResponseEvents } from '../../src/core/event-schema.js';

describe('runInit', () => {
  let dir: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'masterytrace-init-'));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('scaffolds a valid sample events.json and a config file', () => {
    const result = runInit(dir, { json: false, force: false });
    expect(result.exitCode).toBe(0);
    expect(existsSync(join(dir, 'events.json'))).toBe(true);
    expect(existsSync(join(dir, 'masterytrace.config.json'))).toBe(true);

    const raw: unknown = JSON.parse(readFileSync(join(dir, 'events.json'), 'utf-8'));
    const events = parseResponseEvents(raw);
    expect(events.length).toBeGreaterThan(0);

    const learnerCount = new Set(events.map((e) => e.learnerId)).size;
    const skillCount = new Set(events.map((e) => e.skillId)).size;
    expect(learnerCount).toBeGreaterThanOrEqual(3);
    expect(skillCount).toBeGreaterThanOrEqual(3);
  });

  it('does not overwrite existing files without --force', () => {
    writeFileSync(join(dir, 'events.json'), '"sentinel"');
    const result = runInit(dir, { json: false, force: false });
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toMatch(/Skipped/);
    expect(readFileSync(join(dir, 'events.json'), 'utf-8')).toBe('"sentinel"');
  });

  it('overwrites existing files when --force is passed', () => {
    writeFileSync(join(dir, 'events.json'), '"sentinel"');
    const result = runInit(dir, { json: false, force: true });
    expect(result.exitCode).toBe(0);
    expect(readFileSync(join(dir, 'events.json'), 'utf-8')).not.toBe('"sentinel"');
  });

  it('skips both files (no "Created" line) when both already exist and --force is not passed', () => {
    writeFileSync(join(dir, 'events.json'), '"sentinel"');
    writeFileSync(join(dir, 'masterytrace.config.json'), '"sentinel"');
    const result = runInit(dir, { json: false, force: false });
    expect(result.exitCode).toBe(0);
    expect(result.stdout).not.toMatch(/^Created:/m);
    expect(result.stdout).toMatch(/Skipped/);
  });

  it('emits machine-readable JSON when --json is set', () => {
    const result = runInit(dir, { json: true, force: false });
    const parsed = JSON.parse(result.stdout) as { created: string[]; skipped: string[] };
    expect(parsed.created.sort()).toEqual(['events.json', 'masterytrace.config.json']);
  });
});
