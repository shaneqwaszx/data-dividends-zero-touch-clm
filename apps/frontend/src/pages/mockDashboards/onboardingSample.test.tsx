// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import Dashboard, { DashboardView } from "../Dashboard";
import { caseQueryKeys } from "../../caseQueries";
import { clearSessionQueries, createSessionQueryClient } from "../../queryClient";
import type { AuthenticatedProfile, AutomationStage, DashboardCaseItem, DashboardSnapshot } from "../../types";
import { buildSampleSnapshot, isSampleCaseId, SAMPLE_CASES, sampleCaseCount, sampleCaseIdFromUrlId, withOnboardingSample } from "./onboardingSample";

const maya: AuthenticatedProfile = {
  user_id: "maya-lim",
  display_name: "Maya Lim",
  role: "CLIENT_ONBOARDER",
  team_id: "TEAM_A",
  team_display_name: "DBS Corporate Onboarding",
  team_type: "Corporate Client Onboarding",
  team_description: "Type: Corporate Client Onboarding | Client coverage: DBS",
  client_scope_label: "DBS",
  capabilities: ["POLICY_VIEW", "CASE_ACCESS"],
};

const olivia: AuthenticatedProfile = {
  ...maya,
  user_id: "olivia-koh",
  display_name: "Olivia Koh",
  role: "DIRECTOR",
  team_id: null,
  team_display_name: null,
  team_type: null,
  team_description: "Global / cross-team access",
  client_scope_label: "Global / cross-team",
  capabilities: ["POLICY_VIEW", "POLICY_MUTATE", "CASE_ACCESS", "CASE_GLOBAL"],
};

const STAGES: AutomationStage[] = ["REGISTRY", "GOLDTIER_SEARCH", "DOCUMENT", "OWNERSHIP", "READINESS", "MOCK_GOLDTIER"];
const DAY = 86_400_000;

function weeksEnding(lastMonday: string): DashboardSnapshot["weekly_onboarded"] {
  const end = Date.parse(`${lastMonday}T00:00:00Z`);
  return Array.from({ length: 8 }, (_, index) => ({
    week_start: new Date(end - (7 - index) * 7 * DAY).toISOString().slice(0, 10),
    by_jurisdiction: {},
    unresolved_count: 0,
  }));
}

const LIVE_CASE: DashboardCaseItem = {
  case_id: "00000000-0000-4000-8000-000000000001",
  requested_uen: "202400001A",
  legal_name: "LIVE SYNTHETIC CLIENT",
  team_id: "TEAM_A",
  team_display_name: "DBS Corporate Onboarding",
  priority: 10,
  status: "COMPLETED",
  current_stage: "COMPLETE",
  progress_percent: 100,
  final_outcome: "MOCK_GOLDTIER_SUBMITTED",
  created_at: "2026-11-04T01:00:00Z",
  updated_at: "2026-11-04T01:10:00Z",
  completed_at: "2026-11-04T01:10:00Z",
  case_elapsed_ms: 600_000,
  delay_note: "Zero-touch",
  created_by_display_name: "Maya Lim",
};

function emptyLive(actor: AuthenticatedProfile, view: "team" | "mine" = "team"): DashboardSnapshot {
  return {
    historical_trend: [],
    scope: { actor_role: actor.role, access: actor.role === "DIRECTOR" ? "GLOBAL" : "TEAM", team_id: actor.team_id, team_display_name: actor.team_display_name, client_scope_label: actor.client_scope_label },
    view,
    data_as_of: "2026-11-05T03:00:00Z",
    totals: { total_cases: 0, completed_cases: 0, non_completed_cases: 0, completion_rate: 0, prioritised_cases: 0, unprioritised_cases: 0 },
    zero_touch_rate: 0,
    timing: { mean_total_duration_ms: null, zero_touch_mean_duration_ms: null, zero_touch_count: 0, blocked_mean_duration_ms: null, blocked_count: 0 },
    status_breakdown: (["PENDING_INPUTS", "RUNNING", "WAITING_FOR_REVIEW", "RESUMING", "RECOVERY_PENDING", "COMPLETED", "TECHNICAL_FAILURE"] as const).map((status) => ({ status, count: 0 })),
    priority_breakdown: [...Array.from({ length: 10 }, (_, index) => ({ priority: 10 - index, count: 0 })), { priority: null, count: 0 }],
    team_breakdown: [],
    stage_timing: STAGES.map((stage) => ({ stage, clean_mean_ms: null, clean_count: 0, with_blocker_mean_ms: null, with_blocker_count: 0, combined_mean_ms: null, blocked_count: 0, top_cases: [] })),
    exception_breakdown: [],
    weekly_onboarded: weeksEnding("2026-11-02"),
    workload_by_person: [],
    recent_cases: [],
    top_active_cases: [],
    scoped_cases: [],
  };
}

