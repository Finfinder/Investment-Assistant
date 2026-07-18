import { describe, it, expect } from "vitest";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const repoRoot = resolve(__dirname, "..", "..");
const thresholdFile = resolve(repoRoot, "mutation-threshold.json");
const strykerConfigFile = resolve(__dirname, "..", "stryker.conf.js");

describe("mutation score threshold consistency", () => {
  it("exposes the shared threshold from mutation-threshold.json", () => {
    const raw = readFileSync(thresholdFile, "utf-8");
    const config = JSON.parse(raw) as { mutationScoreThreshold: number };

    expect(typeof config.mutationScoreThreshold).toBe("number");
    expect(config.mutationScoreThreshold).toBeGreaterThan(0);
    expect(config.mutationScoreThreshold).toBeLessThanOrEqual(100);
  });

  it("uses the shared threshold as the Stryker break threshold", () => {
    const raw = readFileSync(thresholdFile, "utf-8");
    const { mutationScoreThreshold } = JSON.parse(raw) as {
      mutationScoreThreshold: number;
    };

    // stryker.conf.js is CommonJS and reads the shared threshold at load time.
    const strykerConfig = require(strykerConfigFile) as {
      thresholds: { break: number };
    };

    expect(strykerConfig.thresholds.break).toBe(mutationScoreThreshold);
  });
});
