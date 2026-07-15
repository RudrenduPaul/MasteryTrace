import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['test/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['src/cli/index.ts'],
      thresholds: {
        lines: 90,
        statements: 90,
        functions: 90,
        // Branches run lower than the others: a meaningful share of the
        // remaining gap is defensive code (optional-chaining fallbacks
        // required by noUncheckedIndexedAccess, near-impossible
        // denominator===0 guards in the BKT recursion, IRT's gradient-floor
        // clamp) that isn't worth contriving adversarial inputs to hit.
        branches: 70,
      },
    },
  },
});
