import { describe, expect, it } from 'vitest';
import {
  EventValidationError,
  parseResponseEvents,
  ResponseEventSchema,
} from '../src/core/event-schema.js';

describe('ResponseEventSchema / parseResponseEvents', () => {
  it('accepts a well-formed event', () => {
    const events = parseResponseEvents([
      { learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
    ]);
    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({
      learnerId: 'l1',
      skillId: 's1',
      correct: true,
      timestamp: '2026-01-01T00:00:00Z',
    });
  });

  it('accepts multiple valid events and preserves order', () => {
    const raw = [
      { learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
      { learnerId: 'l1', skillId: 's1', correct: false, timestamp: '2026-01-02T00:00:00Z' },
    ];
    const events = parseResponseEvents(raw);
    expect(events.map((e) => e.correct)).toEqual([true, false]);
  });

  it('rejects a non-array top-level value', () => {
    expect(() => parseResponseEvents({ not: 'an array' })).toThrow(EventValidationError);
  });

  it('rejects an empty-string learnerId', () => {
    expect(() =>
      parseResponseEvents([{ learnerId: '', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' }]),
    ).toThrow(EventValidationError);
  });

  it('rejects a missing skillId field', () => {
    try {
      parseResponseEvents([{ learnerId: 'l1', correct: true, timestamp: '2026-01-01T00:00:00Z' }]);
      throw new Error('expected parseResponseEvents to throw');
    } catch (error) {
      expect(error).toBeInstanceOf(EventValidationError);
      const validationError = error as EventValidationError;
      expect(validationError.issues.some((issue) => issue.includes("field 'skillId'"))).toBe(true);
      expect(validationError.issues.some((issue) => issue.includes('row 0'))).toBe(true);
    }
  });

  it('rejects a non-boolean correct field', () => {
    try {
      parseResponseEvents([
        { learnerId: 'l1', skillId: 's1', correct: 'yes', timestamp: '2026-01-01T00:00:00Z' },
      ]);
      throw new Error('expected parseResponseEvents to throw');
    } catch (error) {
      const validationError = error as EventValidationError;
      expect(validationError.issues.some((issue) => issue.includes("field 'correct'"))).toBe(true);
    }
  });

  it('rejects an invalid (non-ISO-8601) timestamp', () => {
    try {
      parseResponseEvents([
        { learnerId: 'l1', skillId: 's1', correct: true, timestamp: 'not-a-date' },
      ]);
      throw new Error('expected parseResponseEvents to throw');
    } catch (error) {
      const validationError = error as EventValidationError;
      expect(validationError.issues.some((issue) => issue.includes("field 'timestamp'"))).toBe(true);
    }
  });

  it('reports every failing row and field, not just the first', () => {
    try {
      parseResponseEvents([
        { learnerId: 'l1', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
        { learnerId: '', skillId: 's1', correct: true, timestamp: '2026-01-01T00:00:00Z' },
        { learnerId: 'l1', skillId: 's1', correct: 'nope', timestamp: 'bad-timestamp' },
      ]);
      throw new Error('expected parseResponseEvents to throw');
    } catch (error) {
      const validationError = error as EventValidationError;
      // Row 0 is valid; rows 1 and 2 each contribute at least one issue.
      expect(validationError.issues.some((issue) => issue.startsWith('row 1'))).toBe(true);
      expect(validationError.issues.filter((issue) => issue.startsWith('row 2')).length).toBe(2);
    }
  });

  it('accepts an empty array (empty event log)', () => {
    expect(parseResponseEvents([])).toEqual([]);
  });

  it('exposes the underlying zod schema for direct use', () => {
    const result = ResponseEventSchema.safeParse({
      learnerId: 'l1',
      skillId: 's1',
      correct: true,
      timestamp: '2026-01-01T00:00:00Z',
    });
    expect(result.success).toBe(true);
  });
});
