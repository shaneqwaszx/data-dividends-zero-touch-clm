// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { DashboardInsights } from "../aiAssistant";
import { caseQueryKeys, dashboardQueryOptions } from "../caseQueries";
import { createSessionQueryClient } from "../queryClient";
import type { AuthenticatedProfile, AutomationStage, DashboardSnapshot } from "../types";
import AiInsights from "./AiInsights";
import { STAGE_LABELS } from "./Dashboard";
import { buildInsightFindings } from "./aiInsightFindings";
import { SAMPLE_ATTENTION_POLICY, withOnboardingSample } from "./mockDashboards/onboardingSample";

const maya: AuthenticatedProfile = {
  user_id: "maya-lim", display_name: "Maya Lim", role: "CLIENT_ONBOARDER", team_id: "TEAM_A",
  team_display_name: "Alpha", team_type: "Corporate Client Onboarding", team_description: "Synthetic team",
  client_scope_label: "Alpha", capabilities: ["CASE_ACCESS"],
};
const olivia: AuthenticatedProfile = {
  ...maya, user_id: "olivia-koh", display_name: "Olivia Koh", role: "DIRECTOR", team_id: null,
  team_display_name: null, team_type: null, client_scope_label: "Global / cross-team", capabilities: ["CASE_ACCESS", "CASE_GLOBAL"],
};
const STAGES: AutomationStage[] = ["REGISTRY", "GOLDTIER_SEARCH", "DOCUMENT", "OWNERSHIP", "READINESS", "MOCK_GOLDTIER"];

function emptyLive(actor: AuthenticatedProfile): DashboardSnapshot {
  const lastMonday = Date.parse("2026-11-02T00:00:00Z");
  return {
    historical_trend: [],
    scope: { actor_role: actor.role, access: actor.role === "DIRECTOR" ? "GLOBAL" : "TEAM", team_id: actor.team_id, team_display_name: actor.team_display_name, client_scope_label: actor.client_scope_label },
    view: "team",
    data_as_of: "2026-11-05T03:00:00Z",
    totals: { total_cases: 0, completed_cases: 0, non_completed_cases: 0, completion_rate: 0, prioritised_cases: 0, unprioritised_cases: 0 },
    zero_touch_rate: 0,
    timing: { mean_total_duration_ms: null, zero_touch_mean_duration_ms: null, zero_touch_count: 0, blocked_mean_duration_ms: null, blocked_count: 0 },
    status_breakdown: (["PENDING_INPUTS", "RUNNING", "WAITING_FOR_REVIEW", "RESUMING", "RECOVERY_PENDING", "COMPLETED", "TECHNICAL_FAILURE"] as const).map((status) => ({ status, count: 0 })),
    priority_breakdown: [],
    team_breakdown: [],
    stage_timing: STAGES.map((stage) => ({ stage, clean_mean_ms: null, clean_count: 0, with_blocker_mean_ms: null, with_blocker_count: 0, combined_mean_ms: null, blocked_count: 0, top_cases: [], reached_count: 0, resolution_mean_ms: null, resolution_count: 0, processing_total_ms: 0, resolution_total_ms: 0, open_blocked_count: 0 })),
    exception_breakdown: [],
    weekly_onboarded: Array.from({ length: 8 }, (_, index) => ({
      week_start: new Date(lastMonday - (7 - index) * 7 * 86_400_000).toISOString().slice(0, 10),
      by_jurisdiction: {}, unresolved_count: 0, zero_touch_count: 0, mean_end_to_end_ms: null,
    })),
    workload_by_person: [],
    recent_cases: [],
    top_active_cases: [],
    scoped_cases: [],
    attention_policy: SAMPLE_ATTENTION_POLICY,
    kpis: { open_cases: 0, running_cases: 0, blocked_cases: 0, awaiting_review_cases: 0, completed_cases: 0, zero_touch_rate: null, mean_processing_ms: null, mean_end_to_end_ms: null, sla_met_cases: 0, sla_compliance_rate: null, overdue_cases: 0, at_risk_cases: 0, high_attention_cases: 0 },
    previous_period: null,
    rework: { total_cases: 0, cases_with_blockers: 0, rework_cases: 0 },
  };
}

