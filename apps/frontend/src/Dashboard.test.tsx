// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { WorkspaceTabs } from "./navigation";
import { configureAuthenticatedTransport, fetchDashboard } from "./api";
import Dashboard, { DashboardCategoryPicker, DashboardView } from "./pages/Dashboard";
import { clearSessionQueries, createSessionQueryClient } from "./queryClient";
import type { AuthenticatedProfile, AutomationStage, DashboardSnapshot } from "./types";

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

function snapshot(actor: AuthenticatedProfile, total = 2): DashboardSnapshot {
  const teamA = {
    case_id: "00000000-0000-4000-8000-000000000001",
    requested_uen: "202400001A",
    legal_name: "DBS SYNTHETIC CLIENT",
    team_id: "TEAM_A" as const,
    team_display_name: "DBS Corporate Onboarding",
    priority: 10,
    status: "RUNNING" as const,
    current_stage: "DOCUMENT" as const,
    progress_percent: 40,
    final_outcome: null,
    created_at: "2026-09-07T01:00:00Z",
    updated_at: "2026-09-08T01:00:00Z",
    completed_at: null,
    case_elapsed_ms: 93_600_000,
    delay_note: null,
    created_by_display_name: "Maya Lim",
  };
  const teamB = {
    ...teamA,
    case_id: "00000000-0000-4000-8000-000000000002",
    requested_uen: "202400007G",
    legal_name: "OCBC SYNTHETIC CLIENT",
    team_id: "TEAM_B" as const,
    team_display_name: "OCBC Corporate Onboarding",
    priority: null,
    status: "COMPLETED" as const,
    current_stage: "COMPLETE" as const,
    progress_percent: 100,
    final_outcome: "MOCK_GOLDTIER_SUBMITTED",
    completed_at: "2026-09-08T02:00:00Z",
    case_elapsed_ms: 90_000_000,
    delay_note: "Zero-touch",
    created_by_display_name: "Sophia Ng",
  };
  const cases = total === 0 ? [] : actor.role === "DIRECTOR" ? [teamA, teamB] : [teamA];
  const completedCount = cases.filter((item) => item.status === "COMPLETED").length;
  return {
    historical_trend: [],
    scope: {
      actor_role: actor.role,
      access: actor.role === "DIRECTOR" ? "GLOBAL" : "TEAM",
      team_id: actor.team_id,
      team_display_name: actor.team_display_name,
      client_scope_label: actor.client_scope_label,
    },
    view: "team",
    data_as_of: "2026-09-08T03:00:00Z",
    totals: {
      total_cases: total === 0 ? 0 : cases.length,
      completed_cases: total === 0 ? 0 : completedCount,
      non_completed_cases: total === 0 ? 0 : cases.length - completedCount,
      completion_rate: total === 0 ? 0 : completedCount / cases.length,
      prioritised_cases: total === 0 ? 0 : cases.filter((item) => item.priority !== null).length,
      unprioritised_cases: total === 0 ? 0 : cases.filter((item) => item.priority === null).length,
    },
    zero_touch_rate: total === 0 || completedCount === 0 ? 0 : 1,
    timing: {
      mean_total_duration_ms: total === 0 || completedCount === 0 ? null : 7_200_000,
      zero_touch_mean_duration_ms: total === 0 || completedCount === 0 ? null : 7_200_000,
      zero_touch_count: completedCount,
      blocked_mean_duration_ms: null,
      blocked_count: 0,
    },
    status_breakdown: [
      { status: "PENDING_INPUTS", count: 0 },
      { status: "RUNNING", count: cases.filter((item) => item.status === "RUNNING").length },
      { status: "WAITING_FOR_REVIEW", count: 0 },
      { status: "RESUMING", count: 0 },
      { status: "RECOVERY_PENDING", count: 0 },
      { status: "COMPLETED", count: completedCount },
      { status: "TECHNICAL_FAILURE", count: 0 },
    ],
    priority_breakdown: [...Array.from({ length: 10 }, (_, index) => ({ priority: 10 - index, count: 10 - index === 10 && cases.length ? 1 : 0 })), { priority: null, count: cases.some((item) => item.priority === null) ? 1 : 0 }],
    team_breakdown: actor.role === "DIRECTOR" ? [
      { team_id: "TEAM_A", team_display_name: "DBS Corporate Onboarding", client_scope_label: "DBS", count: 1 },
      { team_id: "TEAM_B", team_display_name: "OCBC Corporate Onboarding", client_scope_label: "OCBC", count: 1 },
    ] : [{ team_id: "TEAM_A", team_display_name: "DBS Corporate Onboarding", client_scope_label: "DBS", count: total === 0 ? 0 : 1 }],
    stage_timing: STAGES.map((stage) => ({
      stage,
      clean_mean_ms: null,
      clean_count: 0,
      with_blocker_mean_ms: null,
      with_blocker_count: 0,
      combined_mean_ms: null,
      blocked_count: 0,
      top_cases: [],
    })),
    exception_breakdown: [],
    weekly_onboarded: Array.from({ length: 8 }, (_, index) => ({
      week_start: `2026-0${8 - Math.floor(index / 4)}-${(index % 4) * 7 + 1}`.slice(0, 10),
      by_jurisdiction: {},
      unresolved_count: 0,
    })),
    workload_by_person: actor.role === "DIRECTOR"
      ? [
          { user_id: "maya-lim", display_name: "Maya Lim", open_cases: 1, oldest_open_age_ms: 86_400_000, completed_cases: 0, blockers_resolved: 0, mean_fix_time_ms: null },
          { user_id: "sophia-ng", display_name: "Sophia Ng", open_cases: 0, oldest_open_age_ms: null, completed_cases: 1, blockers_resolved: 0, mean_fix_time_ms: null },
        ]
      : (total === 0 ? [] : [{ user_id: "maya-lim", display_name: "Maya Lim", open_cases: 1, oldest_open_age_ms: 86_400_000, completed_cases: 0, blockers_resolved: 0, mean_fix_time_ms: null }]),
    recent_cases: cases,
    top_active_cases: cases.filter((item) => item.status !== "COMPLETED"),
    scoped_cases: cases,
  };
}

