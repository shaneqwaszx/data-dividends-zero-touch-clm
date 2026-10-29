// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchZeroTouchCases } from "./api";
import {
  caseDeletedEffect,
  caseListQueryOptions,
  caseQueryKeys,
} from "./caseQueries";
import CaseQueue, {
  DEFAULT_CASE_QUEUE_PRESENTATION,
  type CaseQueuePresentationState,
} from "./pages/CaseQueue";
import { createSessionQueryClient } from "./queryClient";
import {
  BUSINESS_EXCEPTION_TYPE_LABELS,
  BUSINESS_EXCEPTION_TYPES,
  type AuthenticatedProfile,
  type ZeroTouchCaseListItem,
} from "./types";
import { mapZeroTouchCaseToCaseRow } from "./viewModels";

const actor: AuthenticatedProfile = {
  user_id: "ethan-tan",
  display_name: "Ethan Tan",
  role: "RELATIONSHIP_MANAGER",
  team_id: "TEAM_A",
  team_display_name: "DBS Corporate Onboarding",
  team_type: "Corporate Client Onboarding",
  team_description: "Synthetic team",
  client_scope_label: "DBS",
  capabilities: ["CASE_ACCESS"],
};

function listItem(
  caseId: string,
  activeExceptionTypes: ZeroTouchCaseListItem["active_exception_types"],
  activeExceptionCount: number,
): ZeroTouchCaseListItem {
  return {
    case_id: caseId,
    team_id: "TEAM_A",
    client_scope_label: "DBS",
    priority: 9,
    requested_uen: `20240000${caseId.at(-1)}A`,
    legal_name: activeExceptionTypes.length ? "BLOCKED SYNTHETIC PTE. LTD." : "RECOVERY SYNTHETIC PTE. LTD.",
    status: activeExceptionTypes.length ? "WAITING_FOR_REVIEW" : "RECOVERY_PENDING",
    current_stage: activeExceptionTypes.length ? "DOCUMENT" : "MOCK_GOLDTIER",
    updated_at: "2026-09-21T01:00:00Z",
    active_exception_count: activeExceptionCount,
    active_exception_types: activeExceptionTypes,
    human_interventions: 0,
    final_outcome: null,
    resolved_jurisdiction: "SG",
    created_at: "2026-09-21T00:00:00Z",
    completed_at: null,
    mock_goldtier_party_id: null,
  };
}

const blocked = listItem(
  "00000000-0000-4000-8000-000000000001",
  ["DOCUMENT_LOW_CONFIDENCE", "OWNERSHIP_CYCLE"],
  3,
);
const recovery = listItem("00000000-0000-4000-8000-000000000002", [], 0);

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

