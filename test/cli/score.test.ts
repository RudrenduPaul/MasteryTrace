import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { runScore } from '../../src/cli/commands/score.js';
import type { EngineResult } from '../../src/core/engine.js';

function seedStoredEvents(dir: string, raw: unknown): void {
  const stateDir = join(dir, '.masterytrace');
  mkdirSync(stateDir, { recursive: true });
  writeFileSync(join(stateDir, 'events.json'), JSON.stringify(raw));
}

describe('runScore', () => {
  let dir: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'masterytrace-score-'));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('returns exit code 1 when no event log has been recorded yet', () => {
    const result = runScore(dir, { json: false, model: 'both' });
    expect(result.exitCode).toBe(1);
  });

  it('scores a stored event log and writes .masterytrace/scores.json', () => {
    seedStoredEvents(dir, [
      { learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
      { learnerId: 'l1', skillId: 's1', correct: false, timestamp: '2026-01-02T00:00:00Z' },
    ]);
    const result = runScore(dir, { json: false, model: 'both' });
    expect(result.exitCode).toBe(0);

    const scores = JSON.parse(readFileSync(join(dir, '.masterytrace', 'scores.json'), 'utf-8')) as EngineResult;
    expect(scores.reports.map((r) => r.model).sort()).toEqual(['bkt', 'irt']);
  });

  it('runs only the requested model', () => {
    seedStoredEvents(dir, [
      { learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
    ]);
    const result = runScore(dir, { json: false, model: 'bkt' });
    expect(result.exitCode).toBe(0);
    const scores = JSON.parse(readFileSync(join(dir, '.masterytrace', 'scores.json'), 'utf-8')) as EngineResult;
    expect(scores.reports).toHaveLength(1);
    expect(scores.reports[0]?.model).toBe('bkt');
  });

  it('returns exit code 2 when the stored event log fails schema validation', () => {
    seedStoredEvents(dir, [{ learnerId: '', skillId: 's1', correct: true, timestamp: 'bad' }]);
    const result = runScore(dir, { json: false, model: 'both' });
    expect(result.exitCode).toBe(2);
  });

  it('returns exit code 1 when the stored event log file is not valid JSON at all', () => {
    const stateDir = join(dir, '.masterytrace');
    mkdirSync(stateDir, { recursive: true });
    writeFileSync(join(stateDir, 'events.json'), '{not valid json');
    const result = runScore(dir, { json: false, model: 'both' });
    expect(result.exitCode).toBe(1);
  });

  it('scores an empty stored event log without error', () => {
    seedStoredEvents(dir, []);
    const result = runScore(dir, { json: false, model: 'both' });
    expect(result.exitCode).toBe(0);
  });

  it('respects masterytrace.config.json overrides when present', () => {
    seedStoredEvents(dir, [
      { learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
    ]);
    writeFileSync(
      join(dir, 'masterytrace.config.json'),
      JSON.stringify({ bkt: { defaultParams: { pInit: 0.9 } } }),
    );
    runScore(dir, { json: false, model: 'bkt' });
    const scores = JSON.parse(readFileSync(join(dir, '.masterytrace', 'scores.json'), 'utf-8')) as EngineResult;
    expect(scores.reports[0]?.meta?.params).toMatchObject({ s1: { pInit: 0.9 } });
  });
});