afterEach(() => {
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("historical RBAC dashboard", () => {
  it("is the first authenticated landing view and preserves existing navigation", () => {
    const markup = renderToStaticMarkup(<MemoryRouter initialEntries={["/dashboard"]}><QueryClientProvider client={createSessionQueryClient()}><App actor={maya} onLogout={() => undefined} /></QueryClientProvider></MemoryRouter>);
    expect(markup).toContain('aria-current="page"');
    expect(markup).toContain('href="/dashboard"');
    expect(markup).toContain("Choose a part of the client lifecycle");
    expect(markup).toContain("Onboarding");
    expect(markup).toContain("New onboarding");
    expect(renderToStaticMarkup(<MemoryRouter initialEntries={["/new-onboarding"]}><WorkspaceTabs actor={maya} /></MemoryRouter>)).toContain("Cases");
  });

  it("shows the live onboarding dashboard after selecting the Onboarding category", () => {
    const markup = renderToStaticMarkup(<MemoryRouter><DashboardCategoryPicker dashboard={snapshot(maya)} onSelectOnboarding={() => undefined} /></MemoryRouter>);
    expect(markup).toContain("Onboarding");
    expect(markup).toContain("View dashboard");
    expect(markup).not.toContain("Not set up");
    expect(markup).toContain("Global Tax Compliance (GTC)");
    expect(markup).toContain("Periodic Review / KYC Refresh");
    expect(markup.match(/category-card--live/g)).toHaveLength(1);
    expect(markup.match(/class="card category-card/g)).toHaveLength(3);
  });

  it("renders exact backend totals, zero-touch rate, timing, and scoped cases", () => {
    const markup = renderToStaticMarkup(<MemoryRouter><DashboardView actor={maya} dashboard={snapshot(maya)} dashScope="team" onScopeChange={() => undefined} dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all" onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined} /></MemoryRouter>);
    expect(markup).toContain("Onboarding Dashboard");
    expect(markup).not.toContain("Historical CLM overview");
    expect(markup).not.toContain("Global / cross-team");
    expect(markup).toContain("Open cases");
    expect(markup).toContain("Zero-touch rate");
    expect(markup).toContain("Mean recorded run time");
    expect(markup).toContain("Time per pipeline step");
    expect(markup).toContain("Registry verification");
    expect(markup).toContain("Existing-customer search");
    expect(markup).toContain("Last 30 days");
    expect(markup).toContain("Onboarded per week");
    expect(markup).toContain("All cases");
    expect(markup).toContain("Maya Lim");
    expect(markup).toContain("DBS SYNTHETIC CLIENT");
    expect(markup).not.toContain("OCBC");
  });

  it("renders cross-team workload for the Director", () => {
    const markup = renderToStaticMarkup(<MemoryRouter><DashboardView actor={olivia} dashboard={snapshot(olivia)} dashScope="team" onScopeChange={() => undefined} dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all" onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined} /></MemoryRouter>);
    expect(markup).toContain("Onboarding Dashboard");
    expect(markup).toContain("Maya Lim");
    expect(markup).toContain("Sophia Ng");
    expect(markup).toContain("DBS Corporate Onboarding");
    expect(markup).toContain("OCBC Corporate Onboarding");
    expect(markup).toContain("DBS SYNTHETIC CLIENT");
    expect(markup).toContain("Team scope");
  });

  it("hides the team filter for a team-scoped actor", () => {
    const markup = renderToStaticMarkup(<MemoryRouter><DashboardView actor={maya} dashboard={snapshot(maya)} dashScope="team" onScopeChange={() => undefined} dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all" onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined} /></MemoryRouter>);
    expect(markup).not.toContain("Team scope");
  });

  it("renders the My work scope from the same snapshot shape", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], offset: 0, limit: 8, has_more: false }), { status: 200 })));
    const mineSnapshot = { ...snapshot(maya), view: "mine" as const };
    const markup = renderToStaticMarkup(<MemoryRouter><QueryClientProvider client={createSessionQueryClient()}><DashboardView actor={maya} dashboard={mineSnapshot} dashScope="mine" onScopeChange={() => undefined} dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all" onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined} /></QueryClientProvider></MemoryRouter>);
    expect(markup).toContain("Your open cases");
    expect(markup).toContain("Your created cases onboarded");
    expect(markup).toContain("Your cases");
    expect(markup).toContain("Blocked cases");
    expect(markup).toContain("Recent activity on your cases");
    expect(markup).toContain("Progress");
    expect(markup).toContain("DBS SYNTHETIC CLIENT");
  });

  it("renders a safe empty state without NaN or undefined", () => {
    const markup = renderToStaticMarkup(<MemoryRouter><DashboardView actor={maya} dashboard={snapshot(maya, 0)} dashScope="team" onScopeChange={() => undefined} dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all" onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined} /></MemoryRouter>);
    expect(markup).toContain("No onboarding cases are available for your current scope.");
    expect(markup).not.toContain("NaN");
    expect(markup).not.toContain("undefined");
  });

  it("fetches only the authenticated dashboard endpoint and ignores browser storage", async () => {
    const storage = { getItem: vi.fn(), setItem: vi.fn() };
    const value = snapshot(maya);
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(value), { status: 200 }));
    vi.stubGlobal("localStorage", storage);
    vi.stubGlobal("sessionStorage", storage);
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchDashboard()).resolves.toEqual(value);
    expect(fetchMock).toHaveBeenCalledWith("/api/clm/zero-touch/dashboard", expect.objectContaining({ credentials: "include" }));
    expect(storage.getItem).not.toHaveBeenCalled();
  });

  it("appends scope=mine only when the My work view is requested", async () => {
    const value = snapshot(maya);
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(value), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchDashboard(undefined, "mine");
    expect(fetchMock).toHaveBeenCalledWith("/api/clm/zero-touch/dashboard?scope=mine", expect.objectContaining({ credentials: "include" }));
  });

  it("appends an explicitly selected date_range", async () => {
    const value = snapshot(maya);
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(value), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchDashboard(undefined, "team", "90d");
    expect(fetchMock).toHaveBeenCalledWith("/api/clm/zero-touch/dashboard?date_range=90d", expect.objectContaining({ credentials: "include" }));
  });

  it("keeps API failures on the existing sanitized transport path", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "DASHBOARD_UNAVAILABLE", message: "Dashboard data is unavailable." } }), { status: 503 })));
    await expect(fetchDashboard()).rejects.toMatchObject({ message: "Dashboard data is unavailable.", status: 503 });
  });
});


