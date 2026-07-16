import { mkdtempSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { genericAdapter, parseCsv } from '../src/adapters/generic-adapter.js';
import { EventValidationError } from '../src/core/event-schema.js';

describe('parseCsv', () => {
  it('parses a well-formed CSV into raw event-shaped rows', () => {
    const csv =
      'learner_id,skill_id,correct,timestamp\n' +
      'l1,s1,true,2026-01-01T00:00:00Z\n' +
      'l1,s1,false,2026-01-02T00:00:00Z\n';
    const rows = parseCsv(csv) as { learnerId: string; skillId: string; correct: boolean; timestamp: string }[];
    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({
      learnerId: 'l1',
      skillId: 's1',
      correct: true,
      timestamp: '2026-01-01T00:00:00Z',
    });
    expect(rows[1]?.correct).toBe(false);
  });

  it('accepts "1"/"0" as boolean correct values', () => {
    const csv = 'learner_id,skill_id,correct,timestamp\nl1,s1,1,2026-01-01T00:00:00Z\nl1,s1,0,2026-01-02T00:00:00Z\n';
    const rows = parseCsv(csv) as { correct: boolean }[];
    expect(rows[0]?.correct).toBe(true);
    expect(rows[1]?.correct).toBe(false);
  });

  it('is tolerant of column reordering, keyed by header', () => {
    const csv = 'timestamp,correct,skill_id,learner_id\n2026-01-01T00:00:00Z,true,s1,l1\n';
    const rows = parseCsv(csv) as { learnerId: string; skillId: string }[];
    expect(rows[0]).toMatchObject({ learnerId: 'l1', skillId: 's1' });
  });

  it('returns an empty array for an empty (header-only or blank) file', () => {
    expect(parseCsv('')).toEqual([]);
    expect(parseCsv('learner_id,skill_id,correct,timestamp\n')).toEqual([]);
  });

  it('throws when a required column is missing', () => {
    expect(() => parseCsv('learner_id,skill_id,timestamp\nl1,s1,2026-01-01T00:00:00Z\n')).toThrow(
      /missing required column/i,
    );
  });

  it('does not silently coerce an unrecognized "correct" value to false', () => {
    // Regression test: a garbage/typo'd correct cell (or an empty cell from
    // a shifted column) used to be silently interpreted as `false` instead
    // of surfacing as bad data. It must now come out as the original raw
    // string so schema validation rejects it explicitly.
    const csv = 'learner_id,skill_id,correct,timestamp\nl1,s1,maybe,2026-01-01T00:00:00Z\n';
    const rows = parseCsv(csv) as { correct: unknown }[];
    expect(rows[0]?.correct).toBe('maybe');
    expect(rows[0]?.correct).not.toBe(false);
  });
});

describe('genericAdapter', () => {
  let dir: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'masterytrace-adapter-'));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('loads and validates a JSON event log', () => {
    const path = join(dir, 'events.json');
    writeFileSync(
      path,
      JSON.stringify([{ learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' }]),
    );
    const events = genericAdapter.load(path);
    expect(events).toHaveLength(1);
    expect(events[0]?.learnerId).toBe('l1');
  });

  it('loads and validates a CSV event log', () => {
    const path = join(dir, 'events.csv');
    writeFileSync(path, 'learner_id,skill_id,correct,timestamp\nl1,s1,true,2026-01-01T00:00:00Z\n');
    const events = genericAdapter.load(path);
    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({
      learnerId: 'l1',
      skillId: 's1',
      correct: true,
      timestamp: '2026-01-01T00:00:00Z',
    });
  });

  it('throws EventValidationError for malformed JSON event data', () => {
    const path = join(dir, 'bad.json');
    writeFileSync(path, JSON.stringify([{ learnerId: 'l1', correct: true, timestamp: 'nope' }]));
    expect(() => genericAdapter.load(path)).toThrow(EventValidationError);
  });

  it('throws EventValidationError for malformed CSV event data', () => {
    const path = join(dir, 'bad.csv');
    writeFileSync(path, 'learner_id,skill_id,correct,timestamp\nl1,s1,notabool,not-a-date\n');
    expect(() => genericAdapter.load(path)).toThrow(EventValidationError);
  });

  it('throws EventValidationError for a CSV row with an unrecognized "correct" value, even with an otherwise-valid timestamp', () => {
    const path = join(dir, 'bad-correct.csv');
    writeFileSync(path, 'learner_id,skill_id,correct,timestamp\nl1,s1,maybe,2026-01-01T00:00:00Z\n');
    expect(() => genericAdapter.load(path)).toThrow(EventValidationError);
  });

  it('refuses to read a symlinked path', () => {
    const targetPath = join(dir, 'real.json');
    writeFileSync(targetPath, '[]');
    const linkPath = join(dir, 'link.json');
    symlinkSync(targetPath, linkPath);
    expect(() => genericAdapter.load(linkPath)).toThrow(/symlink/i);
  });

  it('handles an empty JSON array (empty event log)', () => {
    const path = join(dir, 'empty.json');
    writeFileSync(path, '[]');
    expect(genericAdapter.load(path)).toEqual([]);
  });

  it('refuses to read a path that is not a regular file (e.g. a directory)', () => {
    expect(() => genericAdapter.load(dir)).toThrow(/not a regular file/i);
  });
});
