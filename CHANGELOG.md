# Changelog

All notable changes to MasteryTrace are documented in this file. This
changelog covers both distributions -- the npm package (`masterytrace-cli`,
JS/TS, not yet published) and the PyPI package (`masterytrace-cli`,
Python, publish in progress -- see `python/README.md`'s "PyPI status"
note) -- since they implement the same models and CLI contract; entries
note which distribution they apply to.

## [Python 0.1.0] - 2026-07-17

Initial release of the Python port, built, tested (75 pytest tests), and
verified end to end from a real wheel install. Publishing it to PyPI as
`masterytrace-cli` is in progress: the first publish attempt hit PyPI's
account-level new-project rate limit (`429 Too many new projects
created`), a platform-side anti-abuse throttle unrelated to this code;
`pip install masterytrace-cli` will work once that clears. A genuine,
independent port of the npm package's TypeScript source -- same BKT
forward-recursion and grid-search fitting, same 2PL IRT joint
gradient-ascent fit with gauge-fixing, same CLI command/flag/exit-code
contract. See `python/README.md` for Python-specific usage.

### Added

- `masterytrace <init|record|score|report>` CLI (console script
  `masterytrace`, package `masterytrace`) with the same subcommands and
  flags as the npm CLI: `--json` (global), `init --force`, `score
  --model <bkt|irt|both>`, `report --format <table|json|markdown>`.
- Programmatic library API: `from masterytrace import run_scoring,
  parse_response_events, BktModel, IrtModel, ...`, returning the same
  data shape as the npm package's exports (field names are `snake_case`
  in this port rather than `camelCase`, matching Python convention --
  see `python/README.md`'s naming-divergence note; the event-log JSON
  wire format itself stays `camelCase` on both distributions, since that
  is the shared cross-distribution contract `parse_response_events`
  reads).
- `BktModel`: forward-recursion mastery updates and the coarse
  grid-search parameter-fitting routine, ported line-for-line from
  `src/models/bkt.ts`, including its exact default parameters and grid
  values.
- `IrtModel`: 2-parameter logistic joint MLE via batch gradient ascent
  with L2 regularization and per-iteration theta gauge-fixing, ported
  line-for-line from `src/models/irt.ts`.
- `generic_adapter`: JSON/CSV event-log loader with the same symlink
  refusal and 100 MB size guard as the TypeScript original.
- Full pytest suite (75 tests) ported from the TypeScript vitest suite,
  including the hand-computed BKT worked example and the synthetic
  IRT parameter-recovery check.
- No third-party runtime dependencies: both models' math is plain
  scalar/list arithmetic in this port, matching the TypeScript
  original's own dependency-free (`Float64Array` + plain loops)
  implementation.

## [0.1.0] - 2026-07-15 (TypeScript)

Initial release of the TypeScript CLI and library (not yet published to
npm; see the root README's install section for the maintainer's stated
reason). `masterytrace <init|record|score|report>` CLI plus a
programmatic `runScoring`/`BktModel`/`IrtModel` library export, backed by
a full vitest suite including the same hand-computed BKT worked example
and synthetic IRT recovery check the Python port's suite mirrors.