it("Dashboard v2 explicitly requests its 30-day initial cohort", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(snapshot(maya))));
  vi.stubGlobal("fetch", fetchMock);
  await fetchDashboard(undefined, "team", "30d");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/clm/zero-touch/dashboard?date_range=30d",
    expect.objectContaining({ credentials: "include" }),
  );
});


it("renders the fixed mock weekly chart, labelled as mock data, regardless of the backend response", () => {
  const value = snapshot(maya);
  value.weekly_onboarded = [{
    week_start: "2026-10-12", by_jurisdiction: { SG: 3 }, unresolved_count: 0,
  }];
  const markup = renderToStaticMarkup(<MemoryRouter><DashboardView
    actor={maya} dashboard={value} dashScope="team" onScopeChange={() => undefined}
    dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all"
    onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
  /></MemoryRouter>);
  expect(markup).not.toContain('title="Singapore: 3"');
  expect(markup).toContain('title="Singapore: 9"');
  expect(markup).toContain("10-26");
  expect(markup).toContain("Fixed sample figures for demonstration");
  expect(markup).not.toContain("Illustrative mix");
  expect(markup).toContain('title="Australia: 4"');
});


it("qualifies recorded timing samples and availability without Live claims", () => {
  const value = snapshot(maya);
  const picker = renderToStaticMarkup(<MemoryRouter><DashboardCategoryPicker
    dashboard={value} onSelectOnboarding={() => undefined}
  /></MemoryRouter>);
  expect(picker).toContain("Available");
  expect(picker).not.toContain(">Live<");
  const markup = renderToStaticMarkup(<QueryClientProvider client={createSessionQueryClient()}><MemoryRouter><DashboardView
    actor={maya} dashboard={value} dashScope="mine" onScopeChange={() => undefined}
    dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all"
    onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
  /></MemoryRouter></QueryClientProvider>);
  expect(markup).toContain("recorded workflow start to completion");
  expect(markup).not.toContain("creation to Completed");
  const manager = renderToStaticMarkup(<MemoryRouter><DashboardView
    actor={maya} dashboard={value} dashScope="team" onScopeChange={() => undefined}
    dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all"
    onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
  /></MemoryRouter>);
  expect(manager).toContain("Waiting and blocker-resolution time are not included");
  expect(manager).not.toContain("including the time to fix it");
});


it.each(["team", "mine"] as const)("keeps %s case ages, sorting and filters fixed under client skew", async (scope) => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [] }))));
  const value = snapshot(maya);
  const active = { ...value.scoped_cases[0], legal_name: "ACTIVE TIMING CLIENT",
    created_at: "2026-09-06T03:00:00Z", case_elapsed_ms: 172_800_000 };
  const completed = { ...active, case_id: "00000000-0000-4000-8000-000000000099",
    legal_name: "COMPLETED TIMING CLIENT", created_at: "2026-07-31T03:00:00Z",
    completed_at: "2026-08-01T03:00:00Z", status: "COMPLETED" as const,
    current_stage: "COMPLETE" as const, case_elapsed_ms: 86_400_000 };
  value.scoped_cases = [completed, active];
  const now = vi.spyOn(Date, "now").mockReturnValue(Date.parse(value.data_as_of));
  const client = createSessionQueryClient();
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  const render = () => root.render(<QueryClientProvider client={client}><MemoryRouter><DashboardView
    actor={maya} dashboard={value} dashScope={scope} onScopeChange={() => undefined}
    dateRange="all" onDateRangeChange={() => undefined} teamFilter="all"
    onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
  /></MemoryRouter></QueryClientProvider>);
  try {
    await act(async () => render());
    const article = Array.from(container.querySelectorAll("article")).find(item =>
      item.querySelector("h2")?.textContent === (scope === "team" ? "All cases" : "Your cases"))!;
    const rows = () => Array.from(article.querySelectorAll("tbody tr"));
    expect(rows()[0].textContent).toContain("ACTIVE TIMING CLIENT");
    expect(rows()[0].textContent).toContain("2d");
    expect(rows()[1].textContent).toContain("1d");
    const age = Array.from(article.querySelectorAll("label")).find(item =>
      item.textContent?.trim().startsWith("Case age / duration"))!.querySelector("select")!;
    await act(async () => { age.value = "lt7"; age.dispatchEvent(new Event("change", { bubbles: true })); });
    expect(rows()).toHaveLength(2);
    const observed = article.innerHTML;
    now.mockReturnValue(Date.parse(value.data_as_of) + 40 * 86_400_000);
    await act(async () => render());
    expect(article.innerHTML).toBe(observed);
    await act(async () => { age.value = "gt30"; age.dispatchEvent(new Event("change", { bubbles: true })); });
    expect(rows()).toHaveLength(0);
    expect(article.textContent).toContain("No cases match these filters.");
  } finally {
    await act(async () => root.unmount());
    client.clear();
    container.remove();
  }
});