describe("blocker-aware attention queue contract", () => {
  it("keeps the exact backend vocabulary in declaration order with complete labels", () => {
    expect(BUSINESS_EXCEPTION_TYPES).toEqual([
      "REGISTRY_REVIEW_REQUIRED",
      "JURISDICTION_UNRESOLVED",
      "JURISDICTION_CONFLICT",
      "REGISTRY_PROVIDER_NOT_IMPLEMENTED",
      "REGISTRY_IDENTIFIER_NOT_ELIGIBLE",
      "DOCUMENT_SOURCE_CONFLICT",
      "DOCUMENT_LOW_CONFIDENCE",
      "DOCUMENT_REQUIRED_FIELD_MISSING",
      "DOCUMENT_REVIEW_REQUIRED",
      "RECONCILIATION_INVALID",
      "OWNERSHIP_CYCLE",
      "OWNERSHIP_INCOMPLETE",
      "OWNERSHIP_REVIEW_REQUIRED",
      "ENTITY_RESOLUTION_REVIEW_REQUIRED",
      "MOCK_RISK_REVIEW_REQUIRED",
      "EXISTING_PARTY_REVIEW_REQUIRED",
      "TARGET_PARTIAL_REVIEW_REQUIRED",
      "TARGET_CLASSIFICATION_REQUIRED",
      "TARGET_CONFIRMATION_REQUIRED",
    ]);
    expect(Object.keys(BUSINESS_EXCEPTION_TYPE_LABELS)).toEqual(BUSINESS_EXCEPTION_TYPES);
    expect(Object.values(BUSINESS_EXCEPTION_TYPE_LABELS).every(Boolean)).toBe(true);
  });

  it("appends attention_type after the existing AbortSignal and omits it for All", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(
      async () => new Response(JSON.stringify([]), { status: 200 }),
    );
    const controller = new AbortController();

    await fetchZeroTouchCases(undefined, "all", "highest_first", "TEAM_A", controller.signal);
    await fetchZeroTouchCases(
      undefined,
      "all",
      "highest_first",
      "TEAM_A",
      controller.signal,
      "OWNERSHIP_CYCLE",
    );

    expect(request.mock.calls[0][0]).toBe("/api/clm/zero-touch/cases?team_filter=TEAM_A");
    expect(request.mock.calls[0][1]).toMatchObject({ signal: controller.signal });
    expect(request.mock.calls[1][0]).toBe(
      "/api/clm/zero-touch/cases?team_filter=TEAM_A&attention_type=OWNERSHIP_CYCLE",
    );
    expect(request.mock.calls[1][1]).toMatchObject({ signal: controller.signal });
  });

  it("isolates attention keys and carries the query AbortSignal to the request", async () => {
    const unfiltered = caseQueryKeys.caseList(
      actor.user_id,
      undefined,
      "all",
      "highest_first",
      "TEAM_A",
    );
    const filtered = caseQueryKeys.caseList(
      actor.user_id,
      undefined,
      "all",
      "highest_first",
      "TEAM_A",
      "DOCUMENT_LOW_CONFIDENCE",
    );
    expect(filtered).not.toEqual(unfiltered);
    expect(filtered).not.toEqual(caseQueryKeys.caseList(
      actor.user_id,
      undefined,
      "all",
      "highest_first",
      "TEAM_B",
      "DOCUMENT_LOW_CONFIDENCE",
    ));

    let capturedSignal: AbortSignal | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) => {
      capturedSignal = init?.signal as AbortSignal;
      return new Promise<Response>((_resolve, reject) => {
        capturedSignal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
      });
    });
    const queryClient = createSessionQueryClient();
    const pending = queryClient.fetchQuery(caseListQueryOptions(
      actor.user_id,
      undefined,
      "all",
      "highest_first",
      "TEAM_A",
      "DOCUMENT_LOW_CONFIDENCE",
    ));
    await vi.waitFor(() => expect(capturedSignal).toBeDefined());
    await queryClient.cancelQueries({ queryKey: filtered, exact: true });
    await Promise.allSettled([pending]);
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("cancels and removes a deleted case from every attention variant only for that user", async () => {
    const queryClient = createSessionQueryClient();
    const all = caseQueryKeys.caseList(actor.user_id, undefined, "all", "highest_first");
    const lowConfidence = caseQueryKeys.caseList(
      actor.user_id,
      undefined,
      "all",
      "highest_first",
      undefined,
      "DOCUMENT_LOW_CONFIDENCE",
    );
    const otherUser = caseQueryKeys.caseList(
      "other-user",
      undefined,
      "all",
      "highest_first",
      undefined,
      "DOCUMENT_LOW_CONFIDENCE",
    );
    queryClient.setQueryData(all, [blocked]);
    queryClient.setQueryData(lowConfidence, [blocked]);
    queryClient.setQueryData(otherUser, [blocked]);

    await caseDeletedEffect(queryClient, actor.user_id, blocked.case_id);

    expect(queryClient.getQueryData(all)).toEqual([]);
    expect(queryClient.getQueryData(lowConfidence)).toEqual([]);
    expect(queryClient.getQueryData(otherUser)).toEqual([blocked]);
  });

  it("retires assignment and renders truthful chips, empty state, count, and native Open links", async () => {
    const queryClient = createSessionQueryClient();
    queryClient.setQueryData(caseQueryKeys.casePortfolio(actor.user_id, {
      priority: "all",
      prioritySort: "highest_first",
      teamFilter: "all",
      offset: 0,
      limit: 50,
    }), { items: [blocked, recovery], offset: 0, limit: 50, has_more: false });
    queryClient.setQueryData(caseQueryKeys.casePortfolio(actor.user_id, {
      priority: "all",
      prioritySort: "highest_first",
      teamFilter: "all",
      attentionType: "DOCUMENT_LOW_CONFIDENCE",
      offset: 0,
      limit: 50,
    }), { items: [blocked], offset: 0, limit: 50, has_more: false });

    function Harness() {
      const [presentation, setPresentation] = useState<CaseQueuePresentationState>(
        DEFAULT_CASE_QUEUE_PRESENTATION,
      );
      return <CaseQueue actor={actor} presentation={presentation} onPresentationChange={setPresentation} />;
    }

    await act(async () => root?.render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}><Harness /></QueryClientProvider>
      </MemoryRouter>,
    ));

    expect(container?.textContent).toContain("Needs attention");
    expect(container?.textContent).not.toContain("Assigned to");
    expect(container?.textContent).toContain("Document low confidence");
    expect(container?.textContent).toContain("Ownership cycle");
    expect(container?.textContent).toContain("Zero-touch");
    expect(container?.textContent).not.toContain("3 open · 0 human");
    const attentionCells = Array.from(container?.querySelectorAll("tbody tr") ?? [])
      .map((row) => row.querySelectorAll("td")[7]?.textContent);
    expect(attentionCells).toContain("—");
    expect(mapZeroTouchCaseToCaseRow(blocked)).not.toHaveProperty("assigned_to");
    expect(container?.querySelector<HTMLAnchorElement>("a")?.getAttribute("href"))
      .toBe(`/cases/${blocked.case_id}`);

    const attentionLabel = Array.from(container?.querySelectorAll("label") ?? [])
      .find((label) => label.textContent === "Needs attention");
    const attentionSelect = attentionLabel
      ? container?.querySelector<HTMLSelectElement>(`#${attentionLabel.htmlFor}`)
      : null;
    expect(attentionSelect?.querySelectorAll("option")).toHaveLength(
      BUSINESS_EXCEPTION_TYPES.length + 1,
    );
    await act(async () => {
      if (!attentionSelect) return;
      attentionSelect.value = "DOCUMENT_LOW_CONFIDENCE";
      attentionSelect.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(attentionSelect?.value).toBe("DOCUMENT_LOW_CONFIDENCE");
    expect(container?.textContent).toContain("BLOCKED SYNTHETIC PTE. LTD.");
    expect(container?.textContent).not.toContain("RECOVERY SYNTHETIC PTE. LTD.");
  });
});
