# Contributing to MasteryTrace

MasteryTrace ships two independently maintained, equally first-class
distributions of the same mastery-scoring library: an npm package
(`masterytrace-cli`, TypeScript, repo root -- `npm install -g
masterytrace-cli`) and a PyPI package (`masterytrace-cli`, Python,
`python/` -- `pip install masterytrace-cli`). Both implement the same two models (BKT, 2PL IRT) and the
same CLI contract, and are expected to produce the same numbers against
the same input data. Please read this whole file before opening a PR --
which section applies depends on which codebase you're touching.

## Ground rules

- Every change lands with tests. Neither test suite is optional
  scaffolding -- both are the mechanism that keeps the two
  implementations in parity.
- A change to either model's math (BKT's forward recursion or grid
  search, IRT's gradient-ascent fit or gauge-fixing) must be made in
  **both** `src/models/` (TypeScript) and `python/src/masterytrace/models/`
  (Python), with equivalent test coverage added to both suites. A model
  change that only exists in one language is a silent behavioral gap
  between the two CLIs -- avoid it.
- CLI flags, exit codes, and output shape should read identically between
  the two CLIs wherever the underlying behavior is the same. Field-name
  casing (`camelCase` in TypeScript output, `snake_case` in Python
  output) is the one intentional, documented divergence -- see
  `python/README.md`.
- No `eval`/`exec` of anything read from an event log, in either
  codebase. Event data is parsed as JSON/CSV and validated against a
  fixed schema; it should never be interpreted as code.

## Working on the TypeScript package (repo root)

```bash
npm install
npm run build
npm test
npm run typecheck
```

- Source lives under `src/`; the response-event schema and engine under
  `src/core/`; the two models under `src/models/`; the CLI under
  `src/cli/`.
- Tests use `vitest` (`test/**/*.test.ts`, one file per module, plus an
  end-to-end suite that runs against the built `dist/cli/index.js`
  binary).
- `npm run build` compiles to `dist/`, which is what the `bin` entry
  (`masterytrace`) and the library export both resolve to.

## Working on the Python package (`python/`)

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

- Source lives under `python/src/masterytrace/`, laid out to mirror the
  TypeScript module structure 1:1 (`core/`, `models/`, `adapters/`,
  `data/`, `cli/`) so a change in one codebase has an obvious counterpart
  to check in the other.
- Tests use `pytest` (`python/tests/test_*.py`), including an in-process
  CLI end-to-end suite covering the same `init -> record -> score ->
  report` pipeline and exit-code contract the TypeScript suite's
  subprocess-based e2e test covers.
- Build and verify a real install before opening a PR that touches
  packaging (build the venv *outside* `python/` so it never gets bundled
  into the sdist):
  ```bash
  python3 -m venv /tmp/mt-verify
  /tmp/mt-verify/bin/pip install build
  /tmp/mt-verify/bin/python3 -m build python --outdir python/dist
  /tmp/mt-verify/bin/pip install python/dist/*.whl
  /tmp/mt-verify/bin/masterytrace init && /tmp/mt-verify/bin/masterytrace record events.json && /tmp/mt-verify/bin/masterytrace score && /tmp/mt-verify/bin/masterytrace report
  ```

## Changing or adding a model

1. Decide which model (BKT or IRT) and whether the change affects the
   default parameters, the update/fit rule, or just the CLI/report
   surface around it.
2. Implement the change in `src/models/<model>.ts` (TypeScript) and the
   matching `python/src/masterytrace/models/<model>.py` (Python), keeping
   the update rule and any constants (grid values, default learning
   rate, etc.) numerically identical unless the PR explicitly documents
   an intentional divergence and why.
3. Add or update tests in both suites. If the change affects fitted
   values, prefer a test that checks against a hand-computed or
   known-ground-truth value (see the existing BKT worked-example test and
   IRT synthetic-recovery test) over a vague "value changed" assertion.
4. Run both test suites and confirm the CLI's real output
   (`masterytrace score && masterytrace report`) against a shared sample
   dataset produces the same numbers from both distributions.

## Reporting a security issue

Do not open a public issue for a security vulnerability. See
[SECURITY.md](./SECURITY.md).

## License

By contributing, you agree your contribution is licensed under the same
MIT License that covers the rest of this repository (see
[LICENSE](./LICENSE)).
