import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  caseActivityExportUrl,
  fetchCaseActivity,
  fetchZeroTouchCase,
  fetchZeroTouchCases,
} from "./api";
import {
  activityQueryOptions,
  caseDeletedEffect,
  caseQueryKeys,
  priorityMutationEffect,
} from "./caseQueries";
import AuditTrail, { formatActivityTimestampUtc } from "./pages/AuditTrail";
import { createSessionQueryClient } from "./queryClient";
import type { AuthenticatedProfile, CaseActivityPage, ZeroTouchCaseListItem } from "./types";

const CASE_ID = "00000000-0000-4000-8000-000000000171";
const actor: AuthenticatedProfile = {
  user_id: "ethan-tan",
  display_name: "Ethan Tan",
  role: "RELATIONSHIP_MANAGER",
  team_id: "TEAM_A",
  team_display_name: "Alpha",
  team_type: "Corporate Client Onboarding",
  team_description: "Synthetic POC team",
  client_scope_label: "Alpha",
  capabilities: ["CASE_ACCESS"],
};

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function activityPage(overrides: Partial<CaseActivityPage> = {}): CaseActivityPage {
  return {
    items: [{
      case_id: CASE_ID,
      sequence: 2,
      timestamp: "2026-09-21T12:00:00.123456Z",
      event_type: "DOCUMENT_REVIEW_REQUIRED",
      status: "WAITING_FOR_REVIEW",
      stage: "DOCUMENT",
      outcome: "REVIEW_REQUIRED",
      code: "DOCUMENT_LOW_CONFIDENCE",
      message: "Review <img src=x onerror=alert(1)> safely.",
      current_priority: 8,
      current_client_scope_label: "Alpha",
    }],
    offset: 0,
    limit: 50,
    has_more: false,
    ...overrides,
  };
}

const listItem = (caseId: string): ZeroTouchCaseListItem => ({
  case_id: caseId,
  team_id: "TEAM_A",
  client_scope_label: "Alpha",
  priority: 8,
  requested_uen: "202400001A",
  legal_name: "MERLION PTE. LTD.",
  status: "WAITING_FOR_REVIEW",
  current_stage: "DOCUMENT",
  updated_at: "2026-09-21T12:00:00Z",
  active_exception_count: 1,
  active_exception_types: ["DOCUMENT_LOW_CONFIDENCE"],
  human_interventions: 0,
  final_outcome: null,
  resolved_jurisdiction: "SG",
  created_at: "2026-09-21T11:00:00Z",
  completed_at: null,
  mock_goldtier_party_id: null,
});

async function legacyAuditLoad(caseCount: number): Promise<void> {
  const cases = await fetchZeroTouchCases();
  await Promise.all(cases.slice(0, caseCount).map((item) => fetchZeroTouchCase(item.case_id)));
}

