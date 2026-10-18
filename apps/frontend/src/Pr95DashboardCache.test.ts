import { afterEach, expect, it, vi } from "vitest";
import { activityQueryOptions, caseQueryKeys, dashboardQueryOptions } from "./caseQueries";
import { clearSessionQueries, createSessionQueryClient } from "./queryClient";

afterEach(() => vi.unstubAllGlobals());

it("isolates every dashboard scope/range and creator activity key", () => {
  const keys = new Set<string>();
  for (const user of ["maya-lim", "ethan-tan"]) {
    for (const team of ["all", "TEAM_A", "TEAM_B", "unassigned"]) {
      for (const scope of ["team", "mine"] as const) {
        for (const range of ["7d", "30d", "90d", "all"] as const) {
          keys.add(JSON.stringify(caseQueryKeys.dashboard(user, team, scope, range)));
        }
      }
    }
  }
  expect(keys.size).toBe(64);
  expect(caseQueryKeys.activity("maya-lim", { createdBy: "maya-lim" })).not.toEqual(
    caseQueryKeys.activity("maya-lim", { createdBy: "ethan-tan" }),
  );
});

it("cancels dashboard variants and prevents an old-session result from republishing", async () => {
  const client = createSessionQueryClient();
  let signal: AbortSignal | undefined;
  let release!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) => {
    signal = init.signal as AbortSignal;
    return new Promise<Response>((resolve) => { release = resolve; });
  }));
  const options = dashboardQueryOptions("maya-lim", "TEAM_A", "mine", "90d");
  const pending = client.fetchQuery(options).catch(() => undefined);
  expect(signal?.aborted).toBe(false);
  clearSessionQueries(client);
  expect(signal?.aborted).toBe(true);
  release(new Response(JSON.stringify({ oldSession: true }), { status: 200 }));
  await pending;
  expect(client.getQueryData(options.queryKey)).toBeUndefined();
  expect(client.getQueryCache().getAll()).toEqual([]);
});

it("passes the activity creator and AbortSignal through authenticated transport", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [] })));
  vi.stubGlobal("fetch", fetchMock);
  const signal = new AbortController().signal;
  const options = activityQueryOptions("maya-lim", { createdBy: "maya-lim" });
  await options.queryFn({ signal });
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("created_by=maya-lim"),
    expect.objectContaining({ signal, credentials: "include" }),
  );
});
