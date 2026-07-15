/**
 * Every CLI command handler returns this shape instead of writing to
 * stdout/exiting directly, so integration tests can invoke handlers as
 * plain functions and assert on their output/exit code without spawning a
 * subprocess.
 *
 * Exit code contract (required so an agent invoking this CLI programmatically
 * can rely on it): 0 = success, 1 = general/usage error, 2 = validation error
 * (bad event data).
 */
export type ExitCode = 0 | 1 | 2;

export interface CommandResult {
  exitCode: ExitCode;
  stdout: string;
  stderr?: string;
}
