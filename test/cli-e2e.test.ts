import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';

// This suite exercises the *built* CLI binary as a real subprocess, so the
// commander wiring in src/cli/index.ts (argument parsing, --help text,
// process exit codes) is covered end to end, not just the command handler
// functions it delegates to.
const CLI_PATH = join(import.meta.dirname, '..', 'dist', 'cli', 'index.js');

function runCli(cwd: string, args: string[]): { stdout: string; stderr: string; status: number } {
  try {
    const stdout = execFileSync('node', [CLI_PATH, ...args], { cwd, encoding: 'utf-8' });
    return { stdout, stderr: '', status: 0 };
  } catch (error) {
    const execError = error as { stdout?: string; stderr?: string; status?: number };
    return {
      stdout: execError.stdout ?? '',
      stderr: execError.stderr ?? '',
      status: execError.status ?? 1,
    };
  }
}

describe('masterytrace CLI (subprocess, built binary)', () => {
  let dir: string;

  beforeAll(() => {
    if (!existsSync(CLI_PATH)) {
      throw new Error(`Built CLI not found at ${CLI_PATH}. Run 'npm run build' before the test suite.`);
    }
  });

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'masterytrace-e2e-'));
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('prints help output listing all four subcommands', () => {
    const result = runCli(dir, ['--help']);
    expect(result.status).toBe(0);
    expect(result.stdout).toMatch(/init/);
    expect(result.stdout).toMatch(/record/);
    expect(result.stdout).toMatch(/score/);
    expect(result.stdout).toMatch(/report/);
  });

  it('runs the full init -> record -> score -> report pipeline with exit code 0 at each step', () => {
    expect(runCli(dir, ['init']).status).toBe(0);
    expect(runCli(dir, ['record', 'events.json']).status).toBe(0);
    expect(runCli(dir, ['score']).status).toBe(0);
    const report = runCli(dir, ['report']);
    expect(report.status).toBe(0);
    expect(report.stdout).toMatch(/learner/);
  });

  it('exits 1 when scoring before any event log has been recorded', () => {
    const result = runCli(dir, ['score']);
    expect(result.status).toBe(1);
  });

  it('exits 2 for a validation error via --json', () => {
    writeFileSync(join(dir, 'bad.json'), JSON.stringify([{ learnerId: '', skillId: 's', correct: true, timestamp: 'x' }]));
    const result = runCli(dir, ['--json', 'record', 'bad.json']);
    expect(result.status).toBe(2);
    expect(() => JSON.parse(result.stdout)).not.toThrow();
  });
});