it.each([
  [0, "< 1s"], [12, "< 1s"], [1_001, "1s"], [60_999, "1m"],
  [119_999, "1m 59s"], [3_601_000, "1h"], [86_401_000, "1d"],
])("renders returned dashboard duration %sms without rounding or minimums", (milliseconds, expected) => {
  const value = snapshot(maya);
  value.scoped_cases = value.scoped_cases.map(item => ({ ...item, case_elapsed_ms: milliseconds }));
  value.workload_by_person[0].oldest_open_age_ms = milliseconds;
  value.workload_by_person[0].mean_fix_time_ms = milliseconds;
  value.timing.mean_total_duration_ms = milliseconds;
  value.stage_timing[0].clean_mean_ms = milliseconds;
  value.stage_timing[0].combined_mean_ms = milliseconds;
  for (const scope of ["team", "mine"] as const) {
    const client = createSessionQueryClient();
    const markup = renderToStaticMarkup(<QueryClientProvider client={client}><MemoryRouter><DashboardView
      actor={maya} dashboard={value} dashScope={scope} onScopeChange={() => undefined}
      dateRange="all" onDateRangeChange={() => undefined} teamFilter="all"
      onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
    /></MemoryRouter></QueryClientProvider>);
    const container = document.createElement("div");
    container.innerHTML = markup;
    const article = (heading: string) => Array.from(container.querySelectorAll("article")).find(item =>
      item.querySelector("h2")?.textContent === heading)!;
    const cases = article(scope === "team" ? "All cases" : "Your cases");
    expect(cases.querySelector("tbody tr")!.textContent).toContain(expected);
    const kpi = (label: string) => Array.from(container.querySelectorAll("article.dashboard-kpi")).find(item =>
      item.querySelector("span")?.textContent === label)!.querySelector("strong")!.textContent;
    expect(kpi(scope === "team" ? "Mean recorded run time" : "Recorded run time")).toBe(expected);
    if (scope === "team") {
      const cells = article("Workload by person").querySelectorAll("tbody tr td");
      expect(cells[2].textContent).toBe(expected);
      expect(cells[5].textContent).toBe(expected);
      const stageCells = container.querySelector(".stage-timing-table tbody tr")!.querySelectorAll("td");
      expect(stageCells[2].textContent).toBe(expected);
      expect(stageCells[4].textContent).toBe(expected);
    } else {
      expect(kpi("Time to resolve a blocker")).toBe(expected);
    }
    client.clear();
  }
});


it.each(["team", "mine"] as const)("PR95-R2 labels %s ongoing ages and completed durations truthfully", scope => {
  const value = snapshot(maya);
  const base = value.scoped_cases[0];
  value.scoped_cases = [
    { ...base, legal_name: "ACTIVE", case_elapsed_ms: 0 },
    { ...base, case_id: "blocked", legal_name: "BLOCKED", status: "WAITING_FOR_REVIEW", case_elapsed_ms: 999 },
    { ...base, case_id: "complete", legal_name: "COMPLETED", status: "COMPLETED", case_elapsed_ms: 1_001 },
    // Defensive display of a missing legacy value does not broaden the API type.
    Object.assign({ ...base, case_id: "unknown", legal_name: "UNKNOWN", status: "COMPLETED" as const }, { case_elapsed_ms: undefined }),
  ];
  const client = createSessionQueryClient();
  const markup = renderToStaticMarkup(<QueryClientProvider client={client}><MemoryRouter><DashboardView
    actor={maya} dashboard={value} dashScope={scope} onScopeChange={() => undefined}
    dateRange="all" onDateRangeChange={() => undefined} teamFilter="all"
    onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
  /></MemoryRouter></QueryClientProvider>);
  const container = document.createElement("div");
  container.innerHTML = markup;
  const table = Array.from(container.querySelectorAll("article")).find(item =>
    item.querySelector("h2")?.textContent === (scope === "team" ? "All cases" : "Your cases"))!;
  expect(table.querySelector("thead")!.textContent).toContain("Case age / duration");
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  for (const [name, label, duration] of [
    ["ACTIVE", "Case age", "< 1s"], ["BLOCKED", "Case age", "< 1s"],
    ["COMPLETED", "Case duration", "1s"], ["UNKNOWN", "Case duration", "—"],
  ]) {
    const row = rows.find(item => item.querySelector("strong")?.textContent === name)!;
    expect(row.querySelector(`[aria-label="${label}: ${duration}"]`)?.textContent).toBe(duration);
  }
  client.clear();
});

