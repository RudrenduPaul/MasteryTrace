import { describe, expect, it } from 'vitest';
import { runScoring } from '../src/core/engine.js';
import type { ResponseEvent } from '../src/core/event-schema.js';

const events: ResponseEvent[] = [
  { learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
  { learnerId: 'l1', skillId: 's1', correct: false, timestamp: '2026-01-02T00:00:00Z' },
  { learnerId: 'l2', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
];

describe('runScoring', () => {
  it('defaults to running both models', () => {
    const result = runScoring(events);
    expect(result.reports.map((r) => r.model).sort()).toEqual(['bkt', 'irt']);
  });

  it('runs only bkt when selector is "bkt"', () => {
    const result = runScoring(events, 'bkt');
    expect(result.reports).toHaveLength(1);
    expect(result.reports[0]?.model).toBe('bkt');
  });

  it('runs only irt when selector is "irt"', () => {
    const result = runScoring(events, 'irt');
    expect(result.reports).toHaveLength(1);
    expect(result.reports[0]?.model).toBe('irt');
  });

  it('passes per-model config through to the underlying models', () => {
    const result = runScoring(events, 'bkt', { bkt: { defaultParams: { pInit: 0.9 } } });
    const bktReport = result.reports[0];
    expect(bktReport?.meta?.params).toMatchObject({ s1: { pInit: 0.9 } });
  });

  it('produces an ISO 8601 generatedAt timestamp', () => {
    const result = runScoring(events);
    expect(() => new Date(result.generatedAt).toISOString()).not.toThrow();
  });

  it('handles an empty event log for both models', () => {
    const result = runScoring([], 'both');
    expect(result.reports).toHaveLength(2);
    for (const report of result.reports) {
      expect(report.learners).toEqual([]);
    }
  });
});
