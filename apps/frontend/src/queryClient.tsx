import { QueryClient } from "@tanstack/react-query";

import { clearAllSourceIntents } from "./pages/BlockerDecisionReview";

export const SESSION_STALE_TIME_MS = 45_000;
export const SESSION_GC_TIME_MS = 15 * 60_000;

export function createSessionQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: SESSION_STALE_TIME_MS,
        gcTime: SESSION_GC_TIME_MS,
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
        retry: 1,
      },
      mutations: { retry: false },
    },
  });
}

export function clearSessionQueries(queryClient: QueryClient): void {
  void queryClient.cancelQueries();
  queryClient.clear();
  // In-memory review choices are session state too; another identity must not inherit them.
  clearAllSourceIntents();
}