// One live completed zero-touch case created by Maya, with a resolved blocker fixed by Maya.
function liveWithOneCompletion(actor: AuthenticatedProfile = maya): DashboardSnapshot {
  const live = emptyLive(actor);
  live.totals = { total_cases: 1, completed_cases: 1, non_completed_cases: 0, completion_rate: 1, prioritised_cases: 1, unprioritised_cases: 0 };
  live.zero_touch_rate = 1;
  live.timing = { mean_total_duration_ms: 600_000, zero_touch_mean_duration_ms: 600_000, zero_touch_count: 1, blocked_mean_duration_ms: null, blocked_count: 0 };
  live.status_breakdown = live.status_breakdown.map((item) => ({ ...item, count: item.status === "COMPLETED" ? 1 : 0 }));
  live.stage_timing = live.stage_timing.map((row) => ({ ...row, clean_mean_ms: 60_000, clean_count: 1, combined_mean_ms: 60_000 }));
  live.exception_breakdown = [{ exception_type: "DOCUMENT_LOW_CONFIDENCE", count: 1 }];
  live.weekly_onboarded[7].by_jurisdiction = { SG: 1 };
  live.workload_by_person = [{ user_id: "maya-lim", display_name: "Maya Lim", open_cases: 0, oldest_open_age_ms: null, completed_cases: 1, blockers_resolved: 1, mean_fix_time_ms: 3_600_000 }];
  live.scoped_cases = [LIVE_CASE];
  return live;
}

