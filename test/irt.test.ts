import { describe, expect, it } from 'vitest';
import { IrtModel, probabilityCorrect } from '../src/models/irt.js';
import type { ResponseEvent } from '../src/core/event-schema.js';

// Deterministic (seeded) linear congruential generator, matching the one
// used for the bundled sample data, so synthetic test datasets are fully
// reproducible without relying on Math.random.
function makeLcg(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0xffffffff;
  };
}

function sigmoid(z: number): number {
  if (z >= 0) {
    const e = Math.exp(-z);
    return 1 / (1 + e);
  }
  const e = Math.exp(z);
  return e / (1 + e);
}

let clock = 0;
function nextTimestamp(): string {
  clock += 1;
  return new Date(Date.UTC(2026, 0, 1) + clock * 1000).toISOString();
}

describe('probabilityCorrect (2PL)', () => {
  it('equals 0.5 when theta equals the item difficulty', () => {
    expect(probabilityCorrect(0.5, 1.2, 0.5)).toBeCloseTo(0.5, 10);
  });

  it('increases with theta for fixed a/b', () => {
    const low = probabilityCorrect(-1, 1, 0);
    const high = probabilityCorrect(1, 1, 0);
    expect(high).toBeGreaterThan(low);
  });
});

describe('IrtModel', () => {
  it('implements the ScoringModel interface with name "irt"', () => {
    const model = new IrtModel();
    expect(model.name).toBe('irt');
  });

  it('fits and scores an empty event log without error', () => {
    const model = new IrtModel();
    const report = model.score(model.fit([]));
    expect(report.model).toBe('irt');
    expect(report.learners).toEqual([]);
  });

  it('handles a single response', () => {
    const model = new IrtModel({ iterations: 50 });
    const events: ResponseEvent[] = [
      { learnerId: 'l1', skillId: 's1', correct: true, timestamp: nextTimestamp() },
    ];
    const report = model.score(model.fit(events));
    expect(report.learners).toHaveLength(1);
    expect(Number.isFinite(report.learners[0]?.skills[0]?.value)).toBe(true);
  });

  it('(a) a learner who aces a hard item gets a higher theta than one who aces an easy item', () => {
    const rand = makeLcg(7);
    const events: ResponseEvent[] = [];

    // Baseline learners answer both items with a mix of correct/incorrect,
    // which is what lets the model tell the easy item and the hard item
    // apart in the first place.
    for (let b = 0; b < 6; b += 1) {
      const learnerId = `baseline-${b}`;
      for (let i = 0; i < 20; i += 1) {
        events.push({ learnerId, skillId: 'easy-skill', correct: rand() < 0.7, timestamp: nextTimestamp() });
      }
      for (let i = 0; i < 20; i += 1) {
        events.push({ learnerId, skillId: 'hard-skill', correct: rand() < 0.3, timestamp: nextTimestamp() });
      }
    }

    // Two "ace" learners: each answers only one item, always correctly.
    for (let i = 0; i < 15; i += 1) {
      events.push({ learnerId: 'easy-ace', skillId: 'easy-skill', correct: true, timestamp: nextTimestamp() });
    }
    for (let i = 0; i < 15; i += 1) {
      events.push({ learnerId: 'hard-ace', skillId: 'hard-skill', correct: true, timestamp: nextTimestamp() });
    }

    const model = new IrtModel();
    const fitted = model.fit(events);
    const easyAceTheta = fitted.learners.find((l) => l.learnerId === 'easy-ace')?.theta;
    const hardAceTheta = fitted.learners.find((l) => l.learnerId === 'hard-ace')?.theta;

    expect(easyAceTheta).toBeDefined();
    expect(hardAceTheta).toBeDefined();
    expect(hardAceTheta as number).toBeGreaterThan(easyAceTheta as number);

    // Sanity-check the item difficulties actually came out easy < hard,
    // confirming the theta gap above reflects item difficulty and not noise.
    const easyB = fitted.items.find((i) => i.skillId === 'easy-skill')?.b;
    const hardB = fitted.items.find((i) => i.skillId === 'hard-skill')?.b;
    expect(hardB as number).toBeGreaterThan(easyB as number);
  });

  it('(b) recovers approximately correct theta/a/b from a synthetic dataset with known parameters', () => {
    // Known ground truth. thetaTrue has mean 0 and std 1/sqrt(2); the 2PL
    // model is only identified up to theta's location/scale (z = a*(theta-b)
    // is unchanged by shifting theta and b by the same constant, or by
    // scaling theta/b by s while dividing a by s), and IrtModel's fit pins
    // that gauge by normalizing theta to mean 0 / std 1 every iteration. So
    // the values to compare recovered parameters against are the true
    // values passed through that same normalization, not the raw true
        // values themselves.
    const thetaTrue = [-1.0, -0.5, 0.0, 0.5, 1.0];
    const aTrue = [0.8, 1.0, 1.2, 1.5];
    const bTrue = [-1.0, -0.3, 0.4, 1.0];
    const learnerIds = thetaTrue.map((_, i) => `learner-${i}`);
    const skillIds = aTrue.map((_, i) => `skill-${i}`);
    const REPEATS_PER_PAIR = 200;

    const rand = makeLcg(1234);
    const events: ResponseEvent[] = [];
    for (let li = 0; li < learnerIds.length; li += 1) {
      for (let ii = 0; ii < skillIds.length; ii += 1) {
        const p = sigmoid((aTrue[ii] as number) * ((thetaTrue[li] as number) - (bTrue[ii] as number)));
        for (let r = 0; r < REPEATS_PER_PAIR; r += 1) {
          events.push({
            learnerId: learnerIds[li] as string,
            skillId: skillIds[ii] as string,
            correct: rand() < p,
            timestamp: nextTimestamp(),
          });
        }
      }
    }

    const model = new IrtModel();
    const fitted = model.fit(events);

    const trueMean = thetaTrue.reduce((sum, t) => sum + t, 0) / thetaTrue.length;
    const trueVariance =
      thetaTrue.reduce((sum, t) => sum + (t - trueMean) ** 2, 0) / thetaTrue.length;
    const trueStd = Math.sqrt(trueVariance);

    const TOLERANCE = 0.3;

    learnerIds.forEach((id, i) => {
      const recoveredTheta = fitted.learners.find((l) => l.learnerId === id)?.theta as number;
      const expectedTheta = (thetaTrue[i] as number) / trueStd;
      expect(Math.abs(recoveredTheta - expectedTheta)).toBeLessThan(TOLERANCE);
    });

    skillIds.forEach((id, j) => {
      const item = fitted.items.find((it) => it.skillId === id);
      const expectedB = (bTrue[j] as number) / trueStd;
      const expectedA = (aTrue[j] as number) * trueStd;
      expect(Math.abs((item?.b as number) - expectedB)).toBeLessThan(TOLERANCE);
      expect(Math.abs((item?.a as number) - expectedA)).toBeLessThan(TOLERANCE);
    });
  });

  it('scores each learner+skill with the predicted probability of a correct response attached', () => {
    const model = new IrtModel({ iterations: 50 });
    const events: ResponseEvent[] = [
      { learnerId: 'l1', skillId: 's1', correct: true, timestamp: nextTimestamp() },
      { learnerId: 'l1', skillId: 's1', correct: true, timestamp: nextTimestamp() },
    ];
    const report = model.score(model.fit(events));
    const skill = report.learners[0]?.skills[0];
    expect(skill?.metric).toBe('ability_theta');
    const predicted = skill?.details?.predictedProbabilityCorrect as number;
    expect(predicted).toBeGreaterThan(0);
    expect(predicted).toBeLessThan(1);
  });
});
