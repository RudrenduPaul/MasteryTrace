# Python examples

Each numbered subdirectory is a real, runnable script against the actual
`masterytrace` Python library (`from masterytrace import ...`), not
pseudocode.

Install the package first (editable install from this checkout, or `pip
install masterytrace-cli` from PyPI both work identically):

```bash
cd python
pip install -e .
```

Then run any example directly:

```bash
python3 examples/01-basic-bkt-fit/fit_bkt.py
python3 examples/02-irt-scoring/score_irt.py
python3 examples/03-ci-gate/gate.py
```

| Example | What it demonstrates |
| --- | --- |
| [01-basic-bkt-fit](./01-basic-bkt-fit/) | Fitting a BKT model to a small synthetic response log, printing each learner's posterior mastery trajectory per skill. |
| [02-irt-scoring](./02-irt-scoring/) | Fitting a 2PL IRT model to a response log spanning multiple skills of different difficulty, and reading back each learner's ability estimate and each skill's discrimination/difficulty. |
| [03-ci-gate](./03-ci-gate/) | Using the library as a CI-style gate: load an event log from disk, score it, and exit non-zero if any learner's mastery on a required skill falls below a threshold -- suitable to drop into a CI script directly. |
