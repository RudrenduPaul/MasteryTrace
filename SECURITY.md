# Security Policy

MasteryTrace is a statistics library, not a sandbox or a security tool:
it reads a learner response event log (JSON or CSV) and fits two
psychometric models to it. The threat model is narrower than a scanner
or an interpreter, but still real -- an event log can come from an
upstream system, a file upload, or another agent, so it should be
treated as data the code processes carefully rather than data it
implicitly trusts.

## Supported versions

| Package | Version | Supported |
| --- | --- | --- |
| `masterytrace-cli` (npm) | not yet published | N/A |
| `masterytrace-cli` (PyPI) | 0.1.x | Yes |

The Python distribution is pre-1.0 and under active development.
Security fixes land on the latest `0.1.x` release; there is no older
supported line to backport to yet. The npm distribution is not currently
published to the npm registry (a deliberate maintainer decision, not a
readiness gap in the TypeScript source itself), so it has no installable
version to track here yet.

## What this project actually does with event-log data

Verified directly in the Python source as part of this release's security
review (`python/src/masterytrace/`):

- Event logs are only ever parsed as JSON (`json.loads`) or the
  project's own hand-rolled CSV parser, then checked against a fixed
  field schema (`learnerId`/`skillId`/`correct`/`timestamp`). No
  `eval`, `exec`, dynamic `import`, or `compile` of anything read from an
  event log, anywhere in the codebase.
- No `pickle`, `marshal`, or other unsafe deserialization. State files
  (`.masterytrace/events.json`, `.masterytrace/scores.json`) are plain
  JSON.
- No subprocess/shell invocation and no network calls anywhere in the
  library or CLI.
- The generic adapter (`adapters/generic_adapter.py`) refuses to read a
  symlinked path (`os.lstat`, never resolved through the link) and
  refuses any file over 100 MB, both checked before the file is read
  into memory.

## Known limitation: IRT fit time on very large event logs

The IRT model's joint gradient-ascent fit is implemented as plain Python
loops (a deliberate choice, mirroring the TypeScript original's own
dependency-free `Float64Array` implementation rather than introducing a
numpy dependency -- see `python/README.md`). Measured directly on this
release: fitting 500 iterations against 100,000 events (100 learners x 50
skills x 20 responses) takes about 14 seconds on a single core. That
scales roughly linearly with event count, so a maximal ~100 MB event log
(on the order of 1-1.5 million events, near the adapter's documented size
cap) could take several minutes to fit. This is a genuine, disclosed
resource-consumption consideration for `masterytrace score --model
irt`/`both` run against an untrusted, maximally sized event log -- not a
crash or memory-safety issue, but a real CPU-time cost. **Not fixed in
v0.1**: no request-level fit-time limit or iteration cap is enforced by
the CLI today. If you run this CLI or library against event logs from an
untrusted source in an automated pipeline, consider capping `iterations`
in `masterytrace.config.json` or enforcing your own wall-clock timeout
around the `score`/`fit` call. Tracked as a v0.2 candidate (either a
configurable hard cap or a lower default iteration count for large
inputs), not shipped silently as solved.

## What counts as in scope

- Any code path where content read from an *event log* (file contents,
  learner/skill id strings, CSV cells) is executed, evaluated, or
  dynamically imported, rather than only parsed and validated.
- A crafted event log that bypasses the documented 100 MB size guard or
  the symlink refusal in `generic_adapter.load()`.
- A crafted event log that causes unbounded memory growth (as opposed to
  the disclosed, bounded-but-slow IRT fit time above).
- Any dependency-supply-chain issue: this package currently ships with
  **zero third-party runtime dependencies** (only the Python standard
  library), so the practical surface here is the `dev` extras
  (`pytest`, `build`, `twine`) never being ambient at runtime.

## What is out of scope

- The IRT fit-time characteristic documented above, unless you find a
  way to make it materially worse than linear-in-event-count (e.g. an
  input that causes non-linear blowup) -- that would be in scope.
- Numerical edge cases in the fitted model output itself (e.g. an
  extreme-but-valid dataset producing a mastery estimate you consider
  implausible) -- open a normal issue for those; they are modeling
  questions, not vulnerabilities.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Report it privately via
[GitHub Security Advisories](https://github.com/RudrenduPaul/MasteryTrace/security/advisories/new)
for this repository. Include:

- Which distribution is affected (npm source, PyPI package, or both).
- A minimal reproduction: the event-log content (or a description of its
  shape) and the command/library call that triggers the issue.
- What you expected MasteryTrace to do, and what it actually did.
- Your assessment of impact.

## Response

We aim to acknowledge a report within 5 business days and to have a fix
or a mitigation plan within 30 days for a confirmed, in-scope
vulnerability. Credit is given in the release notes unless you ask to
remain anonymous.
