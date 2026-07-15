import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { runReport } from '../../src/cli/commands/report.js';
import { runScoring } from '../../src/core/engine.js';
import type { ResponseEvent } from '../../src/core/event-schema.js';

function seedScores(dir: string): void {
  const events: ResponseEvent[] = [
    { learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
    { learnerId: 'l1', skillId: 's1', correct: false, timestamp: '2026-01-02T00:00:00Z' },
  ];
  const result = runScoring(events, 'both');
  const stateDir = join(dir, '.masterytrace');
  mkdirSync(stateDir, { recursive: true });
  writeFileSync(join(stateDir, 'scores.json'), JSON.stringify(result));
}

describe('runReport', () => {
  let dir: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'masterytrace-report-'));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('returns exit code 1 when no scores have been computed yet', () => {
    const result = runReport(dir, { json: false, format: 'table' });
    expect(result.exitCode).toBe(1);
  });

  it('renders a human-readable table by default', () => {
    seedScores(dir);
    const result = runReport(dir, { json: false, format: 'table' });
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toMatch(/learner/);
    expect(result.stdout).toMatch(/l1/);
    expect(result.stdout).toMatch(/bkt/);
    expect(result.stdout).toMatch(/irt/);
  });

  it('renders markdown when --format markdown is passed', () => {
    seedScores(dir);
    const result = runReport(dir, { json: false, format: 'markdown' });
    expect(result.stdout).toMatch(/\|\s*learner\s*\|/);
    expect(result.stdout).toContain('---');
  });

  it('renders JSON when --format json is passed', () => {
    seedScores(dir);
    const result = runReport(dir, { json: false, format: 'json' });
    expect(() => JSON.parse(result.stdout)).not.toThrow();
  });

  it('the global --json flag always wins over --format', () => {
    seedScores(dir);
    const result = runReport(dir, { json: true, format: 'table' });
    expect(() => JSON.parse(result.stdout)).not.toThrow();
  });

  it('reports "No scores found" for an empty (but valid) scored event log', () => {
    const stateDir = join(dir, '.masterytrace');
    mkdirSync(stateDir, { recursive: true });
    writeFileSync(join(stateDir, 'scores.json'), JSON.stringify(runScoring([], 'both')));
    const result = runReport(dir, { json: false, format: 'table' });
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toMatch(/No scores found/);
  });

  it('reports "No scores found" in markdown format too, for an empty scored event log', () => {
    const stateDir = join(dir, '.masterytrace');
    mkdirSync(stateDir, { recursive: true });
    writeFileSync(join(stateDir, 'scores.json'), JSON.stringify(runScoring([], 'both')));
    const result = runReport(dir, { json: false, format: 'markdown' });
    expect(result.stdout).toMatch(/No scores found/);
  });

  it('returns exit code 1 when the stored scores file is not valid JSON at all', () => {
    const stateDir = join(dir, '.masterytrace');
    mkdirSync(stateDir, { recursive: true });
    writeFileSync(join(stateDir, 'scores.json'), '{not valid json');
    const result = runReport(dir, { json: false, format: 'table' });
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toMatch(/Error reading scores/);
  });
});