it.each(["team", "mine"] as const)("PR95-R2 exposes native sort buttons and semantic headers in %s tables", async scope => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  vi.stubGlobal("fetch", vi.fn(async (url) => new Response(JSON.stringify(String(url).includes("/teams") ? [] : { items: [] }))));
  const client = createSessionQueryClient();
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  try {
    await act(async () => root.render(<QueryClientProvider client={client}><MemoryRouter><DashboardView
      actor={olivia} dashboard={snapshot(olivia)} dashScope={scope} onScopeChange={() => undefined}
      dateRange="all" onDateRangeChange={() => undefined} teamFilter="all"
      onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
    /></MemoryRouter></QueryClientProvider>));
    const headings = scope === "team" ? ["Time per pipeline step", "Workload by person", "All cases"] : ["Your cases"];
    for (const heading of headings) {
      const article = Array.from(container.querySelectorAll("article")).find(item => item.querySelector("h2")?.textContent === heading)!;
      const headers = Array.from(article.querySelectorAll<HTMLTableCellElement>("thead th.sortable-th"));
      expect(headers.length).toBeGreaterThan(0);
      for (const header of headers) {
        const button = header.querySelector("button");
        expect(button, `${heading}: ${header.textContent}`).not.toBeNull();
        expect(header.getAttribute("scope")).toBe("col");
        expect(button!.type).toBe("button");
        expect(button!.tabIndex).toBe(0);
        button!.focus();
        expect(document.activeElement).toBe(button);
        const before = header.getAttribute("aria-sort");
        await act(async () => button!.click());
        expect(header.getAttribute("aria-sort")).toBe(before === "ascending" ? "descending" : "ascending");
        await act(async () => button!.click());
        expect(header.getAttribute("aria-sort")).toBe(before === "ascending" ? "ascending" : "descending");
        expect(article.querySelectorAll('th[aria-sort="ascending"], th[aria-sort="descending"]')).toHaveLength(1);
      }
    }
  } finally {
    await act(async () => root.unmount());
    client.clear();
    container.remove();
  }
});


it("PR95-R4 every pipeline stage exposes a stable native disclosure and detail region", async () => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  const client = createSessionQueryClient();
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  try {
    await act(async () => root.render(<QueryClientProvider client={client}><MemoryRouter><DashboardView
      actor={maya} dashboard={snapshot(maya)} dashScope="team" onScopeChange={() => undefined}
      dateRange="all" onDateRangeChange={() => undefined} teamFilter="all"
      onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
    /></MemoryRouter></QueryClientProvider>));
    const article = Array.from(container.querySelectorAll("article")).find(item => item.querySelector("h2")?.textContent === "Time per pipeline step")!;
    const buttons = Array.from(article.querySelectorAll<HTMLButtonElement>('tbody button[aria-controls]'));
    expect(buttons).toHaveLength(STAGES.length);
    const ids = new Set<string>();
    for (const button of buttons) {
      expect(button.type).toBe("button");
      const id = button.getAttribute("aria-controls")!;
      expect(ids.has(id)).toBe(false); ids.add(id);
      const detail = document.getElementById(id)!;
      expect(detail).not.toBeNull();
      expect(detail.getAttribute("aria-labelledby")).toBe(button.id);
      expect(button.getAttribute("aria-expanded")).toBe("false");
      expect(detail.closest("tr")!.hidden).toBe(true);
      button.focus(); expect(document.activeElement).toBe(button);
      await act(async () => button.click());
      expect(button.getAttribute("aria-expanded")).toBe("true");
      expect(detail.closest("tr")!.hidden).toBe(false);
      expect(detail.textContent).toContain("No recorded durations for this step.");
      const sort = article.querySelector<HTMLButtonElement>("thead button")!;
      await act(async () => sort.click());
      expect(document.getElementById(id)).toBe(detail);
      expect(button.getAttribute("aria-expanded")).toBe("true");
      await act(async () => button.click());
      expect(button.getAttribute("aria-expanded")).toBe("false");
    }
  } finally {
    await act(async () => root.unmount()); client.clear(); container.remove();
  }
});

it("PR95-R4 recent activity traverses more than100 events using bounded server pages", async () => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  const requests: URL[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const request = new URL(String(url), "http://localhost"); requests.push(request);
    const offset = Number(request.searchParams.get("offset") ?? 0);
    const limit = Number(request.searchParams.get("limit") ?? 50);
    return new Response(JSON.stringify({ offset, limit, has_more: offset + limit < 105,
      items: Array.from({ length: Math.max(0, Math.min(limit, 105 - offset)) }, (_, index) => ({
        case_id: "00000000-0000-4000-8000-000000000001", sequence: 105 - offset - index,
        message: `R4 event ${offset + index + 1}`, timestamp: "2026-09-08T01:00:00Z",
        current_client_scope_label: "DBS",
      })),
    }));
  }));
  const client = createSessionQueryClient();
  const container = document.createElement("div"); document.body.append(container);
  const root = createRoot(container);
  const settle = async () => { await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); }); };
  try {
    await act(async () => root.render(<QueryClientProvider client={client}><MemoryRouter><DashboardView
      actor={maya} dashboard={snapshot(maya)} dashScope="mine" onScopeChange={() => undefined}
      dateRange="all" onDateRangeChange={() => undefined} teamFilter="all"
      onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
    /></MemoryRouter></QueryClientProvider>));
    await settle();
    const article = Array.from(container.querySelectorAll("article")).find(item => item.querySelector("h2")?.textContent?.startsWith("Recent activity"))!;
    const button = (prefix: string) => Array.from(article.querySelectorAll("button")).find(item => item.textContent?.includes(prefix))!;
    expect(requests[0].searchParams.get("limit")).toBe("10");
    expect(requests[0].searchParams.get("created_by")).toBe(maya.user_id);
    const seen: string[] = [];
    for (let page = 0; page <= 10; page++) {
      const rows = Array.from(article.querySelectorAll(".activity-row"));
      seen.push(...rows.map(item => item.querySelector("div")!.textContent!));
      expect(rows[0].textContent).toContain(`R4 event ${page * 10 + 1}`);
      expect(article.textContent).not.toContain("of 100");
      if (page < 10) { await act(async () => button("Next").click()); await settle(); }
    }
    expect(seen).toHaveLength(105); expect(new Set(seen).size).toBe(105);
    expect(button("Next").disabled).toBe(true);
    await act(async () => button("Prev").click()); await settle();
    expect(article.querySelector(".activity-row")!.textContent).toContain("R4 event 91");
    await act(async () => button("Refresh activity").click()); await settle();
    expect(article.querySelector(".activity-row")!.textContent).toContain("R4 event 1");
    expect(article.querySelector('a')!.getAttribute("href")).toBe("/audit");
    expect(requests.every(item => Number(item.searchParams.get("limit")) <= 100)).toBe(true);
  } finally { await act(async () => root.unmount()); client.clear(); container.remove(); }
});


