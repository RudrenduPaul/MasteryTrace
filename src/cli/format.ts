import type { CommandResult, ExitCode } from './types.js';

/** Builds a successful CommandResult, choosing JSON or human text output. */
export function ok(json: boolean, jsonPayload: unknown, text: string): CommandResult {
  return { exitCode: 0, stdout: json ? `${JSON.stringify(jsonPayload)}\n` : text };
}

/** Builds a failing CommandResult (exit code 1 or 2), choosing JSON or human text output. */
export function fail(
  exitCode: Exclude<ExitCode, 0>,
  json: boolean,
  jsonPayload: unknown,
  text: string,
): CommandResult {
  if (json) {
    return { exitCode, stdout: `${JSON.stringify(jsonPayload)}\n` };
  }
  return { exitCode, stdout: '', stderr: text };
}