const sum = (values: number[]) => values.reduce((total, value) => total + value, 0);
const weeklyTotal = (snapshot: DashboardSnapshot) => sum(snapshot.weekly_onboarded.map((week) => sum(Object.values(week.by_jurisdiction).map((count) => count ?? 0)) + week.unresolved_count));
const BLOCKED = ["WAITING_FOR_REVIEW", "RECOVERY_PENDING", "TECHNICAL_FAILURE"];

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("fixed Onboarding sample portfolio", () => {
  it.each(["team", "mine"] as const)("keeps every %s figure consistent with the sample cases", (view) => {
    const sample = buildSampleSnapshot(emptyLive(maya, view), maya);
    const cases = sample.scoped_cases;
    const completed = cases.filter((item) => item.status === "COMPLETED");
    expect(sample.totals.total_cases).toBe(cases.length);
    expect(sample.totals.total_cases).toBe(sampleCaseCount(view, maya));
    expect(sample.totals.completed_cases).toBe(completed.length);
    expect(sample.totals.non_completed_cases + sample.totals.completed_cases).toBe(sample.totals.total_cases);
    expect(sample.totals.prioritised_cases + sample.totals.unprioritised_cases).toBe(sample.totals.total_cases);
    expect(sum(sample.status_breakdown.map((item) => item.count))).toBe(sample.totals.total_cases);
    expect(sum(sample.priority_breakdown.map((item) => item.count))).toBe(sample.totals.total_cases);
    // Every completion falls inside the eight charted weeks.
    expect(weeklyTotal(sample)).toBe(sample.totals.completed_cases);
    expect(sample.timing.zero_touch_count + sample.timing.blocked_count).toBe(sample.totals.completed_cases);
    expect(sample.zero_touch_rate).toBeCloseTo(sample.timing.zero_touch_count / sample.totals.completed_cases);
    expect(completed.filter((item) => item.delay_note === "Zero-touch")).toHaveLength(sample.timing.zero_touch_count);
    // Every open blocked case names the blocker that stopped it.
    for (const item of cases.filter((entry) => BLOCKED.includes(entry.status))) expect(item.delay_note).toBeTruthy();
    for (const item of cases) {
      expect(isSampleCaseId(item.case_id)).toBe(true);
      expect(item.case_elapsed_ms).toBeGreaterThan(0);
      expect(item.case_elapsed_ms).toBeLessThan(30 * DAY);
      expect(item.progress_percent).toBe(item.status === "COMPLETED" ? 100 : item.progress_percent);
      expect(Date.parse(item.created_at)).toBeLessThanOrEqual(Date.parse(item.completed_at ?? item.updated_at));
      if (item.completed_at) expect(Date.parse(item.completed_at)).toBeLessThanOrEqual(Date.parse(sample.data_as_of));
    }
    expect(new Set(cases.map((item) => item.case_id)).size).toBe(cases.length);
    for (const row of sample.stage_timing) {
      expect(row.top_cases.length).toBeLessThanOrEqual(3);
      expect(row.clean_count + row.with_blocker_count).toBeLessThanOrEqual(cases.length);
      expect(row.with_blocker_count).toBeLessThanOrEqual(row.blocked_count);
    }
    expect(sum(sample.exception_breakdown.map((item) => item.count))).toBe(sum(SAMPLE_CASES.filter((item) => view === "team" || item.owner === "viewer").map((item) => item.blockers.length)));
  });

  it("splits the team portfolio across the workload table without gaps", () => {
    const sample = buildSampleSnapshot(emptyLive(maya), maya);
    const rows = sample.workload_by_person;
    expect(sum(rows.map((row) => row.open_cases))).toBe(sample.totals.non_completed_cases);
    expect(sum(rows.map((row) => row.completed_cases))).toBe(sample.totals.completed_cases);
    const resolved = sum(SAMPLE_CASES.map((item) => item.blockers.filter((blocker) => blocker.fix).length));
    expect(sum(rows.map((row) => row.blockers_resolved))).toBe(resolved);
    // The viewer's own sample cases are attributed to whoever is signed in.
    const mine = rows.find((row) => row.user_id === maya.user_id)!;
    const mineView = buildSampleSnapshot(emptyLive(maya, "mine"), maya);
    expect(mineView.workload_by_person).toEqual([mine]);
    expect(mine.open_cases).toBe(mineView.totals.non_completed_cases);
    expect(mine.completed_cases).toBe(mineView.totals.completed_cases);
  });

  it("shows the same sample figures to every user", () => {
    const strip = (snapshot: DashboardSnapshot) => ({
      totals: snapshot.totals,
      zero: snapshot.zero_touch_rate,
      timing: snapshot.timing,
      status: snapshot.status_breakdown,
      stages: snapshot.stage_timing,
      exceptions: snapshot.exception_breakdown,
      weekly: snapshot.weekly_onboarded,
      workload: snapshot.workload_by_person.map(({ user_id: _id, display_name: _name, ...numbers }) => numbers),
      cases: snapshot.scoped_cases.map(({ created_by_display_name: _name, ...item }) => item),
    });
    for (const view of ["team", "mine"] as const) {
      expect(strip(buildSampleSnapshot(emptyLive(maya, view), maya))).toEqual(strip(buildSampleSnapshot(emptyLive(olivia, view), olivia)));
    }
  });

  it("puts every sample case in the Alpha or Beta team", () => {
    const snapshot = buildSampleSnapshot(emptyLive(olivia, "team"), olivia);
    expect(snapshot.scoped_cases.length).toBeGreaterThan(0);
    for (const item of snapshot.scoped_cases) {
      expect([["TEAM_A", "Alpha"], ["TEAM_B", "Beta"]]).toContainEqual([item.team_id, item.team_display_name]);
    }
    expect(snapshot.team_breakdown.map((row) => row.team_display_name)).toEqual(["Alpha", "Beta"]);
    expect(snapshot.team_breakdown.reduce((sum, row) => sum + row.count, 0)).toBe(snapshot.scoped_cases.length);
  });

  it("adds live figures on top of the sample figures without changing the live snapshot", () => {
    const live = liveWithOneCompletion();
    const before = structuredClone(live);
    const sample = buildSampleSnapshot(live, maya);
    const merged = withOnboardingSample(live, maya);
    expect(live).toEqual(before);
    expect(merged.totals.total_cases).toBe(sample.totals.total_cases + 1);
    expect(merged.totals.completed_cases).toBe(sample.totals.completed_cases + 1);
    expect(merged.totals.non_completed_cases).toBe(sample.totals.non_completed_cases);
    expect(merged.zero_touch_rate).toBeCloseTo((sample.timing.zero_touch_count + 1) / (sample.totals.completed_cases + 1));
    expect(merged.timing.zero_touch_count).toBe(sample.timing.zero_touch_count + 1);
    expect(merged.timing.mean_total_duration_ms).toBe(Math.floor(
      (sample.timing.mean_total_duration_ms! * sample.totals.completed_cases + 600_000) / (sample.totals.completed_cases + 1),
    ));
    expect(sum(merged.status_breakdown.map((item) => item.count))).toBe(merged.totals.total_cases);
    expect(weeklyTotal(merged)).toBe(weeklyTotal(sample) + 1);
    expect(merged.weekly_onboarded.map((week) => week.week_start)).toEqual(live.weekly_onboarded.map((week) => week.week_start));
    expect(merged.scoped_cases[0]).toEqual(LIVE_CASE);
    expect(merged.scoped_cases).toHaveLength(sample.scoped_cases.length + 1);
    expect(merged.exception_breakdown.find((item) => item.exception_type === "DOCUMENT_LOW_CONFIDENCE")!.count)
      .toBe(sample.exception_breakdown.find((item) => item.exception_type === "DOCUMENT_LOW_CONFIDENCE")!.count + 1);
    const registry = merged.stage_timing.find((row) => row.stage === "REGISTRY")!;
    const sampleRegistry = sample.stage_timing.find((row) => row.stage === "REGISTRY")!;
    expect(registry.clean_count).toBe(sampleRegistry.clean_count + 1);
    expect(registry.combined_mean_ms).toBe(Math.floor(
      (sampleRegistry.combined_mean_ms! * (sampleRegistry.clean_count + sampleRegistry.with_blocker_count) + 60_000)
        / (sampleRegistry.clean_count + sampleRegistry.with_blocker_count + 1),
    ));
    // Maya's live row and her sample cases become one workload row.
    const mayaRows = merged.workload_by_person.filter((row) => row.user_id === maya.user_id);
    const sampleMaya = sample.workload_by_person.find((row) => row.user_id === maya.user_id)!;
    expect(mayaRows).toHaveLength(1);
    expect(mayaRows[0].completed_cases).toBe(sampleMaya.completed_cases + 1);
    expect(mayaRows[0].blockers_resolved).toBe(sampleMaya.blockers_resolved + 1);
    expect(mayaRows[0].mean_fix_time_ms).toBe(Math.floor(
      (sampleMaya.mean_fix_time_ms! * sampleMaya.blockers_resolved + 3_600_000) / (sampleMaya.blockers_resolved + 1),
    ));
  });

  it("returns exactly the sample figures when there is no live data yet", () => {
    const live = emptyLive(maya);
    const merged = withOnboardingSample(live, maya);
    const sample = buildSampleSnapshot(live, maya);
    expect(merged.totals).toEqual(sample.totals);
    expect(merged.timing).toEqual(sample.timing);
    expect(merged.stage_timing).toEqual(sample.stage_timing);
    expect(merged.weekly_onboarded).toEqual(sample.weekly_onboarded);
    expect(merged.workload_by_person).toEqual(sample.workload_by_person);
    expect(merged.scope).toEqual(live.scope);
    expect(merged.data_as_of).toBe(live.data_as_of);
  });
});

