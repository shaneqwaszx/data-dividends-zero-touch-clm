// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { caseQueryKeys } from "./caseQueries";
import { WorkspaceTabs } from "./navigation";
import CaseQueue, { DEFAULT_CASE_QUEUE_PRESENTATION, type CaseQueuePresentationState } from "./pages/CaseQueue";
import { createSessionQueryClient } from "./queryClient";
import type { AuthenticatedProfile, ZeroTouchCaseListItem } from "./types";

const actor: AuthenticatedProfile = {
  user_id: "maya-lim",
  display_name: "Maya Lim",
  role: "CLIENT_ONBOARDER",
  team_id: "TEAM_A",
  team_display_name: "Alpha",
  team_type: "Corporate Client Onboarding",
  team_description: "Synthetic team",
  client_scope_label: "Alpha",
  capabilities: ["CASE_ACCESS"],
} as AuthenticatedProfile;

const FILTERS = { priority: "all" as const, prioritySort: "highest_first" as const, teamFilter: "all", offset: 0, limit: 50 };

function item(index: number, human: number, types: ZeroTouchCaseListItem["active_exception_types"] = []): ZeroTouchCaseListItem {
  return {
    case_id: `00000000-0000-4000-8000-00000000030${index}`,
    team_id: "TEAM_A",
    client_scope_label: "Alpha",
    priority: null,
    requested_uen: `20999010${index}A`,
    legal_name: `DEMO CASE ${index} PTE. LTD.`,
    status: types.length ? "WAITING_FOR_REVIEW" : "COMPLETED",
    current_stage: "READINESS",
    updated_at: "2026-10-29T08:00:00Z",
    active_exception_count: types.length,
    active_exception_types: types,
    human_interventions: human,
    final_outcome: null,
    resolved_jurisdiction: "SG",
    created_at: "2026-10-29T07:00:00Z",
    completed_at: null,
    mock_goldtier_party_id: null,
  };
}

const ITEMS = [item(1, 0), item(2, 1, ["TARGET_CONFIRMATION_REQUIRED"]), item(3, 3)];

let root: Root | null = null;
let container: HTMLDivElement | null = null;

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.restoreAllMocks();
});

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

async function renderCases(observedAt = new Date().toISOString()) {
  const queryClient = createSessionQueryClient();
  queryClient.setQueryData(caseQueryKeys.casePortfolio(actor.user_id, FILTERS), {
    items: ITEMS, offset: 0, limit: 50, has_more: false, observed_at: observedAt,
  });
  await act(async () => root?.render(
    <MemoryRouter><QueryClientProvider client={queryClient}>
      <CaseQueue actor={actor} presentation={DEFAULT_CASE_QUEUE_PRESENTATION} onPresentationChange={() => undefined} />
    </QueryClientProvider></MemoryRouter>,
  ));
  return queryClient;
}

function rowCells(index: number): HTMLTableCellElement[] {
  return Array.from(container!.querySelectorAll("tbody tr")[index].querySelectorAll("td"));
}

function headers(): string[] {
  return Array.from(container!.querySelectorAll("thead th")).map((cell) => cell.textContent ?? "");
}

describe("Autoboard logo", () => {
  it("links to the profile's landing page", async () => {
    await act(async () => root?.render(<MemoryRouter><WorkspaceTabs actor={actor} retainedIntakeCaseId={null} /></MemoryRouter>));
    const brand = container!.querySelector<HTMLAnchorElement>("a.nav-brand");
    expect(brand?.getAttribute("aria-label")).toBe("Autoboard home");
    expect(brand?.getAttribute("href")).toBe("/dashboard");
    expect(brand?.textContent).toBe("Autoboard");
  });

  it("stays plain text when the profile has no landing page", async () => {
    const nowhere = { ...actor, capabilities: [] } as AuthenticatedProfile;
    await act(async () => root?.render(<MemoryRouter><WorkspaceTabs actor={nowhere} retainedIntakeCaseId={null} /></MemoryRouter>));
    expect(container!.querySelector("a.nav-brand")).toBeNull();
    expect(container!.querySelector("span.nav-brand")?.textContent).toBe("Autoboard");
  });
});