// Mirrors apps/assistant/ai_assistant/dashboard_insights.py input rules.
const FACT_KEY = /^[a-z][a-z_]{1,31}$/;
const FACT_TEXT = /^[A-Za-z0-9 .,%&()/:'+\-–·]{1,48}$/;
const PERIOD = /^[A-Za-z0-9 ]{1,32}$/;

const options = (actor: AuthenticatedProfile) => ({ isDirector: actor.role === "DIRECTOR", dateRange: "30d", stageLabels: STAGE_LABELS });

describe("AI insight findings (fixed rules)", () => {
  it("picks the dashboard's findings, most severe first, with case links kept in the browser", () => {
    const dashboard = withOnboardingSample(emptyLive(olivia), olivia);
    const result = buildInsightFindings(dashboard, options(olivia))!;
    const findings = result.request.findings;
    expect(result.request.period).toBe("Last 30 days");
    // Director-only findings first, then the rest by severity; at most eight.
    expect(findings.map((item) => item.topic)).toEqual([
      "DIRECTOR_RECOVERY", "TEAM_GAP", "SLA_OVERDUE", "SLA_AT_RISK", "WAITING_DRIVER", "STOP_HOTSPOT", "TURNAROUND", "ZERO_TOUCH",
    ]);
    expect(findings.map((item) => item.id)).toEqual(["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]);
    expect(findings[2]).toEqual({
      id: "F3", topic: "SLA_OVERDUE", severity: "CRITICAL", actionable: true,
      facts: { overdue_cases: 3, target: "10 days", oldest_open: "26d 2h", oldest_past_target: "16d 2h", oldest_status: "GoldTier recovery pending" },
    });
    expect(result.views.F3.cases.map((item) => item.name)).toEqual([
      "Marine Parade Wellness Pte. Ltd.", "Bugis Street Eateries Pte. Ltd.", "Sengkang Solar Installers Pte. Ltd.",
    ]);
    expect(result.views.F4.cases.map((item) => item.name)).toEqual(["Kranji Agritech Pte. Ltd."]);
    expect(findings[4].facts).toMatchObject({ exception: "Ownership review required", share_of_fix_time: "43%", total_fix_time: "2d 20h" });
    expect(findings[5].facts).toMatchObject({ step: "Document verification", stopped_cases: 8, reached_cases: 41, still_waiting: 2 });
    expect(findings[1].facts).toMatchObject({ team_most_overdue: "Beta", its_overdue: 2, other_team: "Alpha", other_overdue: 1 });
    // A team member's insights keep the workload finding that the Director's list has no room for.
    const team = buildInsightFindings(withOnboardingSample(emptyLive(maya), maya), options(maya))!.request.findings;
    expect(team.find((item) => item.topic === "WORKLOAD")).toMatchObject({ severity: "INFO", actionable: false });
  });

  it("sends no customer names, registration numbers or case IDs, and stays inside the service's input rules", () => {
    const dashboard = withOnboardingSample(emptyLive(olivia), olivia);
    const { request } = buildInsightFindings(dashboard, options(olivia))!;
    const sent = JSON.stringify(request);
    for (const item of dashboard.scoped_cases) {
      expect(sent).not.toContain(item.case_id);
      expect(sent).not.toContain(item.requested_uen);
      if (item.legal_name) expect(sent).not.toContain(item.legal_name);
    }
    expect(sent).not.toMatch(/Pte|Ltd|Pty/);
    expect(request.period).toMatch(PERIOD);
    for (const finding of request.findings) {
      expect(Object.keys(finding.facts).length).toBeLessThanOrEqual(10);
      for (const [key, value] of Object.entries(finding.facts)) {
        expect(key).toMatch(FACT_KEY);
        if (typeof value === "string") expect(value).toMatch(FACT_TEXT);
        else expect(Number.isFinite(value) && value >= 0).toBe(true);
      }
    }
  });

  it("leads a Director's insights with the decisions only they can take", () => {
    const dashboard = withOnboardingSample(emptyLive(olivia), olivia);
    const recovery = dashboard.status_breakdown.find((item) => item.status === "RECOVERY_PENDING")!.count;
    const result = buildInsightFindings(dashboard, { ...options(olivia), pendingPolicyChanges: 2 })!;
    const [first, second] = result.request.findings;
    expect(first).toMatchObject({ topic: "DIRECTOR_RECOVERY", actionable: true, facts: { recovery_cases: recovery } });
    expect(second).toMatchObject({ topic: "DIRECTOR_POLICY", facts: { policy_changes_waiting: 2 } });
    expect(result.views[first.id].cases.length).toBeGreaterThan(0);
    // No policy finding without changes waiting, and none of this for a team member.
    expect(buildInsightFindings(dashboard, { ...options(olivia), pendingPolicyChanges: 0 })!.request.findings
      .map((item) => item.topic)).not.toContain("DIRECTOR_POLICY");
    const team = buildInsightFindings(withOnboardingSample(emptyLive(maya), maya), { ...options(maya), pendingPolicyChanges: 2 })!;
    expect(team.request.findings.some((item) => item.topic.startsWith("DIRECTOR_"))).toBe(false);
  });

  it("returns nothing for an empty dashboard and leaves team comparison out for non-Directors", () => {
    expect(buildInsightFindings(emptyLive(maya), options(maya))).toBeNull();
    const topics = buildInsightFindings(withOnboardingSample(emptyLive(maya), maya), options(maya))!.request.findings.map((item) => item.topic);
    expect(topics).not.toContain("TEAM_GAP");
  });
});

// The panel always works from all the data in scope ("All time"), whatever range is shown.
function render(dashboard: DashboardSnapshot, actor: AuthenticatedProfile, reply?: DashboardInsights, shown: { dateRange: string; allTime?: DashboardSnapshot } = { dateRange: "all" }): HTMLElement {
  const client = createSessionQueryClient();
  const source = shown.allTime ? withOnboardingSample(shown.allTime, actor) : dashboard;
  const findings = buildInsightFindings(source, { ...options(actor), dateRange: "all" });
  if (shown.allTime) client.setQueryData(dashboardQueryOptions(actor.user_id, "all", "team", "all").queryKey, shown.allTime);
  if (reply && findings) client.setQueryData(caseQueryKeys.dashboardInsights(actor.user_id, findings.request), reply);
  const markup = renderToStaticMarkup(
    <QueryClientProvider client={client}><MemoryRouter>
      <AiInsights dashboard={dashboard} actor={actor} dateRange={shown.dateRange} teamFilter="all" stageLabels={STAGE_LABELS} />
    </MemoryRouter></QueryClientProvider>,
  );
  client.clear();
  return new DOMParser().parseFromString(`<div>${markup}</div>`, "text/html").body;
}

const REPLY: DashboardInsights = {
  summary: "3 cases are overdue against the 10 days target.",
  notes: [
    { id: "F3", text: "3 cases are past the 10 days target." },
    { id: "F5", text: "Ownership review required takes 43% of fix time." },
    { id: "F99", text: "Not a finding this panel built." },
  ],
  actions: [{ id: "F3", text: "Clear the overdue cases first." }],
  model: "ministral-3:8b",
};

describe("AI insights panel", () => {
  it("uses all the data in scope rather than the date range on screen, and shows no period line", () => {
    const allTime = emptyLive(olivia);
    const shown = withOnboardingSample(emptyLive(olivia), olivia);
    const panel = render(shown, olivia, REPLY, { dateRange: "30d", allTime }).querySelector('[aria-label="AI insights"]')!;
    expect(panel).not.toBeNull();
    expect(panel.textContent).not.toMatch(/From the figures|Last 30 days|All time/);
    // Until the all-time figures and the reply have loaded, a loading placeholder is shown.
    const waiting = render(shown, olivia, REPLY, { dateRange: "30d" }).querySelector('[aria-label="AI insights"]')!;
    expect(waiting.getAttribute("aria-busy")).toBe("true");
    expect(waiting.textContent).toContain("Loading insights");
    expect(waiting.querySelector(".ai-list")).toBeNull();
  });

  it("shows the AI wording with rule evidence and case links", () => {
    const host = render(withOnboardingSample(emptyLive(olivia), olivia), olivia, REPLY);
    const panel = host.querySelector('[aria-label="AI insights"]')!;
    expect(panel.querySelector("h2")!.textContent).toBe("AI insights");
    expect(panel.querySelector(".ai-summary")!.textContent).toBe(REPLY.summary);
    const notes = Array.from(panel.querySelectorAll("ul.ai-list li")).map((item) => item.textContent);
    expect(notes).toEqual([
      "3 cases are past the 10 days target.Overdue 3 · oldest 26d 2h · target 10 days",
      "Ownership review required takes 43% of fix time.2d 20h of 6d 12h fix time · 3 resolved, 0 open",
    ]);
    expect(panel.querySelector("ul.ai-list li i")!.className).toContain("ai-dot--critical");
    const action = panel.querySelector("ol.ai-list li")!;
    expect(action.textContent).toContain("Clear the overdue cases first.");
    expect(Array.from(action.querySelectorAll("a")).map((item) => item.textContent)).toEqual([
      "Marine Parade Wellness Pte. Ltd.", "Bugis Street Eateries Pte. Ltd.", "Sengkang Solar Installers Pte. Ltd.",
    ]);
    expect(panel.textContent).not.toMatch(/AI-written|Advisory/);
  });

  it("shows a loading placeholder while waiting, and hides without usable notes or when there is nothing to describe", () => {
    const waiting = render(withOnboardingSample(emptyLive(olivia), olivia), olivia).querySelector('[aria-label="AI insights"]')!;
    expect(waiting.textContent).toContain("Loading insights");
    expect(render(withOnboardingSample(emptyLive(olivia), olivia), olivia, { ...REPLY, notes: [] }).querySelector('[aria-label="AI insights"]')).toBeNull();
    // Without a usable summary the checked notes are still shown.
    const noSummary = render(withOnboardingSample(emptyLive(olivia), olivia), olivia, { ...REPLY, summary: "" }).querySelector('[aria-label="AI insights"]')!;
    expect(noSummary.querySelector(".ai-summary")).toBeNull();
    expect(noSummary.querySelectorAll("ul.ai-list li")).toHaveLength(2);
    expect(render(emptyLive(olivia), olivia, REPLY).querySelector('[aria-label="AI insights"]')).toBeNull();
  });

  it("keys the cached reply by the signed-in user and the exact findings", () => {
    const findings = buildInsightFindings(withOnboardingSample(emptyLive(olivia), olivia), options(olivia))!;
    const key = caseQueryKeys.dashboardInsights("olivia-koh", findings.request);
    expect(key.slice(0, 3)).toEqual(["auth", "olivia-koh", "dashboard-insights"]);
    expect(caseQueryKeys.dashboardInsights("maya-lim", findings.request)).not.toEqual(key);
  });
});
