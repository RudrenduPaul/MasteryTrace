import { describe, expect, it } from 'vitest';
import {
  BKT_DEFAULT_PARAMS,
  BktModel,
  fitSkillParamsByGridSearch,
  runForwardRecursion,
  type BktParams,
} from '../src/models/bkt.js';
import type { ResponseEvent } from '../src/core/event-schema.js';

function event(learnerId: string, skillId: string, correct: boolean, timestamp: string): ResponseEvent {
  return { learnerId, skillId, correct, timestamp };
}

describe('runForwardRecursion (hand-computed worked example)', () => {
  // Worked by hand with p_init=0.4, p_transit=0.3, p_slip=0.1, p_guess=0.2
  // for the response sequence [correct, incorrect, correct, correct, incorrect].
  //
  // Step 0 (correct): prior L = 2/5.
  //   num = L*(1-slip)     = (2/5)*(9/10)               = 9/25   = 0.36
  //   den = num + (1-L)*guess = 9/25 + (3/5)*(1/5)       = 12/25  = 0.48
  //   post0 = num/den = (9/25)/(12/25) = 9/12 = 3/4      = 0.75
  //   next prior = post0 + (1-post0)*transit = 3/4 + (1/4)*(3/10) = 33/40 = 0.825
  //
  // Step 1 (incorrect): prior L = 33/40.
  //   num = L*slip           = (33/40)*(1/10)                  = 33/400
  //   den = num + (1-L)*(1-guess) = 33/400 + (7/40)*(4/5)      = 89/400
  //   post1 = (33/400)/(89/400) = 33/89                        = 0.3707865168...
  //   next prior = 33/89 + (56/89)*(3/10) = 249/445           = 0.5595505618...
  //
  // Step 2 (correct): prior L = 249/445.
  //   num = (249/445)*(9/10) = 2241/4450
  //   den = 2241/4450 + (196/445)*(1/5) = 2633/4450
  //   post2 = 2241/2633 = 0.8511203950...
  //   next prior = post2 + (1-post2)*0.3 = 11793/13165 = 0.8957842869...
  //
  // Step 3 (correct): prior L = 11793/13165.
  //   num = (11793/13165)*(9/10) = 106137/131650
  //   den = 106137/131650 + (1372/13165)*(1/5) = 108881/131650
  //   post3 = 106137/108881 = 0.9747981742...
  //   next prior = post3 + (1-post3)*0.3 = 534801/544405 = 0.9823593251...
  //
  // Step 4 (incorrect): prior L = 534801/544405.
  //   num = (534801/544405)*(1/10) = 534801/5444050
  //   den = 534801/5444050 + (9604/544405)*(4/5) = 611633/5444050
  //   post4 = 534801/611633 = 0.8743821867...
  const expectedPosteriors = [
    0.75,
    33 / 89,
    2241 / 2633,
    106137 / 108881,
    534801 / 611633,
  ];

  it('matches the hand-computed posteriors within floating point tolerance', () => {
    const posteriors = runForwardRecursion([true, false, true, true, false], BKT_DEFAULT_PARAMS);
    expect(posteriors).toHaveLength(5);
    posteriors.forEach((p, i) => {
      expect(p).toBeCloseTo(expectedPosteriors[i] as number, 10);
    });
  });

  it('starts from p_init as the implicit prior before any response', () => {
    // With zero responses, there is nothing to recur over.
    expect(runForwardRecursion([], BKT_DEFAULT_PARAMS)).toEqual([]);
  });

  it('handles a single response', () => {
    const posteriors = runForwardRecursion([true], BKT_DEFAULT_PARAMS);
    expect(posteriors).toHaveLength(1);
    expect(posteriors[0]).toBeCloseTo(0.75, 10);
  });

  it('increases mastery monotonically across an all-correct streak', () => {
    const posteriors = runForwardRecursion([true, true, true, true, true], BKT_DEFAULT_PARAMS);
    for (let i = 1; i < posteriors.length; i += 1) {
      expect(posteriors[i]).toBeGreaterThan(posteriors[i - 1] as number);
    }
    expect(posteriors[posteriors.length - 1]).toBeGreaterThan(0.99);
  });

  it('keeps mastery low (but non-zero, due to guessing) across an all-incorrect streak', () => {
    const posteriors = runForwardRecursion([false, false, false, false, false], BKT_DEFAULT_PARAMS);
    expect(posteriors[posteriors.length - 1]).toBeLessThan(0.2);
    for (const p of posteriors) {
      expect(p).toBeGreaterThan(0);
      expect(p).toBeLessThan(1);
    }
  });
});