describe("Cases page top", () => {
  it("orders the labelled filters with Search first and shows the new intro", async () => {
    await renderCases();
    const labels = Array.from(container!.querySelectorAll(".case-filters .case-filter > label, .case-filters .case-filter__label"))
      .map((label) => label.textContent);
    expect(labels).toEqual(["Search", "Status", "Priority", "Needs attention", "Jurisdiction", "Created between", "Sort"]);
    for (const label of container!.querySelectorAll<HTMLLabelElement>(".case-filter > label")) {
      expect(container!.querySelector(`#${label.htmlFor}`)).not.toBeNull();
    }
    expect(container!.querySelector<HTMLInputElement>("#case-filter-search")?.placeholder).toBe("Company, UEN or case ID");
    expect(container!.querySelector(".case-search-field svg")?.getAttribute("aria-hidden")).toBe("true");
    expect(container!.textContent).toContain(
      "Every case you can access, including completed ones. One customer may have more than one case.",
    );
  });

  it("shows only the range and an updated time with a working Refresh", async () => {
    const observedAt = new Date().toISOString();
    await renderCases(observedAt);
    expect(container!.textContent).toContain("Showing 1–3");
    expect(container!.textContent).not.toContain("on page 1.");
    expect(container!.textContent).not.toContain("Total results are not calculated");
    expect(container!.textContent).not.toContain("Timing observed at");
    const updated = Array.from(container!.querySelectorAll<HTMLElement>("[title]"))
      .find((element) => element.textContent?.startsWith("Updated "));
    expect(updated?.textContent).toBe("Updated just now");
    expect(updated?.title).not.toBe("");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ items: ITEMS, offset: 0, limit: 50, has_more: false, observed_at: observedAt }),
    );
    const refresh = Array.from(container!.querySelectorAll("button")).find((button) => button.textContent === "Refresh")!;
    await act(async () => refresh.click());
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/clm/zero-touch/case-portfolio"))).toHaveLength(1);
  });

  it("says how long ago an older observation was made", async () => {
    await renderCases(new Date(Date.now() - 5 * 60_000).toISOString());
    expect(container!.textContent).toMatch(/Updated 5m(?: \d+s)? ago/);
  });
});

describe("Cases table", () => {
  it("keeps every other column and renames only Needs attention", async () => {
    await renderCases();
    expect(headers()).toEqual([
      "Company", "Registration ID", "Jurisdiction", "Status", "Priority", "Client scope", "Stage",
      "Needs attention", "Created", "Updated", "Operational timing", "Action",
    ]);
  });

  it("shows Zero-touch or the number of manual steps, without the open count", async () => {
    await renderCases();
    expect(rowCells(0)[3].querySelector("strong")?.textContent).toBe("Zero-touch");
    expect(rowCells(1)[3].textContent).toContain("1 manual step");
    expect(rowCells(1)[3].textContent).not.toContain("1 manual steps");
    expect(rowCells(2)[3].textContent).toContain("3 manual steps");
    expect(container!.textContent).not.toMatch(/\d+ open · \d+ human/);
  });

  it("shows a dash when nothing needs attention", async () => {
    await renderCases();
    expect(rowCells(0)[7].textContent).toBe("—");
    expect(rowCells(1)[7].textContent).toBe("Target confirmation required");
    expect(container!.textContent).not.toContain("No open business exceptions recorded");
  });

  it("saves priority on change with one request and no Set button or badge", async () => {
    await renderCases();
    const cell = rowCells(1)[4];
    expect(cell.querySelector("button")).toBeNull();
    expect(cell.querySelector(".priority-badge")).toBeNull();
    expect(cell.querySelector(".sr-only")?.textContent).toBe("Priority for DEMO CASE 2 PTE. LTD.");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => (
      String(url).endsWith("/priority") ? json({ case_id: ITEMS[1].case_id, priority: 10 }) : json({ items: ITEMS, offset: 0, limit: 50, has_more: false })
    ));
    const select = cell.querySelector<HTMLSelectElement>("select.priority-select")!;
    await act(async () => {
      select.value = "10";
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    const priorityCalls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/priority"));
    expect(priorityCalls).toHaveLength(1);
    expect(priorityCalls[0][1]?.method).toBe("PATCH");
    expect(JSON.parse(String(priorityCalls[0][1]?.body))).toEqual({ priority: 10 });
  });

  it("restores the saved priority and shows the error when saving fails", async () => {
    await renderCases();
    const cell = rowCells(1)[4];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: { code: "CASE_PRIORITY_FORBIDDEN", message: "Priority cannot be changed." } }, 403));
    const select = cell.querySelector<HTMLSelectElement>("select.priority-select")!;
    await act(async () => {
      select.value = "5";
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(select.value).toBe("");
    expect(cell.querySelector(".cell-note--attention")?.textContent).not.toBe("");
  });
});


