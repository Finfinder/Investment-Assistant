import type { StrategyEntry } from "@/types";

const DEFAULT_STRATEGY_ENTRY: StrategyEntry = {
  direction: "long",
  entry_condition: "",
  entry_price: 1.1,
  stop_loss: 1.0,
  tp1: 1.2,
  tp2: 1.3,
  confidence_pct: 50,
  risk_reward_ratio: 1,
  risk_reward_ratio_tp2: 1,
};

export function makeStrategyEntry(overrides: Partial<StrategyEntry> = {}): StrategyEntry {
  const definedOverrides = Object.fromEntries(
    Object.entries(overrides).filter(([, value]) => value !== undefined),
  ) as Partial<StrategyEntry>;
  return { ...DEFAULT_STRATEGY_ENTRY, ...definedOverrides };
}
