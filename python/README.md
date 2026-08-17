<!-- mcp-name: io.github.RudrenduPaul/masterytrace -->

# masterytrace-cli (Python)

Mastery Measurement API and CLI: fits Bayesian Knowledge Tracing (BKT) and
Item Response Theory (2-parameter logistic IRT) models to learner response
logs and reports per-learner, per-skill mastery estimates.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/RudrenduPaul/MasteryTrace/blob/main/LICENSE)
[![CI](https://github.com/RudrenduPaul/MasteryTrace/actions/workflows/ci.yml/badge.svg)](https://github.com/RudrenduPaul/MasteryTrace/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/masterytrace-cli.svg)](https://pypi.org/project/masterytrace-cli/)
[![npm version](https://img.shields.io/npm/v/masterytrace-cli.svg)](https://www.npmjs.com/package/masterytrace-cli)

**PyPI status**: `masterytrace-cli` is published and live on PyPI --
`pip install masterytrace-cli` works today.

## Why this exists

Most tutoring products and AI tutoring agents track raw percent-correct,
which conflates a lucky guess with real mastery and never says how
confident the estimate actually is. BKT and IRT are the two psychometric
models built to fix that, but they live almost entirely as Python-only
libraries with no CLI a non-Python tool (or an agent shelling out to a
subprocess) can call directly. MasteryTrace is a CLI and library that
turns a log of `{learnerId, skillId, correct, timestamp}` response events
into a posterior mastery probability (BKT) and an ability estimate (IRT)
per learner per skill. This package is the Python distribution -- a
genuine, independent port of the npm package's TypeScript source, not a
wrapper around a Node binary.

## Install

```bash
pip install masterytrace-cli
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv add masterytrace-cli
```

To install from source instead (e.g. for local development):

```bash
git clone https://github.com/RudrenduPaul/MasteryTrace.git
cd MasteryTrace/python
pip install -e .
```

This installs a `masterytrace` console script and the `masterytrace`
importable package. No runtime dependencies beyond the Python standard
library -- the forward-recursion and gradient-ascent math in this port
are both plain scalar/list arithmetic, exactly what the TypeScript
original does with `Float64Array` and plain numbers, so a numpy/scipy
dependency would not simplify anything here.

**npm side:** the complementary JS/TS distribution (`masterytrace-cli` on
npm) is also published -- `npm install -g masterytrace-cli`. This PyPI
package is an independent port and installs and runs on its own either
way.

## Quickstart

```bash
masterytrace init
masterytrace record events.json
masterytrace score
masterytrace report
```

`init` scaffolds a sample `events.json` (3 learners, 3 skills, several
responses each) and a default `masterytrace.config.json` in the current
directory. Real output from that flow:

```
$ masterytrace init
Created: events.json, masterytrace.config.json
Next: run 'masterytrace record events.json' to load it, then 'masterytrace score'.

$ masterytrace record events.json
Stored 58 event(s) to /path/to/.masterytrace/events.json
(record replaces any previously stored event log; see --help for details.)

$ masterytrace score
Scored 58 event(s) with model(s): both
Wrote /path/to/.masterytrace/scores.json

$ masterytrace report
learner        skill                  model  metric                         value    responses
-------------  ---------------------  -----  -----------------------------  -------  ---------
learner-ada    fractions              bkt    posterior_mastery_probability  0.9994   6
learner-ada    fractions              irt    ability_theta                  0.7349   6
learner-ada    linear-equations       bkt    posterior_mastery_probability  0.9746   7
learner-brook  fractions              bkt    posterior_mastery_probability  0.0612   6
learner-cyrus  reading-comprehension  bkt    posterior_mastery_probability  0.9947   7
...
```

`report` also takes `--format markdown` or `--format json`, and every
command accepts a global `--json` flag for machine-readable output on
stdout, with a real exit code contract (`0` success, `1` general/usage
error, `2` bad event data) so a script or agent invoking this CLI can
branch on the result without parsing text.

Your own event log is a JSON array of `{learnerId, skillId, correct,
timestamp}` objects, or a CSV with header
`learner_id,skill_id,correct,timestamp`. `timestamp` must be ISO 8601;
`correct` is a boolean (JSON) or `true`/`false`/`1`/`0` (CSV), and any
other value in a CSV `correct` cell is rejected as a validation error
rather than silently treated as false. Event log files over 100 MB are
rejected up front with a clear error.

## CLI command reference

| Command | Arguments | Options | Does |
| --- | --- | --- | --- |
| `masterytrace init` | | `--force` | Scaffolds a sample `events.json` and `masterytrace.config.json` in the current directory. Skips files that already exist unless `--force` is passed. |
| `masterytrace record <path>` | `<path>`: JSON or CSV event log | | Validates an event log and stores it to `.masterytrace/events.json`. Always replaces any previously stored log. |
| `masterytrace score` | | `--model <bkt\|irt\|both>` (default `both`) | Fits and scores the stored event log, writing the result to `.masterytrace/scores.json`. |
| `masterytrace report` | | `--format <table\|json\|markdown>` (default `table`) | Reads `.masterytrace/scores.json` and prints a per-learner, per-skill mastery table. |

Global option: `--json` forces machine-readable JSON on stdout for any
command, overriding `--format` on `report`.

Exit codes: `0` success, `1` general or usage error (bad flag, missing
file), `2` validation error (the event log itself is malformed).

## MCP Server

This package ships a Model Context Protocol (MCP) server, so an agent
(Claude Desktop, Claude Code, or any other MCP client) can invoke the CLI
directly instead of shelling out itself.

```bash
pip install "masterytrace-cli[mcp]"
```

Claude Desktop config example (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "masterytrace": {
      "command": "masterytrace-mcp"
    }
  }
}
```

The server exposes one tool, `run(args: list[str]) -> dict`, which shells
out to the installed `masterytrace` CLI with the given argument list and
returns its parsed output. Example call:
`run(["score", "--model", "bkt", "--json"])` fits a BKT model against the
stored event log and returns the parsed JSON mastery report.

## Library API

```python
from masterytrace import (
    # Event schema and validation
    ResponseEvent, parse_response_events, EventValidationError,

    # Engine: runs one or both models
    run_scoring, EngineConfig, EngineResult,

    # BKT
    BktModel, BKT_DEFAULT_PARAMS, run_forward_recursion, fit_skill_params_by_grid_search,
    BktParams, BktConfig, BktFittedModel,

    # IRT
    IrtModel, probability_correct,
    IrtItemParams, IrtLearnerResult, IrtConfig, IrtFittedModel,

    # Generic JSON/CSV event log adapter
    generic_adapter, parse_csv, GenericAdapter,
)

events = parse_response_events([
    {"learnerId": "l1", "skillId": "fractions", "correct": True, "timestamp": "2026-01-01T00:00:00Z"},
    {"learnerId": "l1", "skillId": "fractions", "correct": False, "timestamp": "2026-01-02T00:00:00Z"},
])

result = run_scoring(events, "both")
# result.reports[0].model == "bkt", result.reports[1].model == "irt"
# each learner's report.learners[i].skills[j].value is the mastery estimate
```

`BktModel` and `IrtModel` both implement the same `fit(events)` then
`score(fitted_model)` two-step interface, so the engine, and your own
code, can treat them interchangeably.

**A deliberate naming divergence from the npm package**: this Python
port's JSON output and dataclass field names are `snake_case`
(`learner_id`, `response_count`, `item_discrimination`) rather than the
npm CLI's `camelCase` (`learnerId`, `responseCount`,
`itemDiscrimination`), matching each language's own convention. The data
shape -- which fields exist and what they mean -- is identical.

## How BKT and IRT work

MasteryTrace implements two independent psychometric models. They answer
different questions and produce different kinds of numbers, so
`masterytrace score --model both` runs them side by side rather than
picking one.

### Bayesian Knowledge Tracing (BKT)

BKT models one learner's mastery of one skill as a hidden binary state
(knows it / does not know it yet) and updates a probability of "knows it"
after every response, using four parameters: `p_init` (prior probability
the learner already knows the skill), `p_transit` (probability of
learning the skill between one attempt and the next), `p_slip`
(probability of an incorrect answer despite knowing the skill), and
`p_guess` (probability of a correct answer despite not knowing the
skill). For each response, the forward recursion first updates the belief
given the observed outcome (Bayes' rule), then advances it for possible
learning before the next attempt:

```
after correct:   P(know | obs) = P(know) * (1 - p_slip) / [P(know) * (1 - p_slip) + (1 - P(know)) * p_guess]
after incorrect: P(know | obs) = P(know) * p_slip       / [P(know) * p_slip       + (1 - P(know)) * (1 - p_guess)]
P(know)_next = P(know | obs) + (1 - P(know | obs)) * p_transit
```

MasteryTrace runs this recursion per learner per skill, in chronological
order, and reports the final posterior as that learner's mastery
probability for that skill. If you set `"bkt": {"fit": true}` in
`masterytrace.config.json`, each skill's four parameters are fit from
your own data by a coarse grid search (7 x 7 x 5 x 5 candidate
combinations) that minimizes squared error between predicted and observed
correctness, instead of using the textbook defaults (`p_init=0.4,
p_transit=0.3, p_slip=0.1, p_guess=0.2`). This is the same coarse,
dependency-free grid search the TypeScript original implements -- not a
full EM/Baum-Welch fit -- ported line-for-line, including its parameter
grid values.

### Item Response Theory (2PL IRT)

IRT models one continuous learner ability (`theta`) per learner and two
parameters per skill treated as an "item": discrimination (`a`, how
sharply the item separates high- and low-ability learners) and difficulty
(`b`). The probability of a correct response under the 2-parameter
logistic model is:

```
P(correct) = sigmoid(a * (theta - b))
```

MasteryTrace fits all of these jointly by gradient ascent on the
log-likelihood (joint MLE), with a small L2 penalty pulling `theta`/`b`
toward 0 and `a` toward 1. That penalty is what keeps the fit finite for
a learner or skill with an all-correct or all-incorrect record, where the
unregularized likelihood would otherwise be maximized at infinity.
Because the 2PL model is only identified up to a shift and scale of
`theta` (shifting `theta` and `b` by the same constant, or scaling
`theta`/`b` while dividing `a` accordingly, leaves every predicted
probability unchanged), the fit re-centers `theta` to mean 0 and standard
deviation 1 after every iteration -- the standard way to pin down a
single solution. This port mirrors the TypeScript original's hand-rolled
batch gradient ascent line for line (same update rule, same per-iteration
gauge fix, same default 500 iterations / 0.5 learning rate / 0.01
regularization), rather than calling into an external optimizer -- there
is no scipy.optimize equivalent in play to port to, since the original
does not use one either.

### A real recovery check

`tests/test_irt.py` fits the model against a synthetic dataset built from
known ground-truth `theta`/`a`/`b` values (4,000 responses across 5
learners and 4 skills, same synthetic setup as the TypeScript suite's own
recovery test) and checks that the recovered parameters land close to the
true ones once put through the same gauge normalization, within the same
0.3 absolute-error tolerance the TypeScript test uses.

## Benchmark

Run locally against synthetic event logs (single core, in-process library
calls, no subprocess/CLI startup overhead):

| Dataset | Events | BKT fit+score | IRT fit+score (500 iterations) |
| --- | --- | --- | --- |
| Small | 10,000 (50 learners x 20 skills x 10 responses) | 0.05s | 2.86s |
| Large | 100,000 (100 learners x 50 skills x 20 responses) | 0.09s | 14.42s |

BKT with grid-search fitting (`"bkt": {"fit": true}`, a 1,225-combination
grid search per skill) on the 10,000-event dataset took 5.20s.

**Honest comparison with the TypeScript package**: the npm package's own
documented benchmark reports the 100,000-event IRT fit at 0.54s (as part
of a `--model both` subprocess run) -- roughly 27x faster than this
Python port's 14.42s for the same fit alone. This gap is expected and
disclosed, not a porting bug: IRT's gradient-ascent fit is a tight
numeric loop, and V8's JIT compiles that loop far more aggressively than
CPython's interpreter executes the equivalent Python loop. The fitted
*values* are what this port keeps faithful (see the recovery check
above, and the identical-to-4-decimal-places output in the Quickstart
section); wall-clock fit time on large datasets is not. See
[SECURITY.md](https://github.com/RudrenduPaul/MasteryTrace/blob/main/SECURITY.md)'s
"known limitation" section for what this means for very large,
untrusted event logs.

## CI integration

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
- run: pip install masterytrace-cli
- run: masterytrace init
- run: masterytrace record events.json
- run: masterytrace score --model both
- run: masterytrace report --format json > mastery-report.json
```

Full walkthrough in
[docs/integrations/ci.md](https://github.com/RudrenduPaul/MasteryTrace/blob/main/docs/integrations/ci.md).

## Security

MasteryTrace never `eval()`s or `exec()`s anything read from an event
log; event data is only ever parsed as JSON/CSV and pattern-matched
against the validation schema. The generic adapter refuses symlinked
paths and files over 100 MB before reading them, closing the two most
likely ways a maliciously crafted event-log path could cause unexpected
behavior. **Honest note**: this project does not currently publish SLSA
provenance, Sigstore signatures, or an SBOM, and has no OpenSSF Scorecard
badge set up -- none of that infrastructure exists yet for either
distribution, so it isn't claimed here. See
[SECURITY.md](https://github.com/RudrenduPaul/MasteryTrace/blob/main/SECURITY.md)
for the vulnerability disclosure process.

## Contributing

See [CONTRIBUTING.md](https://github.com/RudrenduPaul/MasteryTrace/blob/main/CONTRIBUTING.md)
for the full guide, covering both the TypeScript and Python codebases.

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT, see [LICENSE](https://github.com/RudrenduPaul/MasteryTrace/blob/main/LICENSE).
