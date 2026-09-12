import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, { WorkspaceTabs } from "./App";
import { configureAuthenticatedTransport, fetchDashboard } from "./api";
import { DashboardView } from "./pages/Dashboard";
import type { AuthenticatedProfile, DashboardSnapshot } from "./types";

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

function snapshot(actor: AuthenticatedProfile, total = 2): DashboardSnapshot {
  const teamA = {
    case_id: "00000000-0000-4000-8000-000000000001",
    requested_uen: "202400001A",
    legal_name: "DBS SYNTHETIC CLIENT",
    team_id: "TEAM_A" as const,
    team_display_name: "DBS Corporate Onboarding",
    priority: 10,
    status: "RUNNING" as const,
    final_outcome: null,
    created_at: "2026-09-07T01:00:00Z",
    updated_at: "2026-09-08T01:00:00Z",
    completed_at: null,
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
    final_outcome: "MOCK_GOLDTIER_SUBMITTED",
    completed_at: "2026-09-08T02:00:00Z",
  };
  const cases = total === 0 ? [] : actor.role === "DIRECTOR" ? [teamA, teamB] : [teamA];
  return {
    scope: {
      actor_role: actor.role,
      access: actor.role === "DIRECTOR" ? "GLOBAL" : "TEAM",
      team_id: actor.team_id,
      team_display_name: actor.team_display_name,
      client_scope_label: actor.client_scope_label,
    },
    data_as_of: "2026-09-08T03:00:00Z",
    totals: {
      total_cases: total === 0 ? 0 : cases.length,
      completed_cases: total === 0 ? 0 : cases.filter((item) => item.status === "COMPLETED").length,
      non_completed_cases: total === 0 ? 0 : cases.filter((item) => item.status !== "COMPLETED").length,
      completion_rate: total === 0 ? 0 : cases.filter((item) => item.status === "COMPLETED").length / cases.length,
      prioritised_cases: total === 0 ? 0 : cases.filter((item) => item.priority !== null).length,
      unprioritised_cases: total === 0 ? 0 : cases.filter((item) => item.priority === null).length,
    },
    status_breakdown: [
      { status: "PENDING_INPUTS", count: 0 },
      { status: "RUNNING", count: cases.filter((item) => item.status === "RUNNING").length },
      { status: "WAITING_FOR_REVIEW", count: 0 },
      { status: "RESUMING", count: 0 },
      { status: "RECOVERY_PENDING", count: 0 },
      { status: "COMPLETED", count: cases.filter((item) => item.status === "COMPLETED").length },
      { status: "TECHNICAL_FAILURE", count: 0 },
    ],
    priority_breakdown: [...Array.from({ length: 10 }, (_, index) => ({ priority: 10 - index, count: 10 - index === 10 && cases.length ? 1 : 0 })), { priority: null, count: cases.some((item) => item.priority === null) ? 1 : 0 }],
    team_breakdown: actor.role === "DIRECTOR" ? [
      { team_id: "TEAM_A", team_display_name: "DBS Corporate Onboarding", client_scope_label: "DBS", count: 1 },
      { team_id: "TEAM_B", team_display_name: "OCBC Corporate Onboarding", client_scope_label: "OCBC", count: 1 },
    ] : [{ team_id: "TEAM_A", team_display_name: "DBS Corporate Onboarding", client_scope_label: "DBS", count: total === 0 ? 0 : 1 }],
    recent_cases: cases,
    top_active_cases: cases.filter((item) => item.status !== "COMPLETED"),
    historical_trend: total === 0 ? [] : [{ day: "2026-09-08", created_count: 1, completed_count: actor.role === "DIRECTOR" ? 1 : 0 }],
  };
}

afterEach(() => {
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.unstubAllGlobals();
});

describe("historical RBAC dashboard", () => {
  it("is the first authenticated landing view and preserves existing navigation", () => {
    const markup = renderToStaticMarkup(<App actor={maya} onLogout={() => undefined} />);
    expect(markup).toContain('aria-current="page">Dashboard');
    expect(markup).toContain("Loading dashboard");
    expect(markup).toContain("New onboarding");
    expect(renderToStaticMarkup(<WorkspaceTabs activeTab="home" onChange={() => undefined} actor={maya} />)).toContain("Cases");
  });

  it("renders exact backend totals, status, priority, recent, active, and trend data", () => {
    const markup = renderToStaticMarkup(<DashboardView actor={maya} dashboard={snapshot(maya)} onOpenCase={() => undefined} onRefresh={() => undefined} />);
    expect(markup).toContain("DBS Corporate Onboarding");
    expect(markup).toContain("Total cases");
    expect(markup).toContain("Completion rate");
    expect(markup).toContain("RUNNING");
    expect(markup).toContain("Unset");
    expect(markup).toContain("Highest-priority active cases");
    expect(markup).toContain("DBS SYNTHETIC CLIENT");
    expect(markup).toContain("30-day UTC history");
    expect(markup).not.toContain("OCBC");
  });

  it("renders both backend-returned teams only for the Director", () => {
    const markup = renderToStaticMarkup(<DashboardView actor={olivia} dashboard={snapshot(olivia)} onOpenCase={() => undefined} onRefresh={() => undefined} />);
    expect(markup).toContain("Global / cross-team");
    expect(markup).toContain("DBS Corporate Onboarding");
    expect(markup).toContain("OCBC Corporate Onboarding");
    expect(markup).toContain("OCBC SYNTHETIC CLIENT");
  });

  it("renders a safe empty state without NaN or undefined", () => {
    const markup = renderToStaticMarkup(<DashboardView actor={maya} dashboard={snapshot(maya, 0)} onOpenCase={() => undefined} onRefresh={() => undefined} />);
    expect(markup).toContain("No onboarding cases are available for your current scope.");
    expect(markup).toContain("0%");
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

  it("keeps API failures on the existing sanitized transport path", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "DASHBOARD_UNAVAILABLE", message: "Dashboard data is unavailable." } }), { status: 503 })));
    await expect(fetchDashboard()).rejects.toMatchObject({ message: "Dashboard data is unavailable.", status: 503 });
  });
});
