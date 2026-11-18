// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AiAssistantError, DASHBOARD_INSIGHTS_MODE_TIMEOUT_MS, fetchDashboardInsightsMode, type DashboardInsights } from "../aiAssistant";
import { caseQueryKeys, dashboardQueryOptions } from "../caseQueries";
import { createSessionQueryClient } from "../queryClient";
import type { AuthenticatedProfile, AutomationStage, DashboardSnapshot } from "../types";
import AiInsights, { RULE_BASED_LABEL, RULE_BASED_SCOPE, RULE_TOPIC_LABELS } from "./AiInsights";
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
  // c2r1: the merged automatic panel runs only once the service has confirmed mode "auto".
  client.setQueryData(caseQueryKeys.dashboardInsightsMode(actor.user_id), { mode: "auto", remaining_user: null, remaining_site: null });
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

// D-130 amendment draft (fifth hosted Claude path): the panel when the service offers explicit
// generation. Nothing reaches a model on load; one click is one request; the notice is always shown.
describe("AI insights panel: hosted generation (fifth path)", () => {
  type Call = { url: string; method: string; body: unknown };
  let calls: Call[] = [];
  let root: Root | null = null;
  let container: HTMLDivElement | null = null;
  const HOSTED_REPLY = {
    insights: {
      summary: "1 of 2 open cases is overdue.",
      notes: [{ id: "F1", text: "1 open case is past the 10 days target." }, { id: "F9", text: "Not a returned finding." }],
      actions: [{ id: "F1", text: "Clear the overdue case first." }],
      model: "claude-sonnet-5-5",
    },
    findings: [{ id: "F1", topic: "SLA_OVERDUE", severity: "CRITICAL", actionable: true, facts: { open_cases: 2, overdue_cases: 1, target: "10 days" } }],
  };

  function serve(routes: Record<string, () => Response>) {
    calls = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : undefined });
      const route = routes[`${method} ${url.replace(/^.*\/api\/assistant/, "")}`];
      return route ? route() : new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
    }));
  }
  const json = (body: unknown, status = 200) => () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  const mode = (value: string, remaining = 3) => json({ mode: value, remaining_user: remaining, remaining_site: 10 });
  const settle = async () => {
    for (let index = 0; index < 6; index += 1) await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });
  };
  const paths = () => calls.map((call) => `${call.method} ${call.url.replace(/^.*\/api\/assistant/, "")}`);

  async function unmount() {
    if (root) await act(async () => root?.unmount());
    container?.remove();
    root = null;
    container = null;
  }

  async function mount(actor: AuthenticatedProfile): Promise<HTMLDivElement> {
    const host = document.createElement("div");
    document.body.append(host);
    container = host;
    root = createRoot(host);
    const client = createSessionQueryClient();
    await act(async () => root!.render(
      <QueryClientProvider client={client}><MemoryRouter>
        <AiInsights dashboard={withOnboardingSample(emptyLive(actor), actor)} actor={actor} dateRange="all" teamFilter="all" stageLabels={STAGE_LABELS} />
      </MemoryRouter></QueryClientProvider>,
    ));
    await settle();
    return host;
  }

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });
  afterEach(async () => {
    await unmount();
    vi.unstubAllGlobals();
  });

  it("asks nothing on load, shows the notice, and sends one request per click with no dashboard data", async () => {
    serve({ "GET /dashboard/insights/mode": mode("generate"), "POST /dashboard/insights/generate": json(HOSTED_REPLY) });
    const host = await mount(olivia);
    expect(paths()).toEqual(["GET /dashboard/insights/mode"]);
    const panel = host.querySelector('[aria-label="AI insights"]')!;
    const notice = panel.querySelector('[data-testid="external-ai-notice"]')!;
    expect(notice.getAttribute("data-surface")).toBe("insights");
    expect(notice.textContent).toContain("sent to Anthropic");
    const button = panel.querySelector("button")!;
    expect(button.textContent).toBe("Generate AI Insights");
    expect(button.getAttribute("aria-describedby")).toBe(notice.id);
    expect(panel.textContent).toContain("3 left today");
    expect(panel.querySelector(".ai-list")).toBeNull();

    await act(async () => button.click());
    await settle();
    const generated = calls.filter((call) => call.url.endsWith("/dashboard/insights/generate"));
    expect(generated).toHaveLength(1);
    // The service derives the figures itself: the browser sends an empty body.
    expect(generated[0]).toMatchObject({ method: "POST", body: {} });
    expect(paths()).not.toContain("POST /dashboard/insights");
    const notes = Array.from(panel.querySelectorAll("ul.ai-list li")).map((item) => item.textContent);
    expect(notes).toEqual(["1 open case is past the 10 days target.open cases 2 · overdue cases 1 · target 10 days"]);
    expect(panel.querySelector("ul.ai-list li i")!.className).toContain("ai-dot--critical");
    expect(panel.querySelector("ol.ai-list li")!.textContent).toContain("Clear the overdue case first.");
    // No case links: the hosted findings carry no case identifiers.
    expect(panel.querySelectorAll("a")).toHaveLength(0);
    // The remaining count is read again after the request.
    expect(paths().filter((item) => item === "GET /dashboard/insights/mode")).toHaveLength(2);
  });

  it("says when the daily limit is reached, and disables the button with none left", async () => {
    serve({
      "GET /dashboard/insights/mode": mode("generate", 1),
      "POST /dashboard/insights/generate": json({ detail: { code: "DASHBOARD_INSIGHTS_LIMIT", message: "limit" } }, 429),
    });
    const host = await mount(olivia);
    await act(async () => host.querySelector("button")!.click());
    await settle();
    expect(host.textContent).toContain("The daily limit for AI insights has been reached.");
    expect(calls.filter((call) => call.url.endsWith("/generate"))).toHaveLength(1);
    await unmount();

    serve({ "GET /dashboard/insights/mode": mode("generate", 0) });
    const exhausted = await mount(olivia);
    expect(exhausted.querySelector("button")!.disabled).toBe(true);
  });

  it("says insights are unavailable when the service refuses, without retrying", async () => {
    serve({
      "GET /dashboard/insights/mode": mode("generate"),
      "POST /dashboard/insights/generate": json({ detail: { code: "DASHBOARD_INSIGHTS_UNAVAILABLE", message: "x" } }, 503),
    });
    const host = await mount(olivia);
    await act(async () => host.querySelector("button")!.click());
    await settle();
    expect(host.textContent).toContain("AI insights are unavailable right now.");
    expect(calls.filter((call) => call.url.endsWith("/generate"))).toHaveLength(1);
  });

  it("shows nothing and asks nothing more when insights are off", async () => {
    serve({ "GET /dashboard/insights/mode": mode("off") });
    const host = await mount(olivia);
    expect(host.querySelector('[aria-label="AI insights"]')).toBeNull();
    expect(paths()).toEqual(["GET /dashboard/insights/mode"]);
  });

  it("keeps the merged automatic panel when the service confirms the mode is auto", async () => {
    serve({ "GET /dashboard/insights/mode": mode("auto"), "POST /dashboard/insights": json(REPLY) });
    const host = await mount(olivia);
    expect(paths().filter((item) => item === "POST /dashboard/insights")).toHaveLength(1);
    expect(host.querySelector('[data-testid="external-ai-notice"]')).toBeNull();
    expect(host.querySelector("button")).toBeNull();
  });

  // c2r1 (P3-3): a failed, malformed or unrecognised mode check fails closed. Nothing is
  // generated, no dashboard figures are sent, and no other AI mode is used: the only request is
  // the mode check itself. F-2: the panel then shows this dashboard's rule-based findings, labelled
  // as not written by AI, with a retry of the mode check.
  function expectRuleBased(panel: Element) {
    expect(panel.getAttribute("data-source")).toBe("rules");
    expect(panel.textContent).toContain(RULE_BASED_LABEL);
    expect(panel.textContent).toContain("AI wording is not available on this deployment.");
    expect(panel.querySelectorAll(".ai-list li").length).toBeGreaterThan(0);
    expect(panel.querySelector('[data-testid="external-ai-notice"]')).toBeNull();
    expect(Array.from(panel.querySelectorAll("button")).map((item) => item.textContent)).toEqual(["Check for AI insights again"]);
  }
  const text = (body: string, status = 200) => () => new Response(body, { status, headers: { "Content-Type": "application/json" } });
  it.each([
    ["not found (404)", json({ detail: "not found" }, 404)],
    ["unavailable (503)", json({ detail: { code: "DASHBOARD_INSIGHTS_UNAVAILABLE", message: "x" } }, 503)],
    ["a server error (500)", text("oops", 500)],
    ["malformed JSON", text("{not json")],
    ["an empty body", text("")],
    ["a JSON array", json(["auto"])],
    ["JSON null", json(null)],
    ["no mode", json({ remaining_user: 3, remaining_site: 10 })],
    ["an unrecognised mode", json({ mode: "automatic", remaining_user: 3, remaining_site: 10 })],
    ["an upper-case mode", json({ mode: "AUTO", remaining_user: null, remaining_site: null })],
    ["a non-string mode", json({ mode: 1, remaining_user: null, remaining_site: null })],
    ["a malformed remaining count", json({ mode: "generate", remaining_user: "3", remaining_site: 10 })],
    ["a negative remaining count", json({ mode: "generate", remaining_user: -1, remaining_site: 10 })],
  ])("fails closed when the mode check returns %s", async (_label, answer) => {
    serve({ "GET /dashboard/insights/mode": answer, "POST /dashboard/insights": json(REPLY), "POST /dashboard/insights/generate": json(HOSTED_REPLY) });
    const host = await mount(olivia);
    expect(paths()).toEqual(["GET /dashboard/insights/mode"]);
    expectRuleBased(host.querySelector('[aria-label="AI insights"]')!);
  });

  it("F-2: shows the dashboard's own rule-based findings, in rule order, with their evidence", async () => {
    serve({ "GET /dashboard/insights/mode": json({ detail: { code: "DASHBOARD_INSIGHTS_UNAVAILABLE", message: "x" } }, 503) });
    const host = await mount(maya);
    expect(paths()).toEqual(["GET /dashboard/insights/mode"]);
    const panel = host.querySelector('[aria-label="AI insights"]')!;
    expectRuleBased(panel);
    const expected = buildInsightFindings(withOnboardingSample(emptyLive(maya), maya), { isDirector: false, dateRange: "all", stageLabels: STAGE_LABELS })!;
    const items = Array.from(panel.querySelectorAll(".ai-list li"));
    expect(items).toHaveLength(expected.request.findings.length);
    expected.request.findings.forEach((finding, index) => {
      expect(items[index].textContent).toContain(RULE_TOPIC_LABELS[finding.topic]);
      expect(items[index].textContent).toContain(expected.views[finding.id].evidence);
    });
    // Nothing on screen claims to be written by a model.
    expect(panel.textContent).not.toContain("What to do");
  });

  it("F-2: with nothing to describe, keeps the unavailable state and asks nothing more", async () => {
    serve({ "GET /dashboard/insights/mode": json({ detail: "not found" }, 404) });
    const host = document.createElement("div");
    document.body.append(host);
    container = host;
    root = createRoot(host);
    await act(async () => root!.render(
      <QueryClientProvider client={createSessionQueryClient()}><MemoryRouter>
        <AiInsights dashboard={emptyLive(maya)} actor={maya} dateRange="all" teamFilter="all" stageLabels={STAGE_LABELS} />
      </MemoryRouter></QueryClientProvider>,
    ));
    await settle();
    expect(paths()).toEqual(["GET /dashboard/insights/mode"]);
    expect(host.textContent).toContain("AI insights are unavailable right now.");
    expect(host.textContent).not.toContain(RULE_BASED_LABEL);
  });

  // F-2 fix (b): with a date range other than "All time" on screen, the rule-based findings still
  // cover all the data in scope. After the failed mode check the panel reads the same dashboard
  // endpoint once more with date_range=all, for the same user and team scope, and nothing else.
  async function mountRange(actor: AuthenticatedProfile, shown: DashboardSnapshot, dateRange: string, teamFilter: string): Promise<HTMLDivElement> {
    const host = document.createElement("div");
    document.body.append(host);
    container = host;
    root = createRoot(host);
    await act(async () => root!.render(
      <QueryClientProvider client={createSessionQueryClient()}><MemoryRouter>
        <AiInsights dashboard={shown} actor={actor} dateRange={dateRange} teamFilter={teamFilter} stageLabels={STAGE_LABELS} />
      </MemoryRouter></QueryClientProvider>,
    ));
    await settle();
    return host;
  }
  const UNAVAILABLE = json({ detail: { code: "DASHBOARD_INSIGHTS_UNAVAILABLE", message: "x" } }, 503);
  const expectFindingsFrom = (panel: Element, expected: NonNullable<ReturnType<typeof buildInsightFindings>>) => {
    const items = Array.from(panel.querySelectorAll(".ai-list li"));
    expect(items).toHaveLength(expected.request.findings.length);
    expected.request.findings.forEach((finding, index) => {
      expect(items[index].textContent).toContain(RULE_TOPIC_LABELS[finding.topic]);
      expect(items[index].textContent).toContain(expected.views[finding.id].evidence);
    });
  };

  it("F-2: with 30 days shown, sends the mode check and exactly one all-time dashboard read, and shows those findings", async () => {
    // The dashboard on screen has nothing to describe; only the all-time read has findings, so
    // findings on screen can only have come from the all-time data.
    const allTime = emptyLive(maya);
    serve({
      "GET /dashboard/insights/mode": UNAVAILABLE,
      "GET /api/clm/zero-touch/dashboard?date_range=all": json(allTime),
      "POST /dashboard/insights": json(REPLY),
      "POST /dashboard/insights/generate": json(HOSTED_REPLY),
    });
    const host = await mountRange(maya, emptyLive(maya), "30d", "all");
    expect(paths()).toEqual(["GET /dashboard/insights/mode", "GET /api/clm/zero-touch/dashboard?date_range=all"]);
    expect(calls.every((call) => call.method === "GET" && call.body === undefined)).toBe(true);
    const panel = host.querySelector('[aria-label="AI insights"]')!;
    expectRuleBased(panel);
    expect(panel.querySelector('[role="note"]')!.textContent).toContain(RULE_BASED_LABEL);
    expect(panel.textContent).toContain(RULE_BASED_SCOPE);
    expectFindingsFrom(panel, buildInsightFindings(withOnboardingSample(allTime, maya), { isDirector: false, dateRange: "all", stageLabels: STAGE_LABELS })!);
    expect(panel.textContent).not.toContain("What to do");
  });

  it("F-2: a Director's all-time read keeps the team scope, and reads policies only with POLICY_APPROVE", async () => {
    const allTime = emptyLive(olivia);
    const dashboardPath = "GET /api/clm/zero-touch/dashboard?team_filter=TEAM_B&date_range=all";
    const catalogue = {
      catalogue_id: "GLOBAL_POLICY_CATALOGUE", version: 2, active_version: 1, rules: [], superseded_versions: [],
      created_at: "2026-11-05T03:00:00Z", updated_at: "2026-11-05T03:00:00Z", updated_by: "system-bootstrap",
      proposals: [{ proposal_id: "P1", version: 2, base_active_version: 1, proposer_id: "someone-else", status: "PENDING_APPROVAL", rules: [], reason: "r",
        created_at: "2026-11-05T03:00:00Z", updated_at: "2026-11-05T03:00:00Z", decided_by: null, decided_at: null, decision_reason: null }],
    };
    const routes = {
      "GET /dashboard/insights/mode": UNAVAILABLE,
      [dashboardPath]: json(allTime),
      "GET /api/policies": json(catalogue),
    };
    // Without POLICY_APPROVE: the mode check and the all-time read only.
    serve(routes);
    let host = await mountRange(olivia, emptyLive(olivia), "30d", "TEAM_B");
    expect(paths()).toEqual(["GET /dashboard/insights/mode", dashboardPath]);
    let panel = host.querySelector('[aria-label="AI insights"]')!;
    expectRuleBased(panel);
    expectFindingsFrom(panel, buildInsightFindings(withOnboardingSample(allTime, olivia), { isDirector: true, dateRange: "all", stageLabels: STAGE_LABELS, pendingPolicyChanges: null })!);
    expect(panel.textContent).not.toContain(RULE_TOPIC_LABELS.DIRECTOR_POLICY);
    await unmount();

    // With POLICY_APPROVE: also the policy catalogue read, and its waiting change is a finding.
    const approver: AuthenticatedProfile = { ...olivia, capabilities: [...olivia.capabilities, "POLICY_APPROVE"] };
    serve(routes);
    host = await mountRange(approver, emptyLive(approver), "30d", "TEAM_B");
    expect([...paths()].sort()).toEqual(["GET /api/policies", "GET /dashboard/insights/mode", dashboardPath].sort());
    expect(paths()[0]).toBe("GET /dashboard/insights/mode");
    expect(paths()).toHaveLength(3);
    panel = host.querySelector('[aria-label="AI insights"]')!;
    expectRuleBased(panel);
    const expected = buildInsightFindings(withOnboardingSample(allTime, approver), { isDirector: true, dateRange: "all", stageLabels: STAGE_LABELS, pendingPolicyChanges: 1 })!;
    expect(expected.request.findings.map((item) => item.topic)).toContain("DIRECTOR_POLICY");
    expectFindingsFrom(panel, expected);
  });

  it("fails closed when the mode check cannot reach the service", async () => {
    calls = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), method: init?.method ?? "GET", body: undefined });
      throw new TypeError("Failed to fetch");
    }));
    const host = await mount(olivia);
    expect(paths()).toEqual(["GET /dashboard/insights/mode"]);
    expectRuleBased(host.querySelector('[aria-label="AI insights"]')!);
  });

  it("retries only the mode check, and then follows the confirmed mode", async () => {
    serve({ "GET /dashboard/insights/mode": text("{bad") });
    const host = await mount(olivia);
    serve({ "GET /dashboard/insights/mode": mode("generate") });
    await act(async () => host.querySelector("button")!.click());
    await settle();
    expect(paths()).toEqual(["GET /dashboard/insights/mode"]);
    expect(host.querySelector('[data-testid="external-ai-notice"]')!.getAttribute("data-surface")).toBe("insights");
    expect(host.querySelector("button")!.textContent).toBe("Generate AI Insights");
  });

  it("never switches to the automatic route when the re-check after a generation fails", async () => {
    let checks = 0;
    serve({
      "GET /dashboard/insights/mode": () => (checks++ === 0 ? mode("generate")() : new Response("bad gateway", { status: 502 })),
      "POST /dashboard/insights/generate": json(HOSTED_REPLY),
      "POST /dashboard/insights": json(REPLY),
    });
    const host = await mount(olivia);
    await act(async () => host.querySelector("button")!.click());
    await settle();
    expect(paths()).toEqual(["GET /dashboard/insights/mode", "POST /dashboard/insights/generate", "GET /dashboard/insights/mode"]);
    expect(paths()).not.toContain("POST /dashboard/insights");
    // The confirmed hosted panel and its reply stay; nothing else is asked.
    expect(host.querySelector("ul.ai-list li")!.textContent).toContain("1 open case is past the 10 days target.");
    expect(host.querySelector('[data-testid="external-ai-notice"]')).not.toBeNull();
  });
});

describe("AI insights mode check (c2r1, P3-3)", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("returns a recognised mode with its counts", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ mode: "generate", remaining_user: 2, remaining_site: 9 }), { status: 200 })));
    await expect(fetchDashboardInsightsMode()).resolves.toEqual({ mode: "generate", remaining_user: 2, remaining_site: 9 });
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ mode: "auto" }), { status: 200 })));
    await expect(fetchDashboardInsightsMode()).resolves.toEqual({ mode: "auto", remaining_user: null, remaining_site: null });
  });

  it("times out as a failed check, not a usable mode", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
    })));
    const pending = fetchDashboardInsightsMode().catch((error: unknown) => error);
    await vi.advanceTimersByTimeAsync(DASHBOARD_INSIGHTS_MODE_TIMEOUT_MS);
    const error = await pending;
    expect(error).toBeInstanceOf(AiAssistantError);
    expect((error as AiAssistantError).message).toContain("timed out");
  });
});
