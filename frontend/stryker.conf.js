// Stryker configuration for the frontend mutation testing gate.
// The mutation score threshold is the single source of truth shared with the
// backend mutmut gate and lives in mutation-threshold.json at the repository root.
const { mutationScoreThreshold } = require("../mutation-threshold.json");

/** @type {import('@stryker-mutator/core').StrykerOptions} */
module.exports = {
  $schema: "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  testRunner: "vitest",
  vitest: {
    configFile: "vitest.config.ts",
  },
  checkers: ["typescript"],
  tsconfigFile: "tsconfig.json",
  mutate: ["src/lib/riskReward.ts", "src/lib/format.ts"],
  testFiles: [
    "__tests__/riskRewardClass.test.ts",
    "__tests__/confidenceBarClass.test.ts",
    "__tests__/formatRiskReward.test.ts",
  ],
  reporters: ["clear-text", "progress", "html"],
  thresholds: {
    break: mutationScoreThreshold,
  },
};
