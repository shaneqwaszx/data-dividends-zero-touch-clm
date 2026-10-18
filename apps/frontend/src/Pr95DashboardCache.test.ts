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


it("PR95-R4 activity keys isolate page, creator, team and effective actor role/team", () => {
  const base = { createdBy: "maya-lim", teamFilter: "all", limit: 10, offset: 0 };
  const scopes = [
    { role: "CLIENT_ONBOARDER" as const, team_id: "TEAM_A" as const },
    { role: "CLIENT_ONBOARDER" as const, team_id: "TEAM_B" as const },
    { role: "DIRECTOR" as const, team_id: null },
  ];
  const keys = new Set<string>();
  for (const scope of scopes) for (const offset of [0, 10, 100]) {
    keys.add(JSON.stringify(activityQueryOptions("maya-lim", { ...base, offset }, scope).queryKey));
  }
  expect(keys.size).toBe(9);
});


it("PR95-R4 paged activity cancellation prevents old-session publication and scopes every filter", async () => {
  const filters = { createdBy: "maya-lim", teamFilter: "TEAM_A", offset: 100, limit: 10 };
  const actorScope = { role: "DIRECTOR" as const, team_id: null };
  const options = activityQueryOptions("olivia-koh", filters, actorScope);
  const variations = [
    activityQueryOptions("maya-lim", filters, actorScope),
    activityQueryOptions("olivia-koh", { ...filters, createdBy: "ethan-tan" }, actorScope),
    activityQueryOptions("olivia-koh", { ...filters, teamFilter: "TEAM_B" }, actorScope),
    activityQueryOptions("olivia-koh", { ...filters, offset: 0 }, actorScope),
    activityQueryOptions("olivia-koh", { ...filters, limit: 50 }, actorScope),
  ];
  expect(new Set([options, ...variations].map(item => JSON.stringify(item.queryKey))).size).toBe(6);
  const client = createSessionQueryClient();
  let signal: AbortSignal | undefined;
  let release!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) => {
    signal = init.signal as AbortSignal;
    return new Promise<Response>(resolve => { release = resolve; });
  }));
  const pending = client.fetchQuery(options).catch(() => undefined);
  expect(signal?.aborted).toBe(false);
  clearSessionQueries(client);
  expect(signal?.aborted).toBe(true);
  release(new Response(JSON.stringify({ items: [{ message: "old private page" }], offset: 100, limit: 10, has_more: true })));
  await pending;
  expect(client.getQueryData(options.queryKey)).toBeUndefined();
  expect(client.getQueryCache().getAll()).toEqual([]);
});
