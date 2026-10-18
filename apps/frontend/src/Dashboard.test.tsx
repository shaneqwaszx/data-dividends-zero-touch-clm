import { renderToStaticMarkup } from "react-dom/server";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { WorkspaceTabs } from "./navigation";
import { configureAuthenticatedTransport, fetchDashboard } from "./api";
import { DashboardCategoryPicker, DashboardView } from "./pages/Dashboard";
import { createSessionQueryClient } from "./queryClient";
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
    expect(markup).toContain("Not set up");
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


it("renders the authorized weekly response instead of illustrative jurisdiction data", () => {
  const value = snapshot(maya);
  value.weekly_onboarded = [{
    week_start: "2026-10-12", by_jurisdiction: { SG: 3 }, unresolved_count: 0,
  }];
  const markup = renderToStaticMarkup(<MemoryRouter><DashboardView
    actor={maya} dashboard={value} dashScope="team" onScopeChange={() => undefined}
    dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all"
    onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
  /></MemoryRouter>);
  expect(markup).toContain('title="Singapore: 3"');
  expect(markup).toContain("10-12");
  expect(markup).not.toContain("Illustrative mix");
  expect(markup).not.toContain("Australia");
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
