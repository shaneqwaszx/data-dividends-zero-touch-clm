export type PriorityTier = "LOW" | "MEDIUM" | "HIGH";

export interface PriorityTierDistributionItem {
  tier: PriorityTier | null;
  label: string;
  count: number;
}

export const PRIORITY_TIER_WRITE_VALUE: Record<PriorityTier, 1 | 5 | 10> = {
  LOW: 1,
  MEDIUM: 5,
  HIGH: 10,
};

export function priorityTierForValue(priority: number | null): PriorityTier | null {
  if (priority === null) return null;
  if (priority <= 3) return "LOW";
  if (priority <= 7) return "MEDIUM";
  return "HIGH";
}

export function priorityTierLabel(priority: number | null): string {
  const tier = priorityTierForValue(priority);
  if (tier === null) return "Unprioritised";
  return tier.charAt(0) + tier.slice(1).toLowerCase();
}

export function priorityTierControlValue(priority: number | null): "" | "1" | "5" | "10" {
  const tier = priorityTierForValue(priority);
  return tier === null ? "" : String(PRIORITY_TIER_WRITE_VALUE[tier]) as "1" | "5" | "10";
}

export function aggregatePriorityDistribution(
  buckets: Array<{ priority: number | null; count: number }>,
): PriorityTierDistributionItem[] {
  const counts: Record<PriorityTier, number> & { UNSET: number } = {
    LOW: 0,
    MEDIUM: 0,
    HIGH: 0,
    UNSET: 0,
  };
  for (const bucket of buckets) {
    const tier = priorityTierForValue(bucket.priority);
    counts[tier ?? "UNSET"] += bucket.count;
  }
  return [
    { tier: "LOW", label: "Low", count: counts.LOW },
    { tier: "MEDIUM", label: "Medium", count: counts.MEDIUM },
    { tier: "HIGH", label: "High", count: counts.HIGH },
    { tier: null, label: "Unset", count: counts.UNSET },
  ];
}
