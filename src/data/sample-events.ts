import type { ResponseEvent } from '../core/event-schema.js';

// A small deterministic linear congruential generator, used only to keep the
// bundled sample data reproducible (no Math.random) while still looking like
// a real, slightly noisy response log rather than a hand-typed pattern.
function makeLcg(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0xffffffff;
  };
}

const LEARNERS = ['learner-ada', 'learner-brook', 'learner-cyrus'];
const SKILLS = ['fractions', 'linear-equations', 'reading-comprehension'];

// Roughly how likely each learner is to answer correctly on their Nth
// attempt at a skill (index 0 = first attempt), used only to shape the
// bundled sample into a plausible "learning over time" curve.
const LEARNING_CURVES: Record<string, number[]> = {
  'learner-ada': [0.3, 0.4, 0.55, 0.7, 0.8, 0.85, 0.9],
  'learner-brook': [0.2, 0.25, 0.3, 0.45, 0.55, 0.65, 0.75],
  'learner-cyrus': [0.5, 0.65, 0.75, 0.85, 0.9, 0.92, 0.95],
};

function buildSampleEvents(): ResponseEvent[] {
  const rand = makeLcg(42);
  const events: ResponseEvent[] = [];
  const startDate = Date.UTC(2026, 0, 5, 9, 0, 0); // 2026-01-05T09:00:00Z
  let dayOffset = 0;

  for (const skillId of SKILLS) {
    for (const learnerId of LEARNERS) {
      const curve = LEARNING_CURVES[learnerId] ?? [0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9];
      const attempts = 6 + Math.floor(rand() * 2); // 6 or 7 attempts per learner+skill
      for (let attempt = 0; attempt < attempts; attempt += 1) {
        const pCorrect = curve[Math.min(attempt, curve.length - 1)] ?? 0.5;
        const correct = rand() < pCorrect;
        const timestamp = new Date(
          startDate + dayOffset * 86_400_000 + attempt * 3_600_000,
        ).toISOString();
        events.push({ learnerId, skillId, correct, timestamp });
      }
      dayOffset += 1;
    }
  }

  return events;
}

/**
 * Bundled example event log for `masterytrace init`: 3 learners x 3 skills,
 * 6-7 responses each, with a deterministic (seeded) but plausible
 * "improving over time" pattern per learner.
 */
export const SAMPLE_EVENTS: ResponseEvent[] = buildSampleEvents();
