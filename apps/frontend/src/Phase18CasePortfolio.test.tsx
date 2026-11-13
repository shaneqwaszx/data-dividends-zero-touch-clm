// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchCasePortfolio } from "./api";
import { CASES_PAGE_SIZE, caseDeletedEffect, caseQueryKeys, prefetchSessionQueries } from "./caseQueries";
import CaseQueue, {
  DEFAULT_CASE_QUEUE_PRESENTATION,
  type CaseQueuePresentationState,
} from "./pages/CaseQueue";
import { createSessionQueryClient } from "./queryClient";
import type { AuthenticatedProfile, ZeroTouchCaseListItem } from "./types";

// These tests cover the live case portfolio; the fixed dashboard sample cases that the Cases
// table lists after live cases are covered in pages/SampleCaseDetail.test.tsx.
vi.mock("./pages/mockDashboards/onboardingSample", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./pages/mockDashboards/onboardingSample")>()),
  sampleCaseRows: () => [],
}));

const actor: AuthenticatedProfile = {
  user_id: "ethan-tan",
  display_name: "Ethan Tan",
  role: "RELATIONSHIP_MANAGER",
  team_id: "TEAM_A",
  team_display_name: "Alpha",
  team_type: "Corporate Client Onboarding",
  team_description: "Synthetic team",
  client_scope_label: "Alpha",
  capabilities: ["CASE_ACCESS"],
};

function item(caseId: string, name: string): ZeroTouchCaseListItem {
  return {
    case_id: caseId,
    team_id: "TEAM_A",
    client_scope_label: "Alpha",
    priority: 8,
    requested_uen: `20240000${caseId.at(-1)}A`,
    legal_name: name,
    status: "WAITING_FOR_REVIEW",
    current_stage: "DOCUMENT",
    updated_at: "2026-09-21T12:00:00Z",
    active_exception_count: 0,
    active_exception_types: [],
    human_interventions: 0,
    final_outcome: null,
    resolved_jurisdiction: "SG",
    created_at: "2026-09-21T11:00:00Z",
    completed_at: null,
    mock_goldtier_party_id: null,
  };
}

const first = item("00000000-0000-4000-8000-000000000181", "ALPHA PTE. LTD.");
const second = item("00000000-0000-4000-8000-000000000182", "BETA PTE. LTD.");

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
  vi.useRealTimers();
  if (root) await act(async () => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.restoreAllMocks();
});

