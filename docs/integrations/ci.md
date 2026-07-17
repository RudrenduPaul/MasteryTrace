# CI integration

MasteryTrace is meant to run as a step in a pipeline: record a batch of
learner response events, score them, and hand the report to whatever
downstream system (dashboard, alerting, another agent) consumes mastery
data.

**Note**: the `pip install masterytrace-cli` steps below reflect the
package's PyPI publish target and will work once that publish completes
(see the root README's install section for current status). Until then,
replace that step with an install from source
(`pip install "git+https://github.com/RudrenduPaul/MasteryTrace.git#subdirectory=python"`).

## GitHub Actions -- Python CLI

```yaml
name: MasteryTrace scoring
on:
  push:
    paths:
      - 'data/events.json'

jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install masterytrace-cli
      - run: masterytrace record data/events.json
      - run: masterytrace score --model both
      - run: masterytrace report --format json > mastery-report.json
      - uses: actions/upload-artifact@v4
        with:
          name: mastery-report
          path: mastery-report.json
```

Exit codes let the job fail cleanly on bad input: `masterytrace record`
and `masterytrace score` both exit `2` if the event log fails validation,
and `1` on a general/usage error (e.g. a missing file), so a malformed
data push fails the workflow instead of silently producing an empty or
wrong report.

## GitHub Actions -- npm CLI

The npm package is not yet published (see the root README), so there is
no `npx masterytrace-cli` step to document yet. Once published, the
equivalent pipeline replaces the three Python-specific steps above with
`npx masterytrace-cli record/score/report` and drops the `setup-python`
step in favor of `actions/setup-node`.

## Agent-native usage

Every command supports a global `--json` flag that forces
machine-readable JSON on stdout regardless of the human-format default,
and the CLI's exit codes are a documented contract (`0`/`1`/`2`), not an
implementation detail -- both are meant for a script or an AI agent to
call this CLI as a subprocess and parse the result programmatically,
without scraping human-formatted text:

```bash
masterytrace --json score --model both
# {"model": "both", "eventCount": 58, "storedAt": "/path/.masterytrace/scores.json"}
```

Or skip the subprocess entirely and call the library in-process (Python):

```python
from masterytrace import run_scoring, parse_response_events

events = parse_response_events(my_event_rows)
result = run_scoring(events, "both")
```
