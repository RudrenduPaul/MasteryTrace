#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Command } from 'commander';
import { runInit } from './commands/init.js';
import { runRecord } from './commands/record.js';
import { runScore } from './commands/score.js';
import { runReport, type ReportFormat } from './commands/report.js';
import type { CommandResult } from './types.js';
import type { ModelSelector } from '../core/engine.js';

const moduleDir = dirname(fileURLToPath(import.meta.url));
// dist/cli/index.js -> ../../package.json is the package root's package.json.
const pkg = JSON.parse(readFileSync(join(moduleDir, '../../package.json'), 'utf-8')) as {
  version: string;
};

interface GlobalOptions {
  json: boolean;
}

function emit(result: CommandResult): void {
  if (result.stdout) {
    process.stdout.write(result.stdout);
  }
  if (result.stderr) {
    process.stderr.write(result.stderr);
  }
  process.exitCode = result.exitCode;
}

const program = new Command();

program
  .name('masterytrace')
  .description(
    'Mastery Measurement API/CLI. Fits Bayesian Knowledge Tracing (BKT) and ' +
      '2-parameter logistic Item Response Theory (IRT) models to learner ' +
      'response logs and reports per-learner, per-skill mastery estimates.',
  )
  .version(pkg.version)
  .option('--json', 'force machine-readable JSON output on stdout instead of human-formatted text', false);

program
  .command('init')
  .description(
    'Scaffold a sample events.json (3 learners x 3 skills, several responses each) ' +
      'and a default masterytrace.config.json in the current directory',
  )
  .option('--force', 'overwrite events.json/masterytrace.config.json if they already exist', false)
  .action((cmdOptions: { force: boolean }, command: Command) => {
    const globalOptions = command.optsWithGlobals<GlobalOptions>();
    emit(runInit(process.cwd(), { json: globalOptions.json, force: cmdOptions.force }));
  });

program
  .command('record')
  .argument('<path>', 'path to a JSON (array of response events) or CSV (learner_id,skill_id,correct,timestamp) event log')
  .description(
    'Validate and load an event log (JSON or CSV, auto-detected by extension) and store it ' +
      'to .masterytrace/events.json. Storing replaces any previously stored event log.',
  )
  .action((path: string, _cmdOptions: unknown, command: Command) => {
    const globalOptions = command.optsWithGlobals<GlobalOptions>();
    emit(runRecord(process.cwd(), path, { json: globalOptions.json }));
  });

program
  .command('score')
  .description(
    'Fit and score the stored event log (.masterytrace/events.json) and write results to .masterytrace/scores.json',
  )
  .option('--model <model>', 'which model(s) to run: bkt, irt, or both', 'both')
  .action((cmdOptions: { model: string }, command: Command) => {
    const globalOptions = command.optsWithGlobals<GlobalOptions>();
    if (cmdOptions.model !== 'bkt' && cmdOptions.model !== 'irt' && cmdOptions.model !== 'both') {
      emit({
        exitCode: 1,
        stdout: '',
        stderr: `Invalid --model '${cmdOptions.model}'. Expected one of: bkt, irt, both.\n`,
      });
      return;
    }
    const model: ModelSelector = cmdOptions.model;
    emit(runScore(process.cwd(), { json: globalOptions.json, model }));
  });

program
  .command('report')
  .description('Read .masterytrace/scores.json and print a per-learner, per-skill mastery table')
  .option('--format <format>', 'output format: table, json, or markdown', 'table')
  .action((cmdOptions: { format: string }, command: Command) => {
    const globalOptions = command.optsWithGlobals<GlobalOptions>();
    if (cmdOptions.format !== 'table' && cmdOptions.format !== 'json' && cmdOptions.format !== 'markdown') {
      emit({
        exitCode: 1,
        stdout: '',
        stderr: `Invalid --format '${cmdOptions.format}'. Expected one of: table, json, markdown.\n`,
      });
      return;
    }
    const format: ReportFormat = cmdOptions.format;
    emit(runReport(process.cwd(), { json: globalOptions.json, format }));
  });

program.exitOverride();

try {
  await program.parseAsync(process.argv);
} catch (error) {
  const commanderError = error as { code?: string; exitCode?: number };
  if (commanderError.code === 'commander.helpDisplayed' || commanderError.code === 'commander.version') {
    process.exitCode = 0;
  } else {
    process.exitCode = typeof commanderError.exitCode === 'number' ? commanderError.exitCode : 1;
  }
}
