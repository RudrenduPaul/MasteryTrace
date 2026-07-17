# Getting started

MasteryTrace turns a log of learner response events into per-learner,
per-skill mastery scores, using Bayesian Knowledge Tracing (BKT) and Item
Response Theory (IRT), instead of a raw percent-correct. It ships as two
independent, equally first-class packages: an npm package
(`masterytrace-cli`, TypeScript) and a PyPI package (`masterytrace-cli`,
Python). Pick whichever fits your toolchain.

## Install

**pip (Python CLI + library):** publishing as `masterytrace-cli` on PyPI
is in progress (the first attempt hit PyPI's account-level new-project
rate limit, a platform-side throttle unrelated to this code). Once live:

```bash
pip install masterytrace-cli
```

Until then, install from source:

```bash
git clone https://github.com/RudrenduPaul/MasteryTrace.git
cd MasteryTrace/python
pip install -e .
```

**npm (JS/TS CLI + library):** the npm package is not yet published to
the npm registry -- that is a deliberate decision by the maintainer,
unrelated to the code's readiness (the TypeScript source passes CI and
builds cleanly). Until it is published, clone the repo and run the
TypeScript CLI from source (`npm install && npm run build && node
dist/cli/index.js`).

## Your first run

Both packages expose the same four subcommands: `init`, `record`,
`score`, `report`.

```bash
masterytrace init
masterytrace record events.json
masterytrace score
masterytrace report
```

Real output (Python CLI, run against the bundled sample data):

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
learner-brook  fractions              bkt    posterior_mastery_probability  0.0612   6
learner-cyrus  reading-comprehension  bkt    posterior_mastery_probability  0.9947   7
...
```

`init` scaffolds a sample `events.json` (3 learners, 3 skills, 6-7
responses each) and a default `masterytrace.config.json` so you have
something to score immediately. Point `record` at your own event log
once you have one.

## Using your own data

An event log is a JSON array of `{learnerId, skillId, correct,
timestamp}` objects (Python's `parse_response_events` and the CLI both
use this camelCase key convention, shared with the npm CLI's event-log
format), or a CSV with header `learner_id,skill_id,correct,timestamp`.
`timestamp` must be ISO 8601; `correct` is a boolean (JSON) or
`true`/`false`/`1`/`0` (CSV) -- any other value in a CSV `correct` cell
is rejected as a validation error rather than silently treated as false.
Event log files over 100 MB are rejected up front.

```bash
masterytrace record my-events.json
# or
masterytrace record my-events.csv
```

`record` always replaces any previously stored event log -- there is no
append/merge mode in v0.1.

## Using the library instead of the CLI

**Python:**

```python
from masterytrace import run_scoring, parse_response_events

events = parse_response_events([
    {"learnerId": "l1", "skillId": "fractions", "correct": True, "timestamp": "2026-01-01T00:00:00Z"},
    {"learnerId": "l1", "skillId": "fractions", "correct": False, "timestamp": "2026-01-02T00:00:00Z"},
])

result = run_scoring(events, "both")
for report in result.reports:
    print(report.model, report.learners)
```

**TypeScript:**

```ts
import { runScoring, parseResponseEvents } from 'masterytrace-cli';

const events = parseResponseEvents([
  { learnerId: 'l1', skillId: 'fractions', correct: true, timestamp: '2026-01-01T00:00:00Z' },
]);
const { reports } = runScoring(events, 'both');
```

## Next steps

- [concepts.md](./concepts.md) -- what BKT and IRT actually model, how
  the forward recursion and gradient-ascent fits work, and how to read
  the two different mastery metrics they produce.
- [integrations/ci.md](./integrations/ci.md) -- running MasteryTrace as
  a CI step (Python CLI).
- The [project README](../README.md) for the full library API reference,
  benchmark numbers, and tool comparison.
- The [python/README.md](../python/README.md) for Python-specific
  library usage and the deliberate snake_case/camelCase naming
  divergence between the two distributions.