it("PR95-R4 activity handles empty/errors, resets scope and rejects late old-team responses", async () => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  let mode = "valid";
  let late!: (response: Response) => void;
  const requests: Array<{ url: URL; signal: AbortSignal }> = [];
  const response = (offset: number, message: string, hasMore = true) => new Response(JSON.stringify({
    offset, limit: 10, has_more: hasMore, items: [{ case_id: "00000000-0000-4000-8000-000000000001", sequence: offset + 1,
      message, timestamp: "2026-09-08T01:00:00Z", current_client_scope_label: "DBS" }],
  }));
  vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit) => {
    const request = new URL(String(url), "http://localhost");
    if (request.pathname.endsWith("/teams/options")) return new Response("[]");
    requests.push({ url: request, signal: init.signal as AbortSignal });
    const offset = Number(request.searchParams.get("offset"));
    if (mode === "late" && offset > 0) return new Promise<Response>(resolve => { late = resolve; });
    if (mode === "error") return new Response(JSON.stringify({ detail: "unavailable" }), { status: 503 });
    if (mode === "empty") return new Response(JSON.stringify({ items: [], offset, limit: 10, has_more: false }));
    return response(offset, `scope ${request.searchParams.get("team_filter")} offset ${offset}`);
  }));
  const client = createSessionQueryClient(); client.setDefaultOptions({ queries: { retry: false } });
  const container = document.createElement("div"); document.body.append(container);
  const root = createRoot(container);
  const settle = async () => { await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); }); };
  const render = async (actor = olivia, teamFilter = "TEAM_A") => {
    await act(async () => root.render(<QueryClientProvider client={client}><MemoryRouter><DashboardView
      actor={actor} dashboard={snapshot(actor)} dashScope="mine" onScopeChange={() => undefined}
      dateRange="all" onDateRangeChange={() => undefined} teamFilter={teamFilter}
      onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
    /></MemoryRouter></QueryClientProvider>)); await settle();
  };
  const article = () => Array.from(container.querySelectorAll("article")).find(item => item.querySelector("h2")?.textContent?.startsWith("Recent activity"))!;
  const click = async (text: string) => { await act(async () => Array.from(article().querySelectorAll("button")).find(item => item.textContent?.includes(text))!.click()); await settle(); };
  try {
    await render();
    mode = "late"; await click("Next");
    const aborted = requests.at(-1)!.signal;
    await render(olivia, "TEAM_B");
    expect(aborted.aborted).toBe(true);
    await act(async () => late(response(10, "STALE TEAM A"))); await settle();
    expect(article().textContent).toContain("scope TEAM_B offset 0");
    expect(article().textContent).not.toContain("STALE TEAM A");
    mode = "error"; await click("Next");
    expect(article().querySelector('[role="alert"]')!.textContent).toContain("Activity is unavailable");
    expect(article().textContent).not.toContain("No recorded activity");
    expect(article().querySelectorAll(".activity-row")).toHaveLength(0);
    mode = "empty"; await click("Retry activity page");
    expect(article().textContent).toContain("No recorded activity on this page.");
    expect(Array.from(article().querySelectorAll("button")).find(item => item.textContent?.includes("Next"))!.disabled).toBe(true);
    mode = "valid"; await render({ ...maya, user_id: "ethan-tan", role: "RELATIONSHIP_MANAGER" }, "all");
    expect(Number(requests.at(-1)!.url.searchParams.get("offset") ?? 0)).toBe(0);
    expect(requests.at(-1)!.url.searchParams.get("created_by")).toBe("ethan-tan");
    expect(article().textContent).not.toContain("scope TEAM_B");
    await click("Next");
    const globalRefresh = Array.from(container.querySelectorAll("button")).find(item => item.textContent === "Refresh")!;
    await act(async () => globalRefresh.click()); await settle();
    expect(article().textContent).toContain("offset 0");
  } finally { await act(async () => root.unmount()); client.clear(); container.remove(); }
});


