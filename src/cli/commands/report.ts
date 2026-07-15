import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { EngineResult } from '../../core/engine.js';
import { fail } from '../format.js';
import type { CommandResult } from '../types.js';
import { STATE_DIR } from './record.js';
import { SCORES_STATE_FILENAME } from './score.js';

export type ReportFormat = 'table' | 'json' | 'markdown';

export interface ReportOptions {
  json: boolean;
  format: ReportFormat;
}

interface ReportRow {
  learnerId: string;
  skillId: string;
  model: string;
  metric: string;
  value: number;
  responseCount: number;
}

function buildRows(result: EngineResult): ReportRow[] {
  const rows: ReportRow[] = [];
  for (const report of result.reports) {
    for (const learner of report.learners) {
      for (const skill of learner.skills) {
        rows.push({
          learnerId: learner.learnerId,
          skillId: skill.skillId,
          model: report.model,
          metric: skill.metric,
          value: skill.value,
          responseCount: skill.responseCount,
        });
      }
    }
  }
  rows.sort(
    (a, b) =>
      a.learnerId.localeCompare(b.learnerId) ||
      a.skillId.localeCompare(b.skillId) ||
      a.model.localeCompare(b.model),
  );
  return rows;
}

const TABLE_HEADER = ['learner', 'skill', 'model', 'metric', 'value', 'responses'];

function renderTable(rows: ReportRow[]): string {
  if (rows.length === 0) {
    return 'No scores found.\n';
  }
  const data = rows.map((r) => [
    r.learnerId,
    r.skillId,
    r.model,
    r.metric,
    r.value.toFixed(4),
    String(r.responseCount),
  ]);
  const widths = TABLE_HEADER.map((h, i) =>
    Math.max(h.length, ...data.map((row) => (row[i] ?? '').length)),
  );
  const renderRow = (cells: string[]): string =>
    cells.map((c, i) => c.padEnd(widths[i] ?? 0)).join('  ');
  return (
    [renderRow(TABLE_HEADER), renderRow(widths.map((w) => '-'.repeat(w))), ...data.map(renderRow)].join(
      '\n',
    ) + '\n'
  );
}

function renderMarkdown(rows: ReportRow[]): string {
  if (rows.length === 0) {
    return 'No scores found.\n';
  }
  const lines = [
    `| ${TABLE_HEADER.join(' | ')} |`,
    `| ${TABLE_HEADER.map(() => '---').join(' | ')} |`,
    ...rows.map(
      (r) =>
        `| ${r.learnerId} | ${r.skillId} | ${r.model} | ${r.metric} | ${r.value.toFixed(4)} | ${r.responseCount} |`,
    ),
  ];
  return lines.join('\n') + '\n';
}

/**
 * Reads `.masterytrace/scores.json` (written by `masterytrace score`) and
 * prints a per-learner, per-skill mastery table in the requested format.
 * The global `--json` flag always wins over `--format` and prints the raw
 * stored report as machine-readable JSON.
 */
export function runReport(cwd: string, options: ReportOptions): CommandResult {
  const scoresPath = join(cwd, STATE_DIR, SCORES_STATE_FILENAME);
  if (!existsSync(scoresPath)) {
    const message = `No scores found at ${scoresPath}. Run 'masterytrace score' first.`;
    return fail(1, options.json, { error: message }, `${message}\n`);
  }

  let result: EngineResult;
  try {
    result = JSON.parse(readFileSync(scoresPath, 'utf-8')) as EngineResult;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return fail(1, options.json, { error: message }, `Error reading scores: ${message}\n`);
  }

  if (options.json) {
    return { exitCode: 0, stdout: `${JSON.stringify(result)}\n` };
  }

  const rows = buildRows(result);
  let text: string;
  if (options.format === 'markdown') {
    text = renderMarkdown(rows);
  } else if (options.format === 'json') {
    text = `${JSON.stringify(result, null, 2)}\n`;
  } else {
    text = renderTable(rows);
  }

  return { exitCode: 0, stdout: text };
}
