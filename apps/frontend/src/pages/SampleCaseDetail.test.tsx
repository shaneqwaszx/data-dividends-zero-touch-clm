// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { caseQueryKeys } from "../caseQueries";
import { parseCaseId, paths, requiredCapabilityForPath } from "../navigation";
import { createSessionQueryClient } from "../queryClient";
import type { AuthenticatedProfile, ZeroTouchCaseListItem } from "../types";
import CaseQueue, { DEFAULT_CASE_QUEUE_PRESENTATION, filterSampleCases } from "./CaseQueue";
import SampleCaseDetail from "./SampleCaseDetail";
import { SAMPLE_CASES, sampleCaseDetail, sampleCaseIdFromUrlId, sampleCaseRows, sampleCaseUrlId } from "./mockDashboards/onboardingSample";

const maya: AuthenticatedProfile = {
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

const olivia: AuthenticatedProfile = {
  ...maya,
  user_id: "olivia-koh",
  display_name: "Olivia Koh",
  role: "DIRECTOR",
  team_id: null,
  team_display_name: null,
  client_scope_label: "Global / cross-team",
  capabilities: ["CASE_ACCESS", "CASE_GLOBAL"],
} as AuthenticatedProfile;

const AS_OF = Date.parse("2026-11-04T10:00:00Z"); // a Wednesday
// An onboarder or relationship manager sees only their own team's sample cases (Alpha for Maya).
// Her own cases plus Ethan Tan's; Ryan Lee's are in Beta.
const MAYA_VISIBLE = SAMPLE_CASES.filter((item) => item.owner !== "ryan").length;
const ALL_FILTERS = {
  view: "all" as const, status: "", priority: "all" as const, prioritySort: "highest_first" as const,
  jurisdiction: "", search: "", attentionType: "", createdFrom: "", createdTo: "",
};

describe("sample case data outside the dashboard", () => {
  it("lists every sample case once for a Director, with dates placed before the as-of time", () => {
    const rows = sampleCaseRows(olivia, AS_OF);
    expect(rows).toHaveLength(SAMPLE_CASES.length);
    expect(new Set(rows.map((row) => row.case_id)).size).toBe(SAMPLE_CASES.length);
    for (const row of rows) {
      expect(Date.parse(row.created_at)).toBeLessThanOrEqual(AS_OF);
      if (row.completed_at) expect(Date.parse(row.completed_at)).toBeLessThanOrEqual(AS_OF);
    }
  });

  it("shows an onboarder only their own team's sample cases, like the backend case scope", () => {
    const rows = sampleCaseRows(maya, AS_OF);
    expect(rows).toHaveLength(MAYA_VISIBLE);
    expect(rows.length).toBeLessThan(SAMPLE_CASES.length);
    expect(rows.every((row) => row.team_id === "TEAM_A")).toBe(true);
    const otherTeam = sampleCaseRows(olivia, AS_OF).find((row) => row.created_by_display_name === "Ryan Lee")!;
    expect(otherTeam.team_id).toBe("TEAM_B");
    expect(sampleCaseDetail(otherTeam.case_id, maya, AS_OF)).toBeNull();
    expect(sampleCaseDetail(otherTeam.case_id, olivia, AS_OF)).not.toBeNull();
  });

  it("returns null for an ID that is not a sample case", () => {
    expect(sampleCaseDetail("sample-9999", maya, AS_OF)).toBeNull();
    expect(sampleCaseDetail("00000000-0000-4000-8000-000000000001", maya, AS_OF)).toBeNull();
  });

  it("describes a completed case: every step done and resolved blockers named", () => {
    const detail = sampleCaseDetail("sample-0015", maya, AS_OF)!;
    expect(detail.legal_name).toBe("Raffles Row Partners Pte. Ltd.");
    expect(detail.status).toBe("COMPLETED");
    expect(detail.steps.every((step) => step.state === "done" && step.duration_ms !== null)).toBe(true);
    expect(detail.blockers).toHaveLength(2);
    expect(detail.blockers.every((blocker) => blocker.resolved && blocker.resolved_by === "Ethan Tan")).toBe(true);
  });

  it("describes an open case stopped for review with its open blocker", () => {
    const detail = sampleCaseDetail("sample-0041", maya, AS_OF)!;
    expect(detail.status).toBe("WAITING_FOR_REVIEW");
    expect(detail.steps.map((step) => step.state)).toEqual(["done", "done", "review", "not_started", "not_started", "not_started"]);
    expect(detail.open_blocker_types).toEqual(["DOCUMENT_LOW_CONFIDENCE"]);
    expect(detail.blockers[0]).toMatchObject({ resolved: false, fix_ms: null, resolved_by: null });
  });

  it("marks running and waiting-for-input steps without a recorded time", () => {
    const running = sampleCaseDetail("sample-0035", olivia, AS_OF)!;
    expect(running.steps.find((step) => step.stage === "DOCUMENT")).toMatchObject({ state: "in_progress", duration_ms: null });
    const pending = sampleCaseDetail("sample-0037", olivia, AS_OF)!;
    expect(pending.steps.find((step) => step.stage === "DOCUMENT")).toMatchObject({ state: "waiting_inputs", duration_ms: null });
  });

  it("gives the signed-in user's cases to the signed-in user", () => {
    expect(sampleCaseDetail("sample-0036", maya, AS_OF)!.created_by_display_name).toBe("Maya Lim");
  });
});

describe("sample case addresses", () => {
  it("gives sample cases ordinary case addresses that map back to the sample case", () => {
    const path = paths.sampleCaseDetail("sample-0041");
    expect(path).toMatch(/^\/cases\/[0-9a-f-]{36}$/);
    expect(path).not.toMatch(/sample/i);
    const urlId = path.slice("/cases/".length);
    expect(parseCaseId(urlId)).toBe(urlId);
    expect(sampleCaseIdFromUrlId(urlId)).toBe("sample-0041");
    expect(sampleCaseUrlId("sample-0041")).toBe(urlId);
    expect(requiredCapabilityForPath(path)).toBe("CASE_ACCESS");
    expect(paths.sampleCaseDetail("not-a-sample")).toBe("/cases");
  });

  it("does not treat backend case IDs as sample cases", () => {
    expect(sampleCaseIdFromUrlId("00000000-0000-4000-8000-000000000001")).toBeNull();
    expect(sampleCaseUrlId("00000000-0000-4000-8000-000000000001")).toBeNull();
  });
});

describe("read-only sample case page", () => {
  const renderPage = (id: string, actor: AuthenticatedProfile = maya) => renderToStaticMarkup(
    <MemoryRouter><SampleCaseDetail sampleCaseId={id} actor={actor} /></MemoryRouter>,
  );

  it("shows the case summary, steps and blockers with no actions", () => {
    const markup = renderPage("sample-0041");
    expect(markup).toContain("Hougang Pet Supplies Pte. Ltd.");
    expect(markup).toContain("201713380T");
    expect(markup).not.toMatch(/sample/i);
    expect(markup).toContain("Stopped for review");
    expect(markup).toContain("Open");
    // Buttons only open steps and sections or expand blockers; there are no case actions.
    const page = new DOMParser().parseFromString(markup, "text/html");
    const sectionToggles = new Set(page.querySelectorAll(".stage-disclosure > h2 > button"));
    expect(sectionToggles.size).toBeGreaterThan(0);
    for (const button of Array.from(page.querySelectorAll("button")).filter((item) => !sectionToggles.has(item))) {
      expect(button.getAttribute("aria-label") ?? button.textContent).toMatch(/^(Open details for |Open case stage details$|Show all issues$|\d+ blockers?$|\d+ items?$|Blocker: )/);
    }
    expect(markup.match(/<a /g)).toHaveLength(1); // only the way back to Cases
  });

  it("does not mark any case as sample data", () => {
    for (const id of ["sample-0001", "sample-0003", "sample-0037", "sample-0046"]) {
      expect(renderPage(id, olivia)).not.toMatch(/sample|illustrative|demonstration|mock/i);
    }
  });

  it("says when the sample case does not exist", () => {
    expect(renderPage("sample-9999")).toContain("Case not found");
  });
});

describe("Cases tab sample cases", () => {
  it("applies the Cases tab filters other than team", () => {
    const rows = sampleCaseRows(olivia, AS_OF);
    expect(filterSampleCases(rows, ALL_FILTERS)).toHaveLength(SAMPLE_CASES.length);
    const completed = SAMPLE_CASES.filter((item) => item.status === "COMPLETED").length;
    expect(filterSampleCases(rows, { ...ALL_FILTERS, view: "onboarded" })).toHaveLength(completed);
    expect(filterSampleCases(rows, { ...ALL_FILTERS, view: "in_progress" })).toHaveLength(SAMPLE_CASES.length - completed);
    expect(filterSampleCases(rows, { ...ALL_FILTERS, search: "hougang" }).map((row) => row.case_id)).toEqual(["sample-0041"]);
    expect(filterSampleCases(rows, { ...ALL_FILTERS, search: "201713380t" }).map((row) => row.case_id)).toEqual(["sample-0041"]);
    expect(filterSampleCases(rows, { ...ALL_FILTERS, jurisdiction: "AU" }).every((row) => row.jurisdiction === "AU")).toBe(true);
    expect(filterSampleCases(rows, { ...ALL_FILTERS, attentionType: "REGISTRY_REVIEW_REQUIRED" }).map((row) => row.case_id)).toEqual(["sample-0045"]);
    expect(filterSampleCases(rows, { ...ALL_FILTERS, priority: "unset" }).every((row) => row.priority === null)).toBe(true);
    const sorted = filterSampleCases(rows, { ...ALL_FILTERS, priority: "prioritised" }).map((row) => row.priority!);
    expect(sorted).toEqual([...sorted].sort((a, b) => b - a));
  });

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
    vi.restoreAllMocks();
  });

  const FIRST_PAGE = { priority: "all" as const, prioritySort: "highest_first" as const, teamFilter: "all", offset: 0, limit: 10 };
  const seedPage = (queryClient: ReturnType<typeof createSessionQueryClient>, offset: number, items: ZeroTouchCaseListItem[], hasMore: boolean) => {
    queryClient.setQueryData(caseQueryKeys.casePortfolio(maya.user_id, { ...FIRST_PAGE, offset }), {
      items, offset, limit: 10, has_more: hasMore, observed_at: new Date().toISOString(),
    });
  };
  const liveItem = (index: number): ZeroTouchCaseListItem => ({
    case_id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
    team_id: "TEAM_A",
    client_scope_label: "Alpha",
    priority: 10,
    requested_uen: `2024${String(index).padStart(5, "0")}A`,
    legal_name: `LIVE ${index} PTE. LTD.`,
    status: "RUNNING",
    current_stage: "DOCUMENT",
    updated_at: "2026-11-04T09:00:00Z",
    active_exception_count: 0,
    active_exception_types: [],
    human_interventions: 0,
    final_outcome: null,
    resolved_jurisdiction: "SG",
    created_at: "2026-11-04T08:00:00Z",
    completed_at: null,
    mock_goldtier_party_id: null,
  });
  const renderQueue = async (queryClient: ReturnType<typeof createSessionQueryClient>) => {
    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CaseQueue actor={maya} presentation={DEFAULT_CASE_QUEUE_PRESENTATION} onPresentationChange={() => undefined} />
        </MemoryRouter>
      </QueryClientProvider>,
    ));
  };
  const pageButton = (label: string) => Array.from(container!.querySelectorAll<HTMLButtonElement>("button"))
    .find((button) => button.textContent?.trim() === label)!;
  const pageLinks = () => Array.from(container!.querySelectorAll('[aria-label="Cases table"] tbody a'))
    .map((item) => item.getAttribute("href")!);
  const isSampleHref = (href: string) => sampleCaseIdFromUrlId(href.slice("/cases/".length)) !== null;

  it("lists sample cases after live cases ten per page, without marking them", async () => {
    const queryClient = createSessionQueryClient();
    for (let offset = 0; offset <= 40; offset += 10) seedPage(queryClient, offset, [], false);
    await renderQueue(queryClient);

    expect(container!.querySelectorAll('[aria-label="Cases table"] tbody tr')).toHaveLength(10);
    expect(container!.textContent).toContain("Showing 1–10");
    expect(container!.textContent).not.toContain("No cases match these filters.");
    expect(container!.textContent).not.toMatch(/sample/i);
    expect(pageButton("Previous").disabled).toBe(true);

    const seen = [...pageLinks()];
    const lastPage = Math.ceil(MAYA_VISIBLE / 10);
    for (let page = 2; page <= lastPage; page += 1) {
      const start = (page - 1) * 10 + 1;
      const end = Math.min(page * 10, MAYA_VISIBLE);
      const range = `${start}–${end}`;
      const rows = end - start + 1;
      await act(async () => pageButton("Next").click());
      expect(container!.textContent).toContain(`Page ${page}`);
      expect(container!.textContent).toContain(`Showing ${range}`);
      expect(pageLinks()).toHaveLength(rows);
      seen.push(...pageLinks());
    }
    expect(pageButton("Next").disabled).toBe(true);
    expect(seen).toHaveLength(MAYA_VISIBLE);
    expect(new Set(seen).size).toBe(MAYA_VISIBLE);
    expect(seen.every(isSampleHref)).toBe(true);

    await act(async () => pageButton("Previous").click());
    expect(container!.textContent).toContain(`Showing ${(lastPage - 2) * 10 + 1}–${(lastPage - 1) * 10}`);
  });

  it("fills the last live page with sample cases, then continues them on later pages", async () => {
    const queryClient = createSessionQueryClient();
    seedPage(queryClient, 0, Array.from({ length: 10 }, (_, index) => liveItem(index + 1)), true);
    seedPage(queryClient, 10, [11, 12, 13].map(liveItem), false);
    for (let offset = 20; offset <= 50; offset += 10) seedPage(queryClient, offset, [], false);
    await renderQueue(queryClient);

    expect(pageLinks()).toHaveLength(10);
    expect(pageLinks().some(isSampleHref)).toBe(false);

    await act(async () => pageButton("Next").click());
    expect(container!.textContent).toContain("Showing 11–20");
    const lastLivePage = pageLinks();
    expect(lastLivePage.filter((href) => !isSampleHref(href))).toHaveLength(3);
    expect(lastLivePage.filter(isSampleHref)).toHaveLength(7);
    // Live rows come first on the shared page.
    expect(lastLivePage.slice(0, 3).some(isSampleHref)).toBe(false);

    const seen = lastLivePage.filter(isSampleHref);
    while (!pageButton("Next").disabled) {
      await act(async () => pageButton("Next").click());
      expect(pageLinks().length).toBeLessThanOrEqual(10);
      seen.push(...pageLinks());
    }
    const total = 13 + MAYA_VISIBLE;
    expect(container!.textContent).toContain(`Showing ${Math.floor((total - 1) / 10) * 10 + 1}–${total}`);
    expect(seen).toHaveLength(MAYA_VISIBLE);
    expect(new Set(seen).size).toBe(MAYA_VISIBLE);
    expect(seen.every(isSampleHref)).toBe(true);
  });

  it("opens a step's section when the step is clicked, like a live case", async () => {
    await act(async () => root?.render(<MemoryRouter><SampleCaseDetail sampleCaseId="sample-0042" actor={olivia} /></MemoryRouter>));
    const sectionToggle = (title: string) => Array.from(container!.querySelectorAll<HTMLButtonElement>(".stage-disclosure > h2 > button"))
      .find((button) => button.textContent?.startsWith(title))!;
    // The blocked step's section starts open; a completed step's section starts closed.
    expect(sectionToggle("Ownership & UBO").getAttribute("aria-expanded")).toBe("true");
    expect(sectionToggle("Registry verification").getAttribute("aria-expanded")).toBe("false");
    const railButton = Array.from(container!.querySelectorAll<HTMLElement>(".ds-stage"))
      .find((stage) => stage.dataset.nodeId === "ACRA_REGISTRY")!
      .querySelector<HTMLButtonElement>("button")!;
    expect(railButton.textContent).toBe("Open case stage details");
    await act(async () => railButton.click());
    expect(sectionToggle("Registry verification").getAttribute("aria-expanded")).toBe("true");
  });

  it("keeps sample cases off pages that have more live cases after them", async () => {
    const queryClient = createSessionQueryClient();
    seedPage(queryClient, 0, [], true);
    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CaseQueue actor={maya} presentation={DEFAULT_CASE_QUEUE_PRESENTATION} onPresentationChange={() => undefined} />
        </MemoryRouter>
      </QueryClientProvider>,
    ));
    expect(container!.querySelector('[aria-label="Cases table"]')).toBeNull();
  });
});
