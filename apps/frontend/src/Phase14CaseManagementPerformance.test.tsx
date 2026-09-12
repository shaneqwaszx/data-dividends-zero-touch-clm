// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  caseDeletedEffect,
  caseListQueryOptions,
  caseQueryKeys,
  dashboardQueryOptions,
  publishCaseDetail,
} from "./caseQueries";
import { deleteZeroTouchCase } from "./api";
import CaseQueue, {
  DEFAULT_CASE_QUEUE_PRESENTATION,
  type CaseQueuePresentationState,
} from "./pages/CaseQueue";
import DeleteCaseDialog from "./pages/DeleteCaseDialog";
import OnboardedClients from "./pages/OnboardedClients";
import { clearSessionQueries, createSessionQueryClient, SESSION_STALE_TIME_MS } from "./queryClient";
import type { AuthenticatedProfile, ZeroTouchCaseListItem, ZeroTouchCaseSummary } from "./types";

const actor: AuthenticatedProfile = {
  user_id: "ethan-tan",
  display_name: "Ethan Tan",
  role: "RELATIONSHIP_MANAGER",
  team_id: "TEAM_A",
  team_display_name: "DBS Corporate Onboarding",
  team_type: "Corporate Client Onboarding",
  team_description: "Type: Corporate Client Onboarding | Client coverage: DBS",
  client_scope_label: "DBS",
  available_teams: [],
};

const listItem: ZeroTouchCaseListItem = {
  case_id: "00000000-0000-4000-8000-000000000014",
  team_id: "TEAM_A",
  client_scope_label: "DBS",
  priority: 9,
  requested_uen: "202400001A",
  legal_name: "MERLION PTE. LTD.",
  status: "WAITING_FOR_REVIEW",
  current_stage: "DOCUMENT",
  updated_at: "2026-09-08T01:00:00Z",
  active_exception_count: 1,
  human_interventions: 1,
  final_outcome: null,
  resolved_jurisdiction: "SG",
  created_at: "2026-09-08T00:00:00Z",
  completed_at: null,
  mock_goldtier_party_id: null,
};

