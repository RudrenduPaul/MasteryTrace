import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { runRecord } from '../../src/cli/commands/record.js';

describe('runRecord', () => {
  let dir: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'masterytrace-record-'));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('records a valid JSON event log to .masterytrace/events.json (exit 0)', () => {
    const src = join(dir, 'events.json');
    writeFileSync(
      src,
      JSON.stringify([{ learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' }]),
    );
    const result = runRecord(dir, src, { json: false });
    expect(result.exitCode).toBe(0);
    const stored = JSON.parse(readFileSync(join(dir, '.masterytrace', 'events.json'), 'utf-8')) as unknown[];
    expect(stored).toHaveLength(1);
  });

  it('records a valid CSV event log', () => {
    const src = join(dir, 'events.csv');
    writeFileSync(src, 'learner_id,skill_id,correct,timestamp\nl1,s1,true,2026-01-01T00:00:00Z\n');
    const result = runRecord(dir, src, { json: false });
    expect(result.exitCode).toBe(0);
  });

  it('replaces a previously stored event log rather than appending', () => {
    const first = join(dir, 'first.json');
    writeFileSync(
      first,
      JSON.stringify([{ learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' }]),
    );
    runRecord(dir, first, { json: false });

    const second = join(dir, 'second.json');
    writeFileSync(
      second,
      JSON.stringify([{ learnerId: 'l2', skillId: 's2', correct: false, timestamp: '2026-01-02T00:00:00Z' }]),
    );
    runRecord(dir, second, { json: false });

    const stored = JSON.parse(readFileSync(join(dir, '.masterytrace', 'events.json'), 'utf-8')) as {
      learnerId: string;
    }[];
    expect(stored).toHaveLength(1);
    expect(stored[0]?.learnerId).toBe('l2');
  });

  it('returns exit code 2 for a validation error (bad event data)', () => {
    const src = join(dir, 'bad.json');
    writeFileSync(src, JSON.stringify([{ learnerId: '', skillId: 's1', correct: true, timestamp: 'bad' }]));
    const result = runRecord(dir, src, { json: false });
    expect(result.exitCode).toBe(2);
    expect(result.stderr).toMatch(/Validation error/);
  });

  it('returns exit code 1 for a general error (file not found)', () => {
    const result = runRecord(dir, join(dir, 'does-not-exist.json'), { json: false });
    expect(result.exitCode).toBe(1);
  });

  it('emits machine-readable JSON on validation failure when --json is set', () => {
    const src = join(dir, 'bad.json');
    writeFileSync(src, JSON.stringify([{ learnerId: '', skillId: 's1', correct: true, timestamp: 'bad' }]));
    const result = runRecord(dir, src, { json: true });
    expect(result.exitCode).toBe(2);
    const parsed = JSON.parse(result.stdout) as { issues: string[] };
    expect(parsed.issues.length).toBeGreaterThan(0);
  });

  it('records an empty event log without error', () => {
    const src = join(dir, 'empty.json');
    writeFileSync(src, '[]');
    const result = runRecord(dir, src, { json: false });
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toMatch(/Stored 0 event/);
  });
});
