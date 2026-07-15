import { z } from 'zod';

/**
 * A single learner response event: one attempt by one learner at one skill,
 * scored correct/incorrect, at a point in time.
 *
 * This is the only unit of data every scoring model and adapter in
 * MasteryTrace operates on.
 */
export const ResponseEventSchema = z.object({
  learnerId: z
    .string({ error: 'learnerId must be a string' })
    .min(1, 'learnerId must be a non-empty string'),
  skillId: z
    .string({ error: 'skillId must be a string' })
    .min(1, 'skillId must be a non-empty string'),
  correct: z.boolean({ error: 'correct must be a boolean' }),
  timestamp: z
    .string({ error: 'timestamp must be an ISO 8601 date string' })
    .refine((value) => !Number.isNaN(Date.parse(value)), {
      error: 'timestamp must be a valid ISO 8601 date string',
    }),
});

export type ResponseEvent = z.infer<typeof ResponseEventSchema>;

/**
 * Thrown when an event log fails validation. `issues` lists every field/row
 * failure found, so a caller (or the CLI) can report all problems at once
 * instead of stopping at the first one.
 */
export class EventValidationError extends Error {
  public readonly issues: string[];

  constructor(message: string, issues: string[]) {
    super(message);
    this.name = 'EventValidationError';
    this.issues = issues;
  }
}

/**
 * Parses an unknown value (typically JSON.parse output or rows decoded from
 * CSV) into a validated array of ResponseEvent. Every row is checked; on
 * failure the error lists every failing row/field, not just the first.
 */
export function parseResponseEvents(raw: unknown): ResponseEvent[] {
  if (!Array.isArray(raw)) {
    throw new EventValidationError(
      'Event log must be a JSON array of response events (row 0: expected array, got ' +
        `${typeof raw})`,
      ['row 0: expected an array of response events'],
    );
  }

  const events: ResponseEvent[] = [];
  const issues: string[] = [];

  raw.forEach((row, index) => {
    const result = ResponseEventSchema.safeParse(row);
    if (result.success) {
      events.push(result.data);
    } else {
      for (const issue of result.error.issues) {
        const field = issue.path.length > 0 ? issue.path.join('.') : '(row)';
        issues.push(`row ${index}: field '${field}' - ${issue.message}`);
      }
    }
  });

  if (issues.length > 0) {
    throw new EventValidationError(
      `Event log failed validation (${issues.length} issue${issues.length === 1 ? '' : 's'}):\n${issues.join('\n')}`,
      issues,
    );
  }

  return events;
}