let root: Root | null = null;
let container: HTMLDivElement | null = null;

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
    .IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(async () => {
  if (root) await act(async () => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.restoreAllMocks();
});

describe("Phase 14 session query cache", () => {
  it("reuses fresh data for 45 seconds and clears every user-owned entry", async () => {
    const queryClient = createSessionQueryClient();
    const loader = vi.fn(async () => [listItem]);
    const queryKey = caseQueryKeys.caseList("ethan-tan", undefined, "all", "highest_first");

    await queryClient.fetchQuery({ queryKey, queryFn: loader });
    await queryClient.fetchQuery({ queryKey, queryFn: loader });
    queryClient.setQueryData(caseQueryKeys.dashboard("olivia-koh"), { private: true });

    expect(SESSION_STALE_TIME_MS).toBe(45_000);
    expect(loader).toHaveBeenCalledTimes(1);
    expect(queryClient.getQueryData(queryKey)).toEqual([listItem]);
    clearSessionQueries(queryClient);
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });

  it("deduplicates an in-flight prefetch and aborts it when the session clears", async () => {
    const queryClient = createSessionQueryClient();
    let aborted = false;
    const loader = vi.fn(({ signal }: { signal: AbortSignal }) => new Promise<never>((_, reject) => {
      signal.addEventListener("abort", () => {
        aborted = true;
        reject(new DOMException("aborted", "AbortError"));
      });
    }));
    const options = { queryKey: ["auth", "ethan-tan", "pending"] as const, queryFn: loader };
    const first = queryClient.fetchQuery(options);
    const second = queryClient.fetchQuery(options);

    clearSessionQueries(queryClient);
    await Promise.allSettled([first, second]);
    expect(loader).toHaveBeenCalledTimes(1);
    expect(aborted).toBe(true);
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });

  it("publishes polling detail and removes all deleted case resources and list variants", async () => {
    const queryClient = createSessionQueryClient();
    const caseId = listItem.case_id;
    const summary = { case: { case_id: caseId } } as ZeroTouchCaseSummary;
    const all = caseQueryKeys.caseList(actor.user_id, undefined, "all", "highest_first");
    const completed = caseQueryKeys.caseList(actor.user_id, "COMPLETED", "all", "highest_first");
    queryClient.setQueryData(all, [listItem]);
    queryClient.setQueryData(completed, [listItem]);
    queryClient.setQueryData(caseQueryKeys.documents(actor.user_id, caseId), [{ private: true }]);
    queryClient.setQueryData(caseQueryKeys.ownership(actor.user_id, caseId), { private: true });
    queryClient.setQueryData(caseQueryKeys.dashboard(actor.user_id), { private: true });

    publishCaseDetail(queryClient, actor.user_id, summary);
    expect(queryClient.getQueryData(caseQueryKeys.detail(actor.user_id, caseId))).toBe(summary);
    await caseDeletedEffect(queryClient, actor.user_id, caseId);

    expect(queryClient.getQueryData<ZeroTouchCaseListItem[]>(all)).toEqual([]);
    expect(queryClient.getQueryData<ZeroTouchCaseListItem[]>(completed)).toEqual([]);
    expect(queryClient.getQueryData(caseQueryKeys.detail(actor.user_id, caseId))).toBeUndefined();
    expect(queryClient.getQueryData(caseQueryKeys.documents(actor.user_id, caseId))).toBeUndefined();
    expect(queryClient.getQueryData(caseQueryKeys.ownership(actor.user_id, caseId))).toBeUndefined();
    expect(queryClient.getQueryData(caseQueryKeys.dashboard(actor.user_id))).toBeUndefined();
  });

  it("cancels stale list and Dashboard requests before deletion cache mutation", async () => {
    const queryClient = createSessionQueryClient();
    const listKey = caseQueryKeys.caseList(
      actor.user_id,
      undefined,
      "all",
      "highest_first",
    );
    const otherUserKey = caseQueryKeys.caseList(
      "sophia-ng",
      undefined,
      "all",
      "highest_first",
    );
    queryClient.setQueryData(listKey, [listItem]);
    queryClient.setQueryData(caseQueryKeys.dashboard(actor.user_id), { stale: true });
    queryClient.setQueryData(otherUserKey, [listItem]);

    const pending = new Map<
      "list" | "dashboard",
      { signal: AbortSignal; resolve: (response: Response) => void }
    >();
    const request = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const kind = String(input).includes("/dashboard") ? "dashboard" : "list";
      return new Promise<Response>((resolve) => {
        pending.set(kind, { signal: init?.signal as AbortSignal, resolve });
      });
    });
    const oldList = queryClient.fetchQuery({
      ...caseListQueryOptions(actor.user_id, undefined, "all", "highest_first"),
      staleTime: 0,
    });
    const oldDashboard = queryClient.fetchQuery({
      ...dashboardQueryOptions(actor.user_id),
      staleTime: 0,
    });
    await vi.waitFor(() => expect(pending.size).toBe(2));

    await caseDeletedEffect(queryClient, actor.user_id, listItem.case_id);
    expect(pending.get("list")?.signal.aborted).toBe(true);
    expect(pending.get("dashboard")?.signal.aborted).toBe(true);
    expect(queryClient.getQueryData<ZeroTouchCaseListItem[]>(listKey)).toEqual([]);
    expect(queryClient.getQueryData(caseQueryKeys.dashboard(actor.user_id))).toBeUndefined();
    expect(queryClient.getQueryData(otherUserKey)).toEqual([listItem]);

    pending.get("list")?.resolve(new Response(JSON.stringify([listItem]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    pending.get("dashboard")?.resolve(new Response(JSON.stringify({ stale: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    await Promise.allSettled([oldList, oldDashboard]);
    expect(queryClient.getQueryData<ZeroTouchCaseListItem[]>(listKey)).toEqual([]);
    expect(queryClient.getQueryData(caseQueryKeys.dashboard(actor.user_id))).toBeUndefined();

    request.mockResolvedValueOnce(new Response(JSON.stringify([listItem]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    await queryClient.fetchQuery({
      ...caseListQueryOptions(actor.user_id, undefined, "all", "highest_first"),
      staleTime: 0,
    });
    expect(queryClient.getQueryData(listKey)).toEqual([listItem]);
  });

  it("keeps the row until 204 and retains it when DELETE fails", async () => {
    const queryClient = createSessionQueryClient();
    const listKey = caseQueryKeys.caseList(
      actor.user_id,
      undefined,
      "all",
      "highest_first",
    );
    queryClient.setQueryData(listKey, [listItem]);
    let resolveDelete!: (response: Response) => void;
    const request = vi.spyOn(globalThis, "fetch").mockImplementationOnce(
      () => new Promise<Response>((resolve) => {
        resolveDelete = resolve;
      }),
    );
    const successfulDelete = (async () => {
      await deleteZeroTouchCase(listItem.case_id);
      await caseDeletedEffect(queryClient, actor.user_id, listItem.case_id);
    })();
    await vi.waitFor(() => expect(request).toHaveBeenCalledTimes(1));
    expect(queryClient.getQueryData(listKey)).toEqual([listItem]);
    resolveDelete(new Response(null, { status: 204 }));
    await successfulDelete;
    expect(queryClient.getQueryData(listKey)).toEqual([]);

    queryClient.setQueryData(listKey, [listItem]);
    request.mockResolvedValueOnce(new Response(JSON.stringify({
      detail: { code: "CASE_DELETE_UNAVAILABLE", message: "Deletion unavailable." },
    }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    }));
    await expect(deleteZeroTouchCase(listItem.case_id)).rejects.toThrow();
    expect(queryClient.getQueryData(listKey)).toEqual([listItem]);
  });
});

describe("Phase 14 queue and delete UX", () => {
  it("loads the portfolio with one list request and no detail fan-out", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([listItem]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const queryClient = createSessionQueryClient();
    await queryClient.fetchQuery(
      caseListQueryOptions(actor.user_id, undefined, "all", "highest_first"),
    );

    await act(async () => {
      root?.render(
        <QueryClientProvider client={queryClient}>
          <CaseQueue
            actor={actor}
            presentation={DEFAULT_CASE_QUEUE_PRESENTATION}
            onPresentationChange={() => undefined}
            onOpenCase={() => undefined}
          />
        </QueryClientProvider>,
      );
    });
    expect(container?.textContent).toContain("MERLION PTE. LTD.");

    expect(request).toHaveBeenCalledTimes(1);
    expect(String(request.mock.calls[0][0])).toContain("/api/clm/zero-touch/cases");
    expect(request.mock.calls.some(([url]) => String(url).endsWith(`/${listItem.case_id}`))).toBe(false);
  });

  it("loads Onboarded with one completed-list request and no detail fan-out", async () => {
    const completed = { ...listItem, status: "COMPLETED" as const };
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([completed]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const queryClient = createSessionQueryClient();
    await queryClient.fetchQuery(
      caseListQueryOptions(actor.user_id, "COMPLETED", "all", "highest_first"),
    );
    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <OnboardedClients actor={actor} onOpenClient={() => undefined} />
      </QueryClientProvider>,
    ));

    expect(container?.textContent).toContain("MERLION PTE. LTD.");
    expect(request).toHaveBeenCalledTimes(1);
    expect(String(request.mock.calls[0][0])).toContain("status=COMPLETED");
    expect(request.mock.calls.some(([url]) => String(url).endsWith(`/${listItem.case_id}`))).toBe(false);
  });

  it("preserves controlled filters when the queue is unmounted for detail navigation", async () => {
    function Harness() {
      const [presentation, setPresentation] = useState<CaseQueuePresentationState>({
        ...DEFAULT_CASE_QUEUE_PRESENTATION,
        search: "Merlion",
        jurisdiction: "SG",
      });
      const [detail, setDetail] = useState(false);
      return detail ? (
        <button type="button" onClick={() => setDetail(false)}>Back</button>
      ) : (
        <CaseQueue actor={actor} presentation={presentation} onPresentationChange={setPresentation} onOpenCase={() => setDetail(true)} />
      );
    }
    const queryClient = createSessionQueryClient();
    queryClient.setQueryData(
      caseQueryKeys.caseList(actor.user_id, undefined, "all", "highest_first"),
      [listItem],
    );
    await act(async () => root?.render(<QueryClientProvider client={queryClient}><Harness /></QueryClientProvider>));
    const row = container?.querySelector<HTMLTableRowElement>("tbody tr");
    await act(async () => row?.click());
    await act(async () => container?.querySelector<HTMLButtonElement>("button")?.click());

    expect(container?.querySelector<HTMLInputElement>("input")?.value).toBe("Merlion");
    expect(container?.querySelectorAll<HTMLSelectElement>("select")[3]?.value).toBe("SG");
  });

  it("focuses Cancel, traps Tab, restores focus, handles Escape, and submits once", async () => {
    const trigger = document.createElement("button");
    document.body.append(trigger);
    trigger.focus();
    const confirm = vi.fn(() => new Promise<void>(() => undefined));
    const cancel = vi.fn();
    await act(async () => root?.render(
      <DeleteCaseDialog
        caseId={listItem.case_id}
        companyName="MERLION PTE. LTD."
        requestedUen={listItem.requested_uen}
        onCancel={cancel}
        onConfirm={confirm}
      />,
    ));
    const buttons = container?.querySelectorAll<HTMLButtonElement>("button");
    expect(document.activeElement).toBe(buttons?.[0]);
    buttons?.[1].focus();
    buttons?.[1].dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
    expect(document.activeElement).toBe(buttons?.[0]);
    await act(async () => {
      buttons?.[1].click();
      buttons?.[1].click();
    });
    expect(confirm).toHaveBeenCalledTimes(1);

    await act(async () => root?.unmount());
    expect(document.activeElement).toBe(trigger);
    trigger.remove();
    root = null;
  });

  it("cancels with Escape before submission", async () => {
    const cancel = vi.fn();
    await act(async () => root?.render(
      <DeleteCaseDialog
        caseId={listItem.case_id}
        companyName="MERLION PTE. LTD."
        requestedUen={listItem.requested_uen}
        onCancel={cancel}
        onConfirm={async () => undefined}
      />,
    ));
    container?.querySelector("[role='alertdialog']")?.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );
    expect(cancel).toHaveBeenCalledTimes(1);
  });
});