it.each([0, 1, 200, 201, 250])("PR95-R5 truthfully describes loaded case subset for %s cohort cases", count => {
  for (const scope of ["team", "mine"] as const) {
    const value = snapshot(maya, count);
    const example = snapshot(maya).scoped_cases[0];
    value.scoped_cases = Array.from({ length: Math.min(count, 200) }, (_, index) => ({
      ...example, case_id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
    }));
    value.view = scope;
    value.totals.total_cases = count;
    const client = createSessionQueryClient();
    const markup = renderToStaticMarkup(<QueryClientProvider client={client}><MemoryRouter><DashboardView
      actor={maya} dashboard={value} dashScope={scope} onScopeChange={() => undefined}
      dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all"
      onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
    /></MemoryRouter></QueryClientProvider>);
    const container = document.createElement("div"); container.innerHTML = markup;
    const articles = Array.from(container.querySelectorAll("article")).filter(article =>
      ["All cases", "Your cases", "Blocked cases"].includes(article.querySelector("h2")?.textContent ?? ""));
    expect(articles).toHaveLength(scope === "mine" ? 2 : 1);
    for (const article of articles) {
      if (count > 200) {
        expect(article.textContent).toContain(`Loaded subset: 200 of ${count}`);
        expect(article.textContent).toContain("filters apply only to the loaded subset");
        const link = article.querySelector('a[href="/cases"]');
        expect(link?.textContent).toBe("View or search Cases");
        expect(article.textContent).not.toContain("None of your cases are currently blocked.");
        expect(article.textContent).toContain(scope === "mine" ? "creator-only" : "authorized cohort");
      } else expect(article.textContent).not.toContain("Loaded subset:");
    }
    expect(markup).not.toContain("1–0 of 0");
    if (count === 0) {
      for (const pager of container.querySelectorAll(".pagination:not([aria-label])")) {
        expect(pager.textContent).toContain("0 of 0");
        expect(Array.from(pager.querySelectorAll("button")).filter(button => !button.disabled && button.textContent !== "1")).toHaveLength(0);
      }
    }
    expect(container.querySelector('select.dashboard-date-range')?.getAttribute("aria-label")).toBe("Dashboard date range");
    client.clear();
  }
});

