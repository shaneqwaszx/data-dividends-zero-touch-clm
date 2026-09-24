import { fetchGoldTierSandboxStatus } from "./api";

export const goldTierSandboxQueryKeys = {
  root: (userId: string) => ["auth", userId, "provider-sandbox", "goldtier"] as const,
  status: (userId: string) => [
    ...goldTierSandboxQueryKeys.root(userId),
    "status",
  ] as const,
};

export function goldTierSandboxStatusQueryOptions(userId: string) {
  return {
    queryKey: goldTierSandboxQueryKeys.status(userId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchGoldTierSandboxStatus(signal),
  };
}