describe("Phase 18 paged Cases portfolio", () => {
  it("sends every server dimension, trims search, and preserves AbortSignal", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [], offset: 50, limit: 25, has_more: false }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const controller = new AbortController();

    await fetchCasePortfolio({
      status: "WAITING_FOR_REVIEW",
      priority: "8",
      prioritySort: "lowest_first",
      teamFilter: "TEAM_A",
      attentionType: "DOCUMENT_LOW_CONFIDENCE",
      jurisdiction: "SG",
      search: "  Merlion.*  ",
      offset: 50,
      limit: 25,
    }, controller.signal);

    expect(request).toHaveBeenCalledTimes(1);
    const url = new URL(String(request.mock.calls[0][0]), "http://localhost");
    expect(url.pathname).toBe("/api/clm/zero-touch/case-portfolio");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      status: "WAITING_FOR_REVIEW",
      priority_filter: "8",
      priority_sort: "lowest_first",
      team_filter: "TEAM_A",
      attention_type: "DOCUMENT_LOW_CONFIDENCE",
      jurisdiction: "SG",
      search: "Merlion.*",
      limit: "25",
      offset: "50",
    });
    expect(request.mock.calls[0][1]).toMatchObject({ signal: controller.signal });
  });

  it("prefetches the bounded default page instead of the compatible unbounded list", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(String(input), "http://localhost").pathname;
      return new Response(JSON.stringify(
        path.endsWith("/case-portfolio")
          ? { items: [], offset: 0, limit: 10, has_more: false }
          : {},
      ), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    const queryClient = createSessionQueryClient();

    prefetchSessionQueries(queryClient, actor);
    await vi.waitFor(() => expect(request).toHaveBeenCalledTimes(2));

    const paths = request.mock.calls.map(([input]) => (
      new URL(String(input), "http://localhost").pathname
    ));
    expect(paths).toContain("/api/clm/zero-touch/case-portfolio");
    expect(paths).not.toContain("/api/clm/zero-touch/cases");
    const portfolio = request.mock.calls
      .map(([input]) => new URL(String(input), "http://localhost"))
      .find((url) => url.pathname.endsWith("/case-portfolio"))!;
    // The prefetched first page is the same page the Cases tab shows first.
    expect(portfolio.searchParams.get("limit")).toBe(String(CASES_PAGE_SIZE));
    expect(CASES_PAGE_SIZE).toBe(10);
  });

  it("keys pages by actor and every filter, sort, search, and paging dimension", () => {
    const base = {
      status: "WAITING_FOR_REVIEW" as const,
      priority: "all" as const,
      prioritySort: "highest_first" as const,
      teamFilter: "TEAM_A",
      attentionType: "DOCUMENT_LOW_CONFIDENCE" as const,
      jurisdiction: "SG" as const,
      search: " Merlion ",
      offset: 0,
      limit: 50,
    };
    const key = caseQueryKeys.casePortfolio(actor.user_id, base);
    expect(key).toEqual(caseQueryKeys.casePortfolio(actor.user_id, {
      ...base,
      search: "Merlion",
    }));
    for (const changed of [
      { user: "sophia-ng", filters: base },
      { user: actor.user_id, filters: { ...base, status: "RUNNING" as const } },
      { user: actor.user_id, filters: { ...base, priority: "8" as const } },
      { user: actor.user_id, filters: { ...base, prioritySort: "lowest_first" as const } },
      { user: actor.user_id, filters: { ...base, teamFilter: "TEAM_B" } },
      { user: actor.user_id, filters: { ...base, attentionType: undefined } },
      { user: actor.user_id, filters: { ...base, jurisdiction: "AU" as const } },
      { user: actor.user_id, filters: { ...base, search: "Lion" } },
      { user: actor.user_id, filters: { ...base, offset: 50 } },
      { user: actor.user_id, filters: { ...base, limit: 25 } },
    ]) {
      expect(caseQueryKeys.casePortfolio(changed.user, changed.filters)).not.toEqual(key);
    }
  });

  it("renders truthful bounded ranges and traverses cached pages accessibly", async () => {
    const queryClient = createSessionQueryClient();
    const filters = {
      priority: "all" as const,
      prioritySort: "highest_first" as const,
      teamFilter: "all",
      offset: 0,
      limit: 10,
    };
    queryClient.setQueryData(caseQueryKeys.casePortfolio(actor.user_id, filters), {
      items: [first], offset: 0, limit: 10, has_more: true,
    });
    queryClient.setQueryData(caseQueryKeys.casePortfolio(actor.user_id, {
      ...filters, offset: 10,
    }), { items: [second], offset: 10, limit: 10, has_more: false });

    await act(async () => root?.render(
      <MemoryRouter><QueryClientProvider client={queryClient}>
        <CaseQueue
          actor={actor}
          presentation={DEFAULT_CASE_QUEUE_PRESENTATION}
          onPresentationChange={() => undefined}
        />
      </QueryClientProvider></MemoryRouter>,
    ));
    expect(container?.textContent).toContain("Showing 1–1");
    expect(container?.textContent).not.toContain("Total results are not calculated");
    const next = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent?.trim() === "Next");
    await act(async () => next?.click());
    expect(container?.textContent).toContain("BETA PTE. LTD.");
    expect(container?.textContent).toContain("Showing 11–11");
    expect(container?.textContent).toContain("Page 2");
    const previous = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent?.trim() === "Previous");
    expect(previous?.disabled).toBe(false);
    expect(next?.disabled).toBe(true);
  });

  it("hides old-filter rows during the exact 300ms search debounce", async () => {
    vi.useFakeTimers();
    const queryClient = createSessionQueryClient();
    const base = {
      priority: "all" as const,
      prioritySort: "highest_first" as const,
      teamFilter: "all",
      offset: 0,
      limit: 10,
    };
    queryClient.setQueryData(caseQueryKeys.casePortfolio(actor.user_id, base), {
      items: [first], offset: 0, limit: 10, has_more: false,
    });
    queryClient.setQueryData(caseQueryKeys.casePortfolio(actor.user_id, {
      ...base, search: "Beta",
    }), { items: [second], offset: 0, limit: 10, has_more: false });

    function Harness() {
      const [presentation, setPresentation] = useState<CaseQueuePresentationState>(
        DEFAULT_CASE_QUEUE_PRESENTATION,
      );
      return <CaseQueue
        actor={actor}
        presentation={presentation}
        onPresentationChange={setPresentation}
      />;
    }
    await act(async () => root?.render(
      <MemoryRouter><QueryClientProvider client={queryClient}><Harness /></QueryClientProvider></MemoryRouter>,
    ));
    const search = container?.querySelector<HTMLInputElement>("input");
    await act(async () => {
      if (!search) return;
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")
        ?.set?.call(search, "Beta");
      search.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(container?.textContent).toContain("Updating search…");
    expect(container?.textContent).not.toContain("ALPHA PTE. LTD.");
    await act(async () => vi.advanceTimersByTime(299));
    expect(container?.textContent).not.toContain("BETA PTE. LTD.");
    await act(async () => vi.advanceTimersByTime(1));
    expect(container?.textContent).toContain("BETA PTE. LTD.");
  });

  it("removes a deletion from every page envelope without touching another user", async () => {
    const queryClient = createSessionQueryClient();
    const filters = {
      priority: "all" as const,
      prioritySort: "highest_first" as const,
      offset: 0,
      limit: 10,
    };
    const ownKey = caseQueryKeys.casePortfolio(actor.user_id, filters);
    const otherKey = caseQueryKeys.casePortfolio("sophia-ng", filters);
    queryClient.setQueryData(ownKey, {
      items: [first, second], offset: 0, limit: 10, has_more: false,
    });
    queryClient.setQueryData(otherKey, {
      items: [first], offset: 0, limit: 10, has_more: false,
    });

    await caseDeletedEffect(queryClient, actor.user_id, first.case_id);

    expect(queryClient.getQueryData(ownKey)).toMatchObject({ items: [second] });
    expect(queryClient.getQueryData(otherKey)).toMatchObject({ items: [first] });
  });
});
