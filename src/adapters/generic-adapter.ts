import { lstatSync, readFileSync } from 'node:fs';
import { extname } from 'node:path';
import { parseResponseEvents, type ResponseEvent } from '../core/event-schema.js';

/**
 * A source of response events. `load` takes a local file path and returns
 * validated events. Future adapters (e.g. for a specific tutoring system's
 * native log format) implement this same interface, so the engine and CLI
 * never need to know which adapter produced the events.
 */
export interface EventAdapter {
  name: string;
  load(path: string): ResponseEvent[];
}

function assertReadableRegularFile(path: string): void {
  // lstat (not stat) never follows a symlink, so a symlink at `path` is
  // caught here even if its target is a regular file elsewhere on disk.
  const stats = lstatSync(path);
  if (stats.isSymbolicLink()) {
    throw new Error(`Refusing to read '${path}': symlinks are not supported for event log paths.`);
  }
  if (!stats.isFile()) {
    throw new Error(`Refusing to read '${path}': not a regular file.`);
  }
}

const CSV_COLUMNS = ['learner_id', 'skill_id', 'correct', 'timestamp'] as const;

/**
 * Parses a CSV `correct` cell into a boolean. Only recognizes `true`/`false`
 * and `1`/`0` (case-insensitive, trimmed); anything else is returned as the
 * original raw string rather than silently guessed. That matters: coercing
 * every unrecognized value to `false` (as e.g. `Boolean(raw)`-style logic
 * effectively would) would make a typo, an empty cell from a shifted column,
 * or a "yes"/"no" export format silently record as an incorrect response
 * instead of surfacing as bad data. Returning the raw string instead lets
 * it fail ResponseEventSchema's `correct` boolean check with a clear,
 * row-numbered validation error, exactly like malformed JSON input does.
 */
function parseCsvBoolean(raw: string): boolean | string {
  const normalized = raw.trim().toLowerCase();
  if (normalized === 'true' || normalized === '1') return true;
  if (normalized === 'false' || normalized === '0') return false;
  return raw;
}

/**
 * Parses the fixed-column CSV format (`learner_id,skill_id,correct,timestamp`)
 * into the raw row shape event-schema expects, so it goes through the same
 * validation as JSON input. Deliberately hand-rolled rather than pulling in
 * a CSV library: the format has no quoting/escaping requirements (skill and
 * learner ids are plain identifiers), so a dependency would buy nothing.
 */
export function parseCsv(content: string): unknown[] {
  const lines = content.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length === 0) {
    return [];
  }

  const header = (lines[0] ?? '').split(',').map((h) => h.trim());
  const columnIndex = new Map(header.map((name, index) => [name, index]));
  for (const required of CSV_COLUMNS) {
    if (!columnIndex.has(required)) {
      throw new Error(
        `CSV event log is missing required column '${required}'. Expected header: ${CSV_COLUMNS.join(',')}`,
      );
    }
  }

  return lines.slice(1).map((line) => {
    const cells = line.split(',');
    const cell = (name: (typeof CSV_COLUMNS)[number]): string => {
      const index = columnIndex.get(name);
      return index === undefined ? '' : (cells[index] ?? '').trim();
    };
    return {
      learnerId: cell('learner_id'),
      skillId: cell('skill_id'),
      correct: parseCsvBoolean(cell('correct')),
      timestamp: cell('timestamp'),
    };
  });
}

/**
 * The only EventAdapter shipped in v0.1: reads a JSON array of response
 * events, or a CSV file with columns `learner_id,skill_id,correct,timestamp`,
 * chosen by file extension.
 */
export const genericAdapter: EventAdapter = {
  name: 'generic',
  load(path: string): ResponseEvent[] {
    assertReadableRegularFile(path);
    const content = readFileSync(path, 'utf-8');
    const extension = extname(path).toLowerCase();

    let raw: unknown;
    if (extension === '.csv') {
      raw = parseCsv(content);
    } else {
      raw = JSON.parse(content);
    }

    return parseResponseEvents(raw);
  },
};
