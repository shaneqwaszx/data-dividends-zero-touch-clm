import { describe, expect, it } from "vitest";

import {
  aggregatePriorityDistribution,
  priorityTierControlValue,
  priorityTierForValue,
  priorityTierLabel,
} from "./priority";

describe("provisional priority tier presentation", () => {
  it.each([
    [1, "LOW", "Low", "1"],
    [3, "LOW", "Low", "1"],
    [4, "MEDIUM", "Medium", "5"],
    [7, "MEDIUM", "Medium", "5"],
    [8, "HIGH", "High", "10"],
    [10, "HIGH", "High", "10"],
    [null, null, "Unprioritised", ""],
  ] as const)("maps legacy value %s without changing persistence", (value, tier, label, writeValue) => {
    expect(priorityTierForValue(value)).toBe(tier);
    expect(priorityTierLabel(value)).toBe(label);
    expect(priorityTierControlValue(value)).toBe(writeValue);
  });

  it("aggregates every numeric backend bucket exactly once", () => {
    const buckets = [
      ...Array.from({ length: 10 }, (_, index) => ({ priority: index + 1, count: index + 1 })),
      { priority: null, count: 11 },
    ];
    const distribution = aggregatePriorityDistribution(buckets);
    expect(distribution).toEqual([
      { tier: "LOW", label: "Low", count: 6 },
      { tier: "MEDIUM", label: "Medium", count: 22 },
      { tier: "HIGH", label: "High", count: 27 },
      { tier: null, label: "Unset", count: 11 },
    ]);
    expect(distribution.reduce((total, item) => total + item.count, 0)).toBe(66);
  });
});