it("PR95-R5 keeps capped filter empty messages local to loaded subset", async () => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  const value = snapshot(maya);
  value.totals.total_cases = 201;
  value.scoped_cases = Array.from({ length: 200 }, (_, index) => ({ ...value.scoped_cases[0], case_id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}` }));
  const client = createSessionQueryClient(); const container = document.createElement("div"); document.body.append(container);
  const root = createRoot(container);
  try {
    await act(async () => root.render(<QueryClientProvider client={client}><MemoryRouter><DashboardView
      actor={maya} dashboard={value} dashScope="team" onScopeChange={() => undefined}
      dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all" onTeamFilterChange={() => undefined}
      onRefresh={() => undefined} onBack={() => undefined}
    /></MemoryRouter></QueryClientProvider>));
    const article = Array.from(container.querySelectorAll("article")).find(item => item.querySelector("h2")?.textContent === "All cases")!;
    const completed = Array.from(article.querySelectorAll("button")).find(item => item.textContent === "Completed")!;
    await act(async () => completed.click());
    expect(article.textContent).toContain("No loaded cases match these filters.");
    expect(article.textContent).not.toContain("No cases match these filters.");
    expect(article.querySelector('a[href="/cases"]')).not.toBeNull();
  } finally { await act(async () => root.unmount()); client.clear(); container.remove(); }
});


type R6Request = { resolve: (value: Response) => void; reject: (error: Error) => void; signal: AbortSignal };
type R6EntryHarness = {
  client: ReturnType<typeof createSessionQueryClient>;
  container: HTMLDivElement;
  requests: R6Request[];
  render: (actor?: AuthenticatedProfile, generation?: number) => Promise<void>;
  reply: (index: number, value: unknown, status?: number) => Promise<void>;
  fail: (index: number) => Promise<void>;
  click: (label: string) => Promise<void>;
  open: () => Promise<void>;
  settle: () => Promise<void>;
};

async function r6EntryHarness(run: (harness: R6EntryHarness) => Promise<void>) {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  const requests: R6Request[] = [];
  vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) => {
    expect(String(_url)).toContain("/api/clm/zero-touch/dashboard?date_range=30d");
    expect(init.credentials).toBe("include");
    return new Promise<Response>((resolve, reject) => requests.push({ resolve, reject, signal: init.signal as AbortSignal }));
  }));
  const client = createSessionQueryClient();
  // One controlled attempt per interaction; production retry policy remains unchanged.
  client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, retry: false } });
  const container = document.createElement("div"); document.body.append(container);
  const root = createRoot(container);
  const settle = async () => { await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); }); };
  const render = async (actor = maya, generation = 0) => {
    await act(async () => root.render(<QueryClientProvider client={client}><MemoryRouter><Dashboard key={generation} actor={actor} /></MemoryRouter></QueryClientProvider>));
    await settle();
  };
  const reply = async (index: number, value: unknown, status = 200) => {
    await act(async () => requests[index].resolve(new Response(JSON.stringify(value), { status })));
    await settle();
  };
  const fail = async (index: number) => {
    await act(async () => requests[index].reject(new TypeError("SYNTHETIC_PRIVATE_NETWORK_DETAIL")));
    await settle();
  };
  const click = async (label: string) => {
    const button = Array.from(container.querySelectorAll("button")).find(item => item.textContent?.includes(label));
    expect(button, `missing control ${label}`).toBeDefined();
    await act(async () => button!.click()); await settle();
  };
  const open = async () => {
    const card = container.querySelector<HTMLElement>(".category-card--live")!;
    expect(card).not.toBeNull();
    await act(async () => card.click()); await settle();
  };
  try { await render(); await run({ client, container, requests, render, reply, fail, click, open, settle }); }
  finally { await act(async () => root.unmount()); clearSessionQueries(client); container.remove(); }
}

it("PR95-R6 initial pending picker is truthful and navigation keeps one in-flight query", async () => {
  await r6EntryHarness(async h => {
    expect(h.container.querySelector('[role="status"]')?.textContent).toContain("Loading dashboard");
    expect(h.container.querySelector("h1")?.textContent).toBe("Dashboard");
    expect(h.container.querySelector('[role="alert"]')).toBeNull();
    expect(h.container.textContent).not.toContain("0 open");
    await h.open();
    expect(h.container.querySelector('[role="status"]')?.textContent).toContain("Loading dashboard");
    await h.click("All categories");
    expect(h.container.querySelector(".category-grid")).not.toBeNull();
    expect(h.requests).toHaveLength(1);
    await h.reply(0, snapshot(maya));
    expect(h.container.textContent).toContain("1 open");
    expect(h.container.querySelector('[role="status"]')).toBeNull();
  });
});

it.each(["503", "network"])("PR95-R6 initial %s picker error is accessible, sanitized and directly retryable", async failure => {
  await r6EntryHarness(async h => {
    if (failure === "503") await h.reply(0, { detail: { message: "SYNTHETIC_PRIVATE_RESPONSE_DETAIL" } }, 503);
    else await h.fail(0);
    expect(h.container.querySelector('[role="alert"]')?.textContent).toContain("Dashboard data is unavailable");
    expect(h.container.querySelector(".category-grid")).not.toBeNull();
    expect(h.container.textContent).not.toContain("Loading");
    expect(h.container.textContent).not.toContain("SYNTHETIC_PRIVATE");
    const retry = Array.from(h.container.querySelectorAll("button")).find(item => item.textContent === "Try again")!;
    expect(retry.type).toBe("button"); expect(retry.disabled).toBe(false);
    expect(retry.closest('[role="button"]')).toBeNull();
    retry.focus(); expect(document.activeElement).toBe(retry);
    await h.click("Try again");
    expect(h.requests).toHaveLength(2);
    expect(h.container.querySelector('[role="status"]')?.textContent).toContain("Loading dashboard");
    await h.reply(1, snapshot(maya));
    expect(h.container.querySelector('[role="alert"]')).toBeNull();
    expect(h.container.textContent).toContain("1 open");
  });
});

it("PR95-R6 repeated retry errors return to recoverable error rather than permanent loading", async () => {
  await r6EntryHarness(async h => {
    await h.fail(0);
    for (let attempt = 1; attempt <= 2; attempt++) {
      await h.click("Try again");
      expect(h.container.querySelector('[role="status"]')?.textContent).toContain("Loading dashboard");
      await h.reply(attempt, { detail: { code: "DASHBOARD_UNAVAILABLE" } }, 503);
      expect(h.container.querySelector('[role="alert"]')).not.toBeNull();
      expect(h.container.textContent).not.toContain("Loading");
    }
    await h.click("Try again"); await h.reply(3, snapshot(maya));
    expect(h.requests).toHaveLength(4);
    expect(h.container.querySelector('[role="alert"]')).toBeNull();
    expect(h.container.textContent).toContain("1 open");
  });
});

it("PR95-R6 cached refresh failure keeps snapshot through both views and later replaces it", async () => {
  await r6EntryHarness(async h => {
    await h.reply(0, snapshot(maya)); await h.open(); await h.click("Refresh");
    await h.click("All categories");
    expect(h.container.querySelector('[role="status"]')?.textContent).toContain("Refreshing dashboard");
    expect(h.container.textContent).toContain("1 open");
    await h.fail(1);
    expect(h.container.querySelector('[role="alert"]')?.textContent).toContain("last dashboard snapshot remains visible");
    expect(h.container.textContent).toContain("1 open");
    expect(h.container.textContent).not.toContain("SYNTHETIC_PRIVATE");
    await h.open(); expect(h.container.textContent).toContain("Refresh failed");
    await h.click("All categories"); await h.click("Try again");
    const fresh = snapshot(maya); fresh.totals.non_completed_cases = 7;
    fresh.data_as_of = "2026-09-08T04:00:00Z";
    await h.reply(2, fresh);
    expect(h.container.querySelector('[role="alert"]')).toBeNull();
    expect(h.container.textContent).toContain("7 open");
    await h.open(); expect(h.container.textContent).toContain("Onboarding Dashboard");
    await h.click("All categories"); expect(h.container.textContent).toContain("7 open");
    expect(h.requests).toHaveLength(3);
  });
});

it("PR95-R6 initial failed query remains recoverable when navigating picker and Onboarding", async () => {
  await r6EntryHarness(async h => {
    await h.fail(0); await h.open();
    expect(h.container.querySelector('[role="alert"]')?.textContent).toContain("Dashboard data is unavailable");
    await h.click("All categories");
    expect(h.container.querySelector('[role="alert"]')).not.toBeNull();
    expect(h.requests).toHaveLength(1);
    await h.click("Try again"); await h.reply(1, snapshot(maya));
    await h.open(); expect(h.container.textContent).toContain("Onboarding Dashboard");
    await h.click("All categories"); expect(h.container.querySelector(".category-grid")).not.toBeNull();
  });
});

it.each(["actor", "same-user-role-session"])("PR95-R6 %s replacement aborts pending retry and rejects the old response", async transition => {
  await r6EntryHarness(async h => {
    await h.fail(0); await h.click("Try again");
    const old = h.requests[1];
    clearSessionQueries(h.client);
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
    const next = transition === "actor" ? olivia : { ...olivia, user_id: maya.user_id };
    await h.render(next, 1);
    expect(old.signal.aborted).toBe(true);
    expect(h.container.textContent).not.toContain("1 open");
    const fresh = snapshot(next); fresh.totals.non_completed_cases = 9;
    await h.reply(2, fresh);
    await h.reply(1, snapshot(maya));
    expect(h.container.textContent).toContain("9 open");
    expect(h.container.textContent).not.toContain("1 open");
    expect(h.requests).toHaveLength(3);
  });
});