describe("Phase 17 case activity", () => {
  let root: Root | null = null;
  let container: HTMLDivElement | null = null;

  afterEach(async () => {
    if (root) await act(async () => root?.unmount());
    container?.remove();
    root = null;
    container = null;
    vi.restoreAllMocks();
  });

  it("renders canonical UTC without losing source microsecond precision", () => {
    expect(formatActivityTimestampUtc("2026-09-21T12:00:00.123456Z")).toBe(
      "2026-09-21T12:00:00.123456Z",
    );
    expect(formatActivityTimestampUtc("2026-09-21T12:00:00.123456+00:00")).toBe(
      "2026-09-21T12:00:00.123456Z",
    );
  });

  it("serializes only supplied exact filters and preserves AbortSignal", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(activityPage()));
    const controller = new AbortController();

    await fetchCaseActivity({
      caseId: CASE_ID,
      teamFilter: "all",
      action: "DOCUMENT",
      stage: "DOCUMENT",
      outcome: "REVIEW_REQUIRED",
      from: "2026-09-01T00:00:00Z",
      to: "2026-10-01T00:00:00Z",
      limit: 25,
      offset: 50,
    }, controller.signal);

    expect(String(request.mock.calls[0][0])).toBe(
      `/api/clm/zero-touch/activity?case_id=${CASE_ID}&action=DOCUMENT&stage=DOCUMENT&outcome=REVIEW_REQUIRED&from=2026-09-01T00%3A00%3A00Z&to=2026-10-01T00%3A00%3A00Z&limit=25&offset=50`,
    );
    expect(request.mock.calls[0][1]).toMatchObject({ signal: controller.signal });
    expect(caseActivityExportUrl({
      caseId: CASE_ID,
      action: "DOCUMENT",
      limit: 100,
    })).toBe(
      `/api/clm/zero-touch/activity.csv?case_id=${CASE_ID}&action=DOCUMENT&limit=100`,
    );
  });

  it.each([1, 25, 100])("replaces legacy 1+N detail fan-out for %i cases with one page call", async (count) => {
    const cases = Array.from({ length: count }, (_, index) =>
      listItem(`00000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`));
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url === "/api/clm/zero-touch/cases") return json(cases);
      if (url.startsWith("/api/clm/zero-touch/cases/")) return json({});
      if (url === "/api/clm/zero-touch/activity") return json(activityPage());
      return json({}, 404);
    });

    await legacyAuditLoad(count);
    expect(request).toHaveBeenCalledTimes(1 + count);
    request.mockClear();
    await fetchCaseActivity({});
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("uses complete user/filter/page identity without previous-key data", () => {
    const first = caseQueryKeys.activity(actor.user_id, {
      action: "DOCUMENT",
      stage: "DOCUMENT",
      offset: 0,
    });
    const pageTwo = caseQueryKeys.activity(actor.user_id, {
      action: "DOCUMENT",
      stage: "DOCUMENT",
      offset: 50,
    });
    const otherUser = caseQueryKeys.activity("other-user", {
      action: "DOCUMENT",
      stage: "DOCUMENT",
      offset: 0,
    });
    expect(first).not.toEqual(pageTwo);
    expect(first).not.toEqual(otherUser);
    expect(activityQueryOptions(actor.user_id, {}).queryKey).toEqual(
      caseQueryKeys.activity(actor.user_id, {}),
    );
    expect(activityQueryOptions(actor.user_id, {})).not.toHaveProperty("placeholderData");
  });

  it("invalidates current metadata and cancels/removes all user activity on deletion", async () => {
    const client = createSessionQueryClient();
    const activityKey = caseQueryKeys.activity(actor.user_id, {});
    client.setQueryData(activityKey, activityPage());

    await priorityMutationEffect(client, actor.user_id);
    expect(client.getQueryState(activityKey)?.isInvalidated).toBe(true);

    client.setQueryData(activityKey, activityPage());
    const cancel = vi.spyOn(client, "cancelQueries");
    await caseDeletedEffect(client, actor.user_id, CASE_ID);
    expect(cancel).toHaveBeenCalledWith({ queryKey: caseQueryKeys.activities(actor.user_id) });
    expect(client.getQueryData(activityKey)).toBeUndefined();
  });

  it("renders honest limits, escaped local detail, filters, and bounded paging", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("action=DOCUMENT")) return json(activityPage({ has_more: false }));
      return json(activityPage({ has_more: true }));
    });
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    const client = createSessionQueryClient();
    await act(async () => root?.render(
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <AuditTrail actor={actor} caseId={null} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));

    await vi.waitFor(() => expect(container?.textContent).toContain("document_review_required"));
    expect(container?.textContent).toContain("2026-09-21T12:00:00.123456Z");
    expect(container?.textContent).not.toContain("8:00 pm");
    expect(container?.textContent).toContain("Actor attribution is not recorded");
    expect(container?.textContent).toContain("current case metadata");
    expect(container?.textContent).toContain("live view");
    expect(container?.textContent).not.toContain("ByLoop");
    const exportLink = Array.from(container?.querySelectorAll("a") ?? [])
      .find((link) => link.textContent === "Export current page CSV") as HTMLAnchorElement;
    expect(exportLink.download).toBe("case-activity.csv");
    expect(exportLink.getAttribute("href")).toContain("/api/clm/zero-touch/activity.csv?limit=50");

    const inspect = Array.from(container?.querySelectorAll("button") ?? [])
      .find((button) => button.textContent === "Inspect");
    await act(async () => inspect?.click());
    expect(container?.textContent).toContain("Review <img src=x onerror=alert(1)> safely.");
    expect(container?.querySelector("img")).toBeNull();

    const next = Array.from(container?.querySelectorAll("button") ?? [])
      .find((button) => button.textContent === "Next") as HTMLButtonElement;
    expect(next.disabled).toBe(false);
    await act(async () => next.click());
    await vi.waitFor(() => expect(request.mock.calls.some((call) => String(call[0]).includes("offset=50"))).toBe(true));

    const documentFilter = Array.from(container?.querySelectorAll("button") ?? [])
      .find((button) => button.textContent === "document");
    await act(async () => documentFilter?.click());
    await vi.waitFor(() => expect(String(request.mock.calls.at(-1)?.[0])).toContain("action=DOCUMENT"));
    expect(String(request.mock.calls.at(-1)?.[0])).not.toContain("offset=");
  });
});
// @vitest-environment jsdom