describe("Onboarding dashboard with sample cases", () => {
  const renderView = (dashboard: DashboardSnapshot, scope: "team" | "mine") => {
    const client = createSessionQueryClient();
    const markup = renderToStaticMarkup(<QueryClientProvider client={client}><MemoryRouter><DashboardView
      actor={maya} dashboard={dashboard} dashScope={scope} onScopeChange={() => undefined}
      dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all"
      onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
      sampleCases={sampleCaseCount(scope, maya)}
    /></MemoryRouter></QueryClientProvider>);
    client.clear();
    const container = document.createElement("div");
    container.innerHTML = markup;
    return container;
  };

  it("shows sample cases unmarked and links them to their read-only case page, live cases to case detail", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], offset: 0, limit: 10, has_more: false }))));
    const live = liveWithOneCompletion();
    // The oldest case sorts to the first page of All cases.
    live.scoped_cases = [{ ...LIVE_CASE, case_elapsed_ms: 29 * DAY }];
    const merged = withOnboardingSample(live, maya);
    const team = renderView(merged, "team");
    expect(team.textContent).not.toMatch(/sample/i);
    const kpis = Array.from(team.querySelectorAll("article.dashboard-kpi strong")).map((item) => item.textContent);
    expect(kpis[0]).toBe(String(merged.totals.non_completed_cases));
    expect(kpis[1]).toBe(String(merged.totals.completed_cases));
    const links = Array.from(team.querySelectorAll("a")).map((item) => item.getAttribute("href"));
    const isSampleLink = (href: string | null) => Boolean(href?.startsWith("/cases/") && sampleCaseIdFromUrlId(href.slice("/cases/".length)));
    expect(links.filter((href) => href?.startsWith("/cases/") && !isSampleLink(href))).toEqual([`/cases/${LIVE_CASE.case_id}`]);
    expect(links.filter(isSampleLink).length).toBeGreaterThan(0);
    expect(links.some((href) => href?.includes("sample"))).toBe(false);
    expect(team.querySelectorAll('[title*="sample" i]')).toHaveLength(0);

    const mine = renderView(withOnboardingSample(emptyLive(maya, "mine"), maya), "mine");
    expect(mine.textContent).not.toMatch(/sample/i);
    const blocked = Array.from(mine.querySelectorAll("article")).find((item) => item.querySelector("h2")?.textContent === "Blocked cases")!;
    expect(blocked.querySelectorAll(".blocked-case-row").length).toBeGreaterThan(0);
    const blockedLinks = Array.from(blocked.querySelectorAll("a")).map((item) => item.getAttribute("href"));
    expect(blockedLinks.length).toBeGreaterThan(0);
    expect(blockedLinks.every(isSampleLink)).toBe(true);
  });

  it("adds the sample on top of the live backend response without touching storage or the query cache", async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const storage = { getItem: vi.fn(), setItem: vi.fn(), removeItem: vi.fn() };
    vi.stubGlobal("localStorage", storage);
    vi.stubGlobal("sessionStorage", storage);
    const live = liveWithOneCompletion();
    live.totals.non_completed_cases = 2;
    live.totals.total_cases = 3;
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(live))));
    const client = createSessionQueryClient();
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    const settle = async () => { await act(async () => { await new Promise((resolve) => setTimeout(resolve, 20)); }); };
    try {
      await act(async () => root.render(<QueryClientProvider client={client}><MemoryRouter><Dashboard actor={maya} /></MemoryRouter></QueryClientProvider>));
      await settle();
      const sampleOpen = SAMPLE_CASES.filter((item) => item.status !== "COMPLETED").length;
      const card = container.querySelector(".category-card--live")!;
      expect(card.textContent).toContain(`${2 + sampleOpen} open`);
      expect(card.textContent).not.toMatch(/sample/i);
      expect(client.getQueryData(caseQueryKeys.dashboard(maya.user_id, "all", "team", "30d"))).toEqual(live);
      expect(storage.getItem).not.toHaveBeenCalled();
      expect(storage.setItem).not.toHaveBeenCalled();
      await act(async () => (card as HTMLElement).click());
      await settle();
      expect(container.textContent).toContain("Onboarding Dashboard");
      expect(container.textContent).not.toMatch(/sample/i);
    } finally {
      await act(async () => root.unmount());
      clearSessionQueries(client);
      container.remove();
    }
  });
});