describe('fitSkillParamsByGridSearch', () => {
  it('returns a BktParams object with all four fields in valid ranges', () => {
    const sequences = [
      [true, true, true, true, true],
      [true, true, false, true, true],
    ];
    const fitted = fitSkillParamsByGridSearch(sequences);
    const keys: (keyof BktParams)[] = ['pInit', 'pTransit', 'pSlip', 'pGuess'];
    for (const key of keys) {
      expect(fitted[key]).toBeGreaterThanOrEqual(0);
      expect(fitted[key]).toBeLessThanOrEqual(1);
    }
  });

  it('prefers a high pInit/pTransit combination for a learner who is correct from the start', () => {
    const sequences = [[true, true, true, true, true, true]];
    const fitted = fitSkillParamsByGridSearch(sequences);
    // An always-correct sequence is best explained by a high prior mastery.
    expect(fitted.pInit).toBeGreaterThanOrEqual(0.5);
  });
});

describe('BktModel', () => {
  it('implements the ScoringModel interface with name "bkt"', () => {
    const model = new BktModel();
    expect(model.name).toBe('bkt');
  });

  it('fits and scores an empty event log without error', () => {
    const model = new BktModel();
    const fitted = model.fit([]);
    const report = model.score(fitted);
    expect(report.model).toBe('bkt');
    expect(report.learners).toEqual([]);
  });

  it('groups results per learner and per skill, applying default params', () => {
    const events: ResponseEvent[] = [
      event('l1', 's1', true, '2026-01-01T00:00:00Z'),
      event('l1', 's1', false, '2026-01-02T00:00:00Z'),
      event('l1', 's2', true, '2026-01-01T00:00:00Z'),
      event('l2', 's1', true, '2026-01-01T00:00:00Z'),
    ];
    const model = new BktModel();
    const report = model.score(model.fit(events));

    expect(report.learners).toHaveLength(2);
    const l1 = report.learners.find((l) => l.learnerId === 'l1');
    expect(l1?.skills).toHaveLength(2);
    const l1s1 = l1?.skills.find((s) => s.skillId === 's1');
    expect(l1s1?.responseCount).toBe(2);
    expect(l1s1?.metric).toBe('posterior_mastery_probability');
    expect(l1s1?.value).toBeGreaterThan(0);
    expect(l1s1?.value).toBeLessThan(1);
  });

  it('processes events out of input order by chronological timestamp', () => {
    const outOfOrder: ResponseEvent[] = [
      event('l1', 's1', true, '2026-01-03T00:00:00Z'),
      event('l1', 's1', false, '2026-01-01T00:00:00Z'),
      event('l1', 's1', true, '2026-01-02T00:00:00Z'),
    ];
    const inOrder: ResponseEvent[] = [
      event('l1', 's1', false, '2026-01-01T00:00:00Z'),
      event('l1', 's1', true, '2026-01-02T00:00:00Z'),
      event('l1', 's1', true, '2026-01-03T00:00:00Z'),
    ];
    const model = new BktModel();
    const reportA = model.score(model.fit(outOfOrder));
    const reportB = model.score(model.fit(inOrder));
    expect(reportA.learners[0]?.skills[0]?.value).toBeCloseTo(
      reportB.learners[0]?.skills[0]?.value as number,
      10,
    );
  });

  it('handles a single response for a learner+skill', () => {
    const model = new BktModel();
    const report = model.score(model.fit([event('l1', 's1', true, '2026-01-01T00:00:00Z')]));
    expect(report.learners[0]?.skills[0]?.responseCount).toBe(1);
    expect(report.learners[0]?.skills[0]?.value).toBeCloseTo(0.75, 10);
  });

  it('applies a per-skill parameter override', () => {
    const events: ResponseEvent[] = [event('l1', 's1', true, '2026-01-01T00:00:00Z')];
    const model = new BktModel({ skillParams: { s1: { pInit: 0.9 } } });
    const fitted = model.fit(events);
    expect(fitted.params.s1?.pInit).toBe(0.9);
  });

  it('uses grid-search fitting when config.fit is true and no per-skill override is set', () => {
    const events: ResponseEvent[] = [
      event('l1', 's1', true, '2026-01-01T00:00:00Z'),
      event('l1', 's1', true, '2026-01-02T00:00:00Z'),
      event('l1', 's1', true, '2026-01-03T00:00:00Z'),
      event('l2', 's1', true, '2026-01-01T00:00:00Z'),
      event('l2', 's1', true, '2026-01-02T00:00:00Z'),
      event('l2', 's1', true, '2026-01-03T00:00:00Z'),
    ];
    const model = new BktModel({ fit: true });
    const fitted = model.fit(events);
    // An always-correct dataset should be fit with a high prior/transition,
    // not the textbook defaults (pInit=0.4).
    expect(fitted.params.s1?.pInit).toBeGreaterThan(BKT_DEFAULT_PARAMS.pInit);
  });
});