describe("Show view and GoldTier ID", () => {
  function Harness() {
    const [presentation, setPresentation] = useState<CaseQueuePresentationState>(DEFAULT_CASE_QUEUE_PRESENTATION);
    return <CaseQueue actor={actor} presentation={presentation} onPresentationChange={setPresentation} />;
  }

  function viewButton(label: string): HTMLButtonElement {
    return Array.from(container!.querySelectorAll<HTMLButtonElement>(".case-view button")).find((button) => button.textContent === label)!;
  }

  async function renderStateful() {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => json({ items: ITEMS, offset: 0, limit: 50, has_more: false }));
    await act(async () => root?.render(
      <MemoryRouter><QueryClientProvider client={createSessionQueryClient()}><Harness /></QueryClientProvider></MemoryRouter>,
    ));
    const lastUrl = () => new URL(String(fetchMock.mock.lastCall?.[0]), "http://localhost");
    return { fetchMock, lastUrl };
  }

  it("offers All cases, In progress and Onboarded, with All selected", async () => {
    await renderStateful();
    const buttons = Array.from(container!.querySelectorAll<HTMLButtonElement>(".case-view button"));
    expect(buttons.map((button) => button.textContent)).toEqual(["All cases", "In progress", "Onboarded"]);
    expect(buttons.map((button) => button.getAttribute("aria-pressed"))).toEqual(["true", "false", "false"]);
    expect(container!.querySelector(".case-view [role='group']")?.getAttribute("aria-labelledby")).toBe("case-view-label");
  });

  it("asks the server for in-progress cases and never offers Completed there", async () => {
    const { lastUrl } = await renderStateful();
    expect(lastUrl().searchParams.has("progress")).toBe(false);
    await act(async () => viewButton("In progress").click());
    await vi.waitFor(() => expect(lastUrl().searchParams.get("progress")).toBe("in_progress"));
    const status = container!.querySelector<HTMLSelectElement>("#case-filter-status")!;
    expect(Array.from(status.options).map((option) => option.value)).not.toContain("COMPLETED");
    expect(status.disabled).toBe(false);
  });

  it("asks the server for onboarded cases and fixes Status to Completed", async () => {
    const { lastUrl } = await renderStateful();
    await act(async () => viewButton("Onboarded").click());
    await vi.waitFor(() => expect(lastUrl().searchParams.get("progress")).toBe("onboarded"));
    expect(lastUrl().searchParams.has("status")).toBe(false);
    const status = container!.querySelector<HTMLSelectElement>("#case-filter-status")!;
    expect(status.disabled).toBe(true);
    expect(status.value).toBe("COMPLETED");
    expect(viewButton("Onboarded").getAttribute("aria-pressed")).toBe("true");
  });

  it("shows the GoldTier ID under the company name only when there is one, and copies it", async () => {
    const onboarded = { ...item(4, 0), status: "COMPLETED" as const, mock_goldtier_party_id: "SYNTHETIC-GT-S3" };
    const queryClient = createSessionQueryClient();
    queryClient.setQueryData(caseQueryKeys.casePortfolio(actor.user_id, FILTERS), {
      items: [ITEMS[0], onboarded], offset: 0, limit: 50, has_more: false, observed_at: new Date().toISOString(),
    });
    await act(async () => root?.render(
      <MemoryRouter><QueryClientProvider client={queryClient}>
        <CaseQueue actor={actor} presentation={DEFAULT_CASE_QUEUE_PRESENTATION} onPresentationChange={() => undefined} />
      </QueryClientProvider></MemoryRouter>,
    ));
    expect(rowCells(0)[0].querySelector(".case-goldtier-id")).toBeNull();
    const company = rowCells(1)[0];
    expect(company.textContent).toContain("DEMO CASE 4 PTE. LTD.");
    expect(company.querySelector("code")?.textContent).toBe("SYNTHETIC-GT-S3");
    const writeText = vi.fn(async () => undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    const copy = company.querySelector<HTMLButtonElement>("button")!;
    expect(copy.getAttribute("aria-label")).toBe("Copy GoldTier ID for DEMO CASE 4 PTE. LTD.");
    await act(async () => copy.click());
    expect(writeText).toHaveBeenCalledWith("SYNTHETIC-GT-S3");
    expect(copy.textContent).toBe("Copied");
  });
});
