// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchCasePortfolio, fetchZeroTouchCases } from "./api";
import { caseQueryKeys } from "./caseQueries";
import CaseQueue, {
  DEFAULT_CASE_QUEUE_PRESENTATION,
  type CaseQueuePresentationState,
} from "./pages/CaseQueue";
import { createSessionQueryClient } from "./queryClient";
import type { AuthenticatedProfile, ZeroTouchCaseListItem } from "./types";

const actor: AuthenticatedProfile = {
  user_id: "ethan-tan", display_name: "Ethan Tan", role: "RELATIONSHIP_MANAGER",
  team_id: "TEAM_A", team_display_name: "Alpha", team_type: "Corporate Client Onboarding",
  team_description: "Synthetic team", client_scope_label: "Alpha", capabilities: ["CASE_ACCESS"],
};
const completed: ZeroTouchCaseListItem = {
  case_id: "00000000-0000-4000-8000-000000006100", team_id: "TEAM_A",
  client_scope_label: "Alpha", priority: 8, requested_uen: "209900001A",
  legal_name: "SYNTHETIC DATE CASE", status: "COMPLETED", current_stage: "COMPLETE",
  updated_at: "2026-10-05T12:00:00Z", created_at: "2026-10-03T16:00:00Z",
  completed_at: "2026-10-05T12:00:00Z", active_exception_count: 0,
  active_exception_types: [], human_interventions: 0, final_outcome: null,
  resolved_jurisdiction: "SG", mock_goldtier_party_id: "SYNTHETIC-TARGET-1",
};

let root: Root;
let container: HTMLDivElement;
beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
    .IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.restoreAllMocks();
});

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200, headers: { "Content-Type": "application/json" },
  });
}

async function setDate(label: string, value: string): Promise<void> {
  const input = Array.from(container.querySelectorAll("label"))
    .find((element) => element.querySelector("span")?.textContent === label)
    ?.querySelector<HTMLInputElement>("input");
  expect(input).toBeDefined();
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, value);
    input?.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function CasesHarness() {
  const [presentation, setPresentation] = useState<CaseQueuePresentationState>(
    DEFAULT_CASE_QUEUE_PRESENTATION,
  );
  return <CaseQueue actor={actor} presentation={presentation} onPresentationChange={setPresentation} />;
}

async function waitForText(text: string): Promise<void> {
  await vi.waitFor(async () => {
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });
    expect(container.textContent).toContain(text);
  });
}

describe("S1 Singapore creation-date filters", () => {
  it("serializes dates without browser timezone conversion and retains AbortSignal on both APIs", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => (
      jsonResponse(String(input).includes("case-portfolio")
        ? { items: [], offset: 0, limit: 50, has_more: false }
        : [])
    ));
    const controller = new AbortController();
    await fetchCasePortfolio({
      priority: "all", prioritySort: "highest_first", teamFilter: "TEAM_A",
      createdFrom: "2026-10-04", createdTo: "2026-10-05",
    }, controller.signal);
    await fetchZeroTouchCases(
      "COMPLETED", "all", "highest_first", "TEAM_A", controller.signal,
      undefined, "2026-10-04", "2026-10-05",
    );
    for (const [input, options] of request.mock.calls) {
      const url = new URL(String(input), "http://localhost");
      expect(url.searchParams.get("created_from")).toBe("2026-10-04");
      expect(url.searchParams.get("created_to")).toBe("2026-10-05");
      expect(url.searchParams.get("team_filter")).toBe("TEAM_A");
      expect(options).toMatchObject({ signal: controller.signal });
    }
  });

  it("isolates creation-date query identities with actor and team scope", () => {
    const filters = {
      priority: "all" as const, prioritySort: "highest_first" as const,
      teamFilter: "TEAM_A", createdFrom: "2026-10-04", createdTo: "2026-10-05",
    };
    const key = caseQueryKeys.casePortfolio(actor.user_id, filters);
    for (const changed of [
      { ...filters, createdFrom: "2026-10-03" },
      { ...filters, createdTo: "2026-10-06" },
      { ...filters, teamFilter: "TEAM_B" },
    ]) expect(caseQueryKeys.casePortfolio(actor.user_id, changed)).not.toEqual(key);
    expect(caseQueryKeys.casePortfolio("other-user", filters)).not.toEqual(key);
    const legacy = (from?: string, to?: string) => caseQueryKeys.caseList(
      actor.user_id, "COMPLETED", "all", "highest_first", "TEAM_A", undefined, from, to,
    );
    expect(legacy("2026-10-04", "2026-10-05")).not.toEqual(legacy("2026-10-03", "2026-10-05"));
    expect(legacy("2026-10-04", "2026-10-05")).not.toEqual(legacy("2026-10-04", "2026-10-06"));
  });

  it("Cases resets paging and requests server-created bounds when either date changes", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = new URL(String(input), "http://localhost");
      return jsonResponse({
        items: [completed], offset: Number(url.searchParams.get("offset") ?? 0),
        limit: 50, has_more: !url.searchParams.has("offset"),
      });
    });
    await act(async () => root.render(
      <MemoryRouter><QueryClientProvider client={createSessionQueryClient()}>
        <CasesHarness />
      </QueryClientProvider></MemoryRouter>,
    ));
    await waitForText("SYNTHETIC DATE CASE");
    const next = Array.from(container.querySelectorAll("button"))
      .find((button) => button.textContent === "Next");
    await act(async () => next?.click());
    await waitForText("Page 2");
    await setDate("Created from", "2026-10-04");
    await setDate("Created to", "2026-10-04");
    await waitForText("Page 1");
    const url = new URL(String(request.mock.lastCall?.[0]), "http://localhost");
    expect(url.searchParams.get("created_from")).toBe("2026-10-04");
    expect(url.searchParams.get("created_to")).toBe("2026-10-04");
    expect(url.searchParams.has("offset")).toBe(false);
    expect(container.textContent).toContain("Asia/Singapore, UTC+08:00");
  });

  it.each(["Cases"])("%s cancels an old date request and rejects its late response", async (page) => {
    let releaseOldResponse: ((response: Response) => void) | undefined;
    let oldSignal: AbortSignal | undefined;
    const result = (name: string) => page === "Cases"
      ? { items: [{ ...completed, legal_name: name }], offset: 0, limit: 50, has_more: false }
      : [{ ...completed, legal_name: name }];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, options) => {
      const url = new URL(String(input), "http://localhost");
      if (url.searchParams.get("created_from") === "2026-10-04") {
        oldSignal = options?.signal as AbortSignal;
        return new Promise<Response>((resolve) => { releaseOldResponse = resolve; });
      }
      return jsonResponse(result(url.searchParams.has("created_from") ? "NEW RANGE" : "INITIAL RANGE"));
    });
    await act(async () => root.render(
      <MemoryRouter><QueryClientProvider client={createSessionQueryClient()}>
        <CasesHarness />
      </QueryClientProvider></MemoryRouter>,
    ));
    await waitForText("INITIAL RANGE");
    await setDate("Created from", "2026-10-04");
    expect(releaseOldResponse).toBeDefined();
    await setDate("Created from", "2026-10-05");
    await waitForText("NEW RANGE");
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => releaseOldResponse?.(jsonResponse(result("LATE OLD RANGE"))));
    await waitForText("NEW RANGE");
    expect(container.textContent).not.toContain("LATE OLD RANGE");
  });
});
