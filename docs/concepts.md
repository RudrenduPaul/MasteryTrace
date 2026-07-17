# Concepts

MasteryTrace fits two independent psychometric models to the same event
log and reports both. This page explains what each one actually models,
the exact update rules, and how to read the numbers they produce.

## The data model

Every model operates on the same unit: a `ResponseEvent`, one attempt by
one learner at one skill, scored correct/incorrect, at a point in time.

```
{ learnerId, skillId, correct, timestamp }
```

There is no other required structure -- no course hierarchy, no item
bank, no explicit difficulty labels. Both BKT and IRT derive everything
they need (parameters, ability estimates) from the pattern of
correct/incorrect responses across learners and skills.

## Bayesian Knowledge Tracing (BKT)

BKT models one learner's mastery of one skill as a hidden binary state
("knows it" / "does not know it yet") and updates a probability of
"knows it" after every response. Four parameters govern the model, all
per skill:

| Parameter | Meaning |
| --- | --- |
| `p_init` | Prior probability the learner already knows the skill before any evidence. |
| `p_transit` | Probability of learning the skill between one attempt and the next. |
| `p_slip` | Probability of an incorrect response despite knowing the skill. |
| `p_guess` | Probability of a correct response despite not knowing the skill. |

For each response, in chronological order, the forward recursion first
updates the belief given the observed outcome (Bayes' rule), then
advances it for possible learning before the next attempt:

```
after correct:   P(know | obs) = P(know) * (1 - p_slip) / [P(know) * (1 - p_slip) + (1 - P(know)) * p_guess]
after incorrect: P(know | obs) = P(know) * p_slip       / [P(know) * p_slip       + (1 - P(know)) * (1 - p_guess)]
P(know)_next = P(know | obs) + (1 - P(know | obs)) * p_transit
```

The final posterior after the last observed response is that learner's
`posterior_mastery_probability` for that skill -- the number
`masterytrace report` prints for the `bkt` model.

### Fixed defaults vs. fitting from your data

By default every skill uses the textbook parameters `p_init=0.4,
p_transit=0.3, p_slip=0.1, p_guess=0.2`. Set `"bkt": {"fit": true}` in
`masterytrace.config.json` to instead fit each skill's four parameters
from your own data, via a coarse grid search (7 x 7 x 5 x 5 = 1,225
candidate combinations per skill) that minimizes the total squared error
between the model's pre-update predicted-correct probability and the
actual observed outcome at every response. This is intentionally a
simple, dependency-free fitting routine, not a full EM/Baum-Welch
implementation -- good enough to noticeably improve on the textbook
defaults for a given dataset, not a claim of maximum-likelihood
optimality.

You can also set fixed overrides per skill (`skillParams` /
`skill_params` in the config, keyed by `skillId`), which take priority
over both the fit and the defaults.

## Item Response Theory (2PL IRT)

IRT models one continuous learner ability (`theta`) per learner, and
treats every distinct `skillId` as an "item" with two parameters:
discrimination (`a`, how sharply the item separates high- and
low-ability learners) and difficulty (`b`, on the same scale as `theta`).
This is the **2-parameter logistic (2PL)** model -- the probability of a
correct response is:

```
P(correct) = sigmoid(a * (theta - b))
```

MasteryTrace fits `theta`, `a`, and `b` jointly by batch gradient ascent
on the log-likelihood (joint maximum-likelihood estimation, JMLE), with a
small L2 penalty (default strength 0.01) pulling `theta`/`b` toward 0 and
`a` toward 1. That penalty is what keeps the fit finite for a learner or
skill with an all-correct or all-incorrect record, where the
unregularized likelihood would otherwise be maximized at infinity.
Defaults: 500 iterations, learning rate 0.5.

### Why theta gets re-centered every iteration

The 2PL model is only identified up to a shift and scale of `theta`:
shifting `theta` and `b` by the same constant, or scaling `theta`/`b` by
some factor `s` while dividing `a` by `s`, leaves every predicted
probability exactly unchanged. Without fixing this "gauge freedom," the
fit has infinitely many equally valid solutions. MasteryTrace pins down a
single solution the standard way: after every gradient-ascent iteration,
`theta` is re-centered to mean 0 and re-scaled to standard deviation 1,
with the matching inverse transform applied to `b` and `a`.

The practical consequence: `theta` is a *relative* ability estimate
(z-score-like, mean 0 across the learners in your dataset), not an
absolute score on a fixed scale. Comparing `theta` across two different
`masterytrace score` runs on different datasets is not meaningful unless
both runs include the same learner population.

### Reading the output

`masterytrace report` prints `ability_theta` as the `irt` model's value
per learner per skill (note: `theta` is per-learner, so the same value
repeats across a learner's skills unless that learner's response pattern
differs enough per skill to matter -- see the worked recovery test
below). The full report's `details` (via `--json` or `--format json`)
additionally carries `item_discrimination`, `item_difficulty`, and
`predicted_probability_correct` for that specific learner/skill pair.

## Verifying the math: a synthetic recovery check

Both models are unit-tested against something stronger than "the output
looks plausible": a synthetic dataset built from known ground-truth
parameters, checking the fitted values land close to the true ones.

- **BKT**: `run_forward_recursion` is tested against a fully
  hand-computed worked example (exact fractions, not floating-point
  approximations) for the sequence `[correct, incorrect, correct,
  correct, incorrect]` under the default parameters.
- **IRT**: the model is fit against 4,000 synthetic responses (5
  learners x 4 skills x 200 repeats) generated from known `theta`/`a`/`b`
  values, then checked to recover those values (through the same gauge
  normalization described above) within 0.3 absolute error.

Both tests are part of the shipped test suite (`test/bkt.test.ts` and
`test/irt.test.ts` for TypeScript, `tests/test_bkt.py` and
`tests/test_irt.py` for Python) -- this is the kind of test that actually
catches a subtly wrong port of statistical code, not just a smoke test.

## Exit codes

Every CLI command shares one exit-code contract, so a script or agent
invoking MasteryTrace can branch on the result without parsing text:
`0` success, `1` general/usage error (bad flag, missing file), `2`
validation error (the event log itself is malformed).
