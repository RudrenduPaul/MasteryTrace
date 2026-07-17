#!/usr/bin/env python3
"""
Console entry point: `masterytrace <command> [options]`, installed via the
`masterytrace` console-script defined in python/pyproject.toml. Ported
from src/cli/index.ts (which uses `commander`); this port uses the stdlib
`argparse` to avoid a CLI-framework dependency, matching the flags,
defaults, subcommands, and exit-code contract of the npm CLI's `--help`
output.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List

from .. import __version__
from .commands.init import InitOptions, run_init
from .commands.record import RecordOptions, run_record
from .commands.report import ReportOptions, run_report
from .commands.score import ScoreOptions, run_score
from .format import fail
from .types import CommandResult

_MODELS = ("bkt", "irt", "both")
_FORMATS = ("table", "json", "markdown")


def _emit(result: CommandResult) -> int:
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="masterytrace",
        description=(
            "Mastery Measurement API/CLI. Fits Bayesian Knowledge Tracing (BKT) and "
            "2-parameter logistic Item Response Theory (IRT) models to learner "
            "response logs and reports per-learner, per-skill mastery estimates."
        ),
    )
    parser.add_argument("--version", action="version", version=f"masterytrace-cli {__version__}")
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="force machine-readable JSON output on stdout instead of human-formatted text",
    )

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init",
        help="Scaffold a sample events.json and a default masterytrace.config.json in the current directory",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="overwrite events.json/masterytrace.config.json if they already exist",
    )

    record_parser = subparsers.add_parser(
        "record",
        help="Validate and load an event log (JSON or CSV) and store it to .masterytrace/events.json",
    )
    record_parser.add_argument(
        "path",
        help="path to a JSON (array of response events) or CSV (learner_id,skill_id,correct,timestamp) event log",
    )

    score_parser = subparsers.add_parser(
        "score",
        help="Fit and score the stored event log and write results to .masterytrace/scores.json",
    )
    score_parser.add_argument(
        "--model", default="both", help="which model(s) to run: bkt, irt, or both"
    )

    report_parser = subparsers.add_parser(
        "report",
        help="Read .masterytrace/scores.json and print a per-learner, per-skill mastery table",
    )
    report_parser.add_argument(
        "--format", default="table", help="output format: table, json, or markdown"
    )

    return parser


def run_cli(argv: List[str]) -> int:
    """
    `argv` follows the sys.argv convention: argv[0] is the program name,
    the real arguments start at argv[1]. Returns the process exit code
    (0 success, 1 general/usage error, 2 validation error).

    argparse's `--help`/`--version` actions call `parser.exit()` directly
    (raising SystemExit) rather than returning normally -- that is caught
    here and turned into a normal return, so `run_cli` always returns an
    int and never raises, matching the TS CLI's `program.exitOverride()`
    behavior (commander.helpDisplayed/commander.version both map to exit
    code 0) and letting command handlers be tested as plain functions.

    `--json` is a *global* flag that must work whether it appears before
    or after the subcommand (`masterytrace --json record x` and
    `masterytrace record x --json` both need to force JSON output, same
    as the npm CLI's commander-based global option). Registering the same
    `--json` action on both the main parser and every subparser does not
    reliably compose in argparse (a subparser's own default can overwrite
    a value already set by the main parser's parsing pass), so instead
    `--json` is detected directly from the raw argument list and stripped
    out before argparse ever sees it.
    """
    rest = list(argv[1:])
    as_json = "--json" in rest
    while "--json" in rest:
        rest.remove("--json")

    parser = build_parser()
    try:
        args = parser.parse_args(rest)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 0

    if args.command == "init":
        return _emit(run_init(os.getcwd(), InitOptions(json=as_json, force=args.force)))

    if args.command == "record":
        return _emit(run_record(os.getcwd(), args.path, RecordOptions(json=as_json)))

    if args.command == "score":
        if args.model not in _MODELS:
            return _emit(
                fail(
                    1,
                    as_json,
                    {"error": f"Invalid --model '{args.model}'. Expected one of: bkt, irt, both."},
                    f"Invalid --model '{args.model}'. Expected one of: bkt, irt, both.\n",
                )
            )
        return _emit(run_score(os.getcwd(), ScoreOptions(json=as_json, model=args.model)))

    if args.command == "report":
        if args.format not in _FORMATS:
            return _emit(
                fail(
                    1,
                    as_json,
                    {"error": f"Invalid --format '{args.format}'. Expected one of: table, json, markdown."},
                    f"Invalid --format '{args.format}'. Expected one of: table, json, markdown.\n",
                )
            )
        return _emit(run_report(os.getcwd(), ReportOptions(json=as_json, format=args.format)))

    parser.print_help()
    return 0


def main() -> None:
    try:
        code = run_cli(sys.argv)
    except SystemExit:
        raise
    except Exception as error:  # noqa: BLE001 -- top-level crash guard, mirrors src/cli/index.ts's catch-all
        sys.stderr.write(f"Error: {error}\n")
        sys.exit(1)
    else:
        sys.exit(code)


if __name__ == "__main__":
    main()
