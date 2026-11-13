// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { DashboardView, proposalsAwaitingDecision } from "../Dashboard";
import { caseQueryKeys } from "../../caseQueries";
import { createSessionQueryClient } from "../../queryClient";
import { formatDuration } from "../../shared";
import type { AuthenticatedProfile, AutomationStage, DashboardSnapshot, PolicyCatalogue, PolicyProposal } from "../../types";
import { buildSampleSnapshot, SAMPLE_ATTENTION_POLICY, withOnboardingSample } from "./onboardingSample";

const HOUR = 3_600_000;
const formatDurationForTest = (ms: number) => formatDuration(ms);

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
  capabilities: ["CASE_ACCESS", "CASE_GLOBAL", "POLICY_APPROVE"],
};

const STAGES: AutomationStage[] = ["REGISTRY", "GOLDTIER_SEARCH", "DOCUMENT", "OWNERSHIP", "READINESS", "MOCK_GOLDTIER"];

function emptyLive(actor: AuthenticatedProfile, view: "team" | "mine" = "team"): DashboardSnapshot {
  const lastMonday = Date.parse("2026-11-02T00:00:00Z");
  return {
    historical_trend: [],
    scope: { actor_role: actor.role, access: actor.role === "DIRECTOR" ? "GLOBAL" : "TEAM", team_id: actor.team_id, team_display_name: actor.team_display_name, client_scope_label: actor.client_scope_label },
    view,
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
      by_jurisdiction: {},
      unresolved_count: 0,
      zero_touch_count: 0,
      mean_end_to_end_ms: null,
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

function render(actor: AuthenticatedProfile, dashboard: DashboardSnapshot, scope: "team" | "mine" = "team", client = createSessionQueryClient()): HTMLElement {
  const markup = renderToStaticMarkup(<QueryClientProvider client={client}><MemoryRouter><DashboardView
    actor={actor} dashboard={dashboard} dashScope={scope} onScopeChange={() => undefined}
    dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all"
    onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
  /></MemoryRouter></QueryClientProvider>);
  return new DOMParser().parseFromString(markup, "text/html").body;
}

function card(host: HTMLElement, title: string): HTMLElement {
  const match = Array.from(host.querySelectorAll<HTMLElement>("article.card"))
    .find((article) => article.querySelector("h2")?.textContent?.startsWith(title));
  expect(match, title).toBeTruthy();
  return match!;
}

function rowTexts(table: HTMLElement): string[][] {
  return Array.from(table.querySelectorAll("tbody tr:not(.step-detail)"))
    .map((row) => Array.from(row.querySelectorAll("td")).map((cell) => cell.textContent ?? ""));
}

describe("sample portfolio insight metrics", () => {
  it("adds open/resolved counts and elapsed fix time per exception type", () => {
    const sample = buildSampleSnapshot(emptyLive(olivia), olivia);
    const byType = Object.fromEntries(sample.exception_breakdown.map((item) => [item.exception_type, item]));
    expect(byType.OWNERSHIP_REVIEW_REQUIRED).toMatchObject({ count: 3, open_count: 0, resolved_count: 3, total_fix_ms: 68 * HOUR, mean_fix_ms: 68 * HOUR / 3 });
    expect(byType.OWNERSHIP_INCOMPLETE).toMatchObject({ count: 3, open_count: 1, resolved_count: 2, total_fix_ms: 48 * HOUR, mean_fix_ms: 24 * HOUR });
    expect(byType.DOCUMENT_LOW_CONFIDENCE).toMatchObject({ count: 5, open_count: 1, resolved_count: 4, total_fix_ms: 16.5 * HOUR });
    expect(byType.TARGET_PARTIAL_REVIEW_REQUIRED).toMatchObject({ count: 1, open_count: 1, resolved_count: 0, total_fix_ms: 0, mean_fix_ms: null });
    // Backend order is unchanged: most frequent first.
    expect(sample.exception_breakdown[0].exception_type).toBe("DOCUMENT_LOW_CONFIDENCE");
  });

  it("reports reached cases and blocker resolution time per step", () => {
    const sample = buildSampleSnapshot(emptyLive(olivia), olivia);
    const document = sample.stage_timing.find((row) => row.stage === "DOCUMENT")!;
    expect([document.reached_count, document.blocked_count]).toEqual([41, 8]);
    expect([document.resolution_count, document.resolution_mean_ms]).toEqual([6, Math.floor(32.5 * HOUR / 6)]);
    const ownership = sample.stage_timing.find((row) => row.stage === "OWNERSHIP")!;
    expect([ownership.resolution_count, ownership.resolution_mean_ms]).toEqual([5, Math.floor(116 * HOUR / 5)]);
    for (const row of sample.stage_timing) expect(row.reached_count).toBeGreaterThanOrEqual(row.blocked_count);
  });

  it("counts zero-touch completions per week and per team", () => {
    const sample = buildSampleSnapshot(emptyLive(olivia), olivia);
    const weeks = sample.weekly_onboarded;
    // This week: one zero-touch and one blocked completion; seven weeks ago: two of three.
    expect([weeks[7].zero_touch_count, weeks[7].by_jurisdiction.SG]).toEqual([1, 2]);
    expect(weeks[0].zero_touch_count).toBe(2);
    const zeroTouchTotal = weeks.reduce((sum, week) => sum + week.zero_touch_count, 0);
    expect(zeroTouchTotal).toBe(sample.timing.zero_touch_count);
    const teamTotal = sample.team_breakdown.reduce((sum, team) => sum + team.count, 0);
    expect(teamTotal).toBe(sample.totals.total_cases);
    expect(sample.team_breakdown.reduce((sum, team) => sum + team.zero_touch_count, 0)).toBe(sample.timing.zero_touch_count);
    for (const team of sample.team_breakdown) {
      expect(team.status_breakdown.reduce((sum, item) => sum + item.count, 0)).toBe(team.count);
    }
  });

  it("merges the new live fields with the sample by count", () => {
    const live = emptyLive(olivia);
    live.exception_breakdown = [{ exception_type: "OWNERSHIP_REVIEW_REQUIRED", count: 1, open_count: 0, resolved_count: 1, mean_fix_ms: 4 * HOUR, total_fix_ms: 4 * HOUR, by_jurisdiction: { SG: 1 }, unresolved_jurisdiction_count: 0, weekly_counts: [0, 0, 0, 0, 0, 0, 0, 1] }];
    live.stage_timing = live.stage_timing.map((row) => row.stage === "OWNERSHIP" ? { ...row, reached_count: 2, blocked_count: 1, resolution_mean_ms: 4 * HOUR, resolution_count: 1 } : row);
    live.weekly_onboarded[7] = { ...live.weekly_onboarded[7], by_jurisdiction: { SG: 1 }, zero_touch_count: 1 };
    live.team_breakdown = [{ team_id: "TEAM_A", team_display_name: "Alpha", client_scope_label: "Alpha", count: 1, status_breakdown: [{ status: "COMPLETED", count: 1 }], zero_touch_count: 1, sla_met_count: 1, overdue_count: 0, high_attention_count: 0, mean_end_to_end_ms: 600_000, resolved_blockers: 1, mean_fix_ms: 4 * HOUR }];
    const sample = buildSampleSnapshot(live, olivia);
    const merged = withOnboardingSample(live, olivia);

    const ownership = merged.exception_breakdown.find((item) => item.exception_type === "OWNERSHIP_REVIEW_REQUIRED")!;
    expect(ownership).toMatchObject({ count: 4, resolved_count: 4, total_fix_ms: 72 * HOUR, mean_fix_ms: 18 * HOUR });
    const stage = merged.stage_timing.find((row) => row.stage === "OWNERSHIP")!;
    const sampleStage = sample.stage_timing.find((row) => row.stage === "OWNERSHIP")!;
    expect(stage.reached_count).toBe(sampleStage.reached_count + 2);
    expect(stage.resolution_count).toBe(6);
    expect(stage.resolution_mean_ms).toBe(Math.floor(120 * HOUR / 6));
    expect(merged.weekly_onboarded[7].zero_touch_count).toBe(sample.weekly_onboarded[7].zero_touch_count + 1);
    const alpha = merged.team_breakdown.find((team) => team.team_id === "TEAM_A")!;
    const sampleAlpha = sample.team_breakdown.find((team) => team.team_id === "TEAM_A")!;
    expect(alpha.count).toBe(sampleAlpha.count + 1);
    expect(alpha.zero_touch_count).toBe(sampleAlpha.zero_touch_count + 1);
    const completed = (team: typeof alpha) => team.status_breakdown.find((item) => item.status === "COMPLETED")!.count;
    expect(completed(alpha)).toBe(completed(sampleAlpha) + 1);
    // The live input is not modified.
    expect(live.team_breakdown[0].count).toBe(1);
  });
});

describe("dashboard insight panels", () => {
  it("shows waiting on a person beside processing time in the step table", () => {
    const host = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    const rows = rowTexts(card(host, "Time per pipeline step").querySelector("table")!);
    const ownership = rows.find((row) => row[1].includes("Ownership & UBO"))!;
    expect(ownership[6]).toBe("23h 12mmean · 5 resolved");
    const readiness = rows.find((row) => row[1].includes("Submission readiness"))!;
    expect(readiness[6]).toBe("—");
  });

  it("ranks exception types by total elapsed fix time and shows every type", () => {
    const host = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    const exceptions = card(host, "Why cases stopped");
    expect(exceptions.querySelector("h2")?.textContent).toBe("Why cases stopped · 20 exceptions");
    expect(exceptions.textContent).not.toContain("not active working time");
    const rows = rowTexts(exceptions.querySelector("table")!);
    expect(rows).toHaveLength(7);
    expect(exceptions.querySelector(".pagination")).toBeNull();
    // Exception, Raised, Share, Countries, Last 8 weeks, Open, Resolved, Mean fix, Total fix.
    expect(rows[0].slice(0, 3)).toEqual(["Ownership review required", "3", "15%"]);
    expect(rows[0][3]).toBe("SG 3");
    expect(rows[0].slice(5, 8)).toEqual(["—", "3", "22h 40m"]);
    expect(rows[0][8]).toContain("2d 20h");
    expect(rows[0][8]).toContain("43% of all fix time");
    expect(rows[1][0]).toBe("Ownership incomplete");
    expect(rows[1][3]).toBe("SG 2 · AU 1");
    expect(rows[1][5]).toBe("1");
    expect(rows.at(-1)!.slice(5, 9)).toEqual(["1", "0", "—", "—"]);
    expect(rows.at(-1)![0]).toBe("Target partial review required");
    const frequent = rows.find((row) => row[0].startsWith("Document low confidence"))!;
    expect(frequent[0]).toBe("Document low confidenceMost frequent");
    expect(frequent[2]).toBe("25%");
    expect(exceptions.querySelectorAll(".sparkline")).toHaveLength(7);
  });

  it("shows the weekly zero-touch rate and the share of cases passing each step", () => {
    const host = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    const panel = card(host, "Straight-through processing");
    const weekly = Array.from(panel.querySelectorAll('[aria-label="Zero-touch rate per week"] .weekly-chart-count')).map((item) => item.textContent);
    expect(weekly).toHaveLength(8);
    expect(weekly[0]).toBe("67%");
    expect(weekly[7]).toBe("50%");
    const steps = Array.from(panel.querySelectorAll(".dashboard-bar")).map((bar) => bar.textContent);
    expect(steps).toContain("Document verification80% · 33/41");
  });

  it("draws the target and flags weeks above it once turnaround nears the target", () => {
    const live = emptyLive(olivia);
    live.weekly_onboarded = live.weekly_onboarded.map((week, index) => ({
      ...week,
      by_jurisdiction: index >= 6 ? { SG: 1 } : {},
      mean_end_to_end_ms: index === 6 ? 6 * 86_400_000 : index === 7 ? 12 * 86_400_000 : null,
    }));
    const trend = card(render(olivia, live), "Turnaround trend");
    expect(trend.querySelector(".trend-target")).not.toBeNull();
    expect(trend.querySelector(".trend-target-note")!.textContent).toBe("1 week above the 10 days target");
    expect(trend.querySelector(".trend-target-note")!.className).toContain("tag-critical");
    expect(trend.querySelectorAll(".trend-point")).toHaveLength(2);
  });

  it("shows weeks without completions as a dash, not 0%", () => {
    const host = render(olivia, emptyLive(olivia));
    const weekly = Array.from(card(host, "Straight-through processing").querySelectorAll('[aria-label="Zero-touch rate per week"] .weekly-chart-count')).map((item) => item.textContent);
    expect(weekly).toEqual(Array(8).fill("—"));
  });

  it("compares teams for the Director only, in the Manager view", () => {
    const director = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    const rows = rowTexts(card(director, "Team comparison").querySelector("table")!);
    expect(rows.map((row) => row[0])).toEqual(["AlphaAlpha", "BetaBeta"]);
    // Team, Cases, Open, Blocked, Overdue, High attention, Onboarded, Zero-touch, SLA, End-to-end, Blocker fix.
    expect(rows.reduce((sum, row) => sum + Number(row[1]), 0)).toBe(46);
    expect(rows.reduce((sum, row) => sum + Number(row[6]), 0)).toBe(34);

    const onboarder = render(maya, withOnboardingSample(emptyLive(maya), maya));
    expect(onboarder.textContent).not.toContain("Team comparison");
    const mine = render(olivia, withOnboardingSample(emptyLive(olivia, "mine"), olivia), "mine");
    expect(mine.textContent).not.toContain("Team comparison");
  });
});

describe("management overview, funnel and case triage", () => {
  const kpiCard = (host: HTMLElement, label: string) => Array.from(host.querySelectorAll<HTMLElement>("article.dashboard-kpi"))
    .find((item) => item.querySelector("span")?.textContent === label)!;

  it("shows the provisional SLA and attention figures with their rules", () => {
    const host = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    expect(kpiCard(host, "Open cases").querySelector("strong")!.textContent).toBe("12");
    expect(kpiCard(host, "Open cases").textContent).toContain("6 running · 6 blocked · 5 awaiting review");
    expect(kpiCard(host, "Onboarded").querySelector("strong")!.textContent).toBe("34");
    expect(kpiCard(host, "SLA compliance").querySelector("strong")!.textContent).toBe("100%");
    expect(kpiCard(host, "SLA compliance").textContent).toContain("34 of 34 completed within the 10 days target");
    expect(kpiCard(host, "Overdue cases").querySelector("strong")!.textContent).toBe("3");
    expect(kpiCard(host, "Overdue cases").className).toContain("dashboard-kpi--critical");
    expect(kpiCard(host, "Overdue cases").textContent).toContain("4 open cases need high attention");
    expect(kpiCard(host, "At-risk cases").querySelector("strong")!.textContent).toBe("1");
    expect(kpiCard(host, "At-risk cases").className).toContain("dashboard-kpi--warning");
    const footnote = host.querySelector(".dashboard-footnote")!.textContent!;
    expect(footnote).toContain("provisional project rules (D-127)");
    expect(footnote).toContain("not a sponsor SLA or a compliance measure");
    expect(footnote).toContain("No earlier completions are available to compare with.");
    expect(host.querySelector(".kpi-delta")).toBeNull();
  });

  it("compares live figures with the previous period when it has completions", () => {
    const live = emptyLive(olivia);
    live.kpis = { ...live.kpis, completed_cases: 5, zero_touch_rate: 0.8, mean_processing_ms: 120_000, mean_end_to_end_ms: 2 * 86_400_000, sla_met_cases: 5, sla_compliance_rate: 1 };
    live.previous_period = { created_from: "2026-09-07", created_to: "2026-10-06", total_cases: 4, completed_cases: 3, zero_touch_rate: 0.5, mean_processing_ms: 180_000, mean_end_to_end_ms: 86_400_000, sla_compliance_rate: 1 };
    const host = render(olivia, live);
    const delta = (label: string) => kpiCard(host, label).querySelector(".kpi-delta")?.textContent;
    expect(delta("Onboarded")).toBe("+2 vs 7 Sept–6 Oct");
    expect(delta("Zero-touch rate")).toBe("+30 pts vs 7 Sept–6 Oct");
    expect(delta("Mean processing time")).toBe("1m shorter vs 7 Sept–6 Oct");
    expect(delta("Mean end-to-end time")).toBe("1d longer vs 7 Sept–6 Oct");
    expect(delta("SLA compliance")).toBe("No change vs 7 Sept–6 Oct");
  });

  it("drops the comparison once fixed sample cases are added", () => {
    const live = emptyLive(olivia);
    live.previous_period = { created_from: "2026-09-07", created_to: "2026-10-06", total_cases: 1, completed_cases: 1, zero_touch_rate: 1, mean_processing_ms: 1_000, mean_end_to_end_ms: 1_000, sla_compliance_rate: 1 };
    expect(withOnboardingSample(live, olivia).previous_period).toBeNull();
  });

  it("shows the funnel from recorded steps with stops per step", () => {
    const host = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    const rows = Array.from(card(host, "Onboarding funnel").querySelectorAll(".funnel-row")).map((row) => row.textContent);
    expect(rows).toHaveLength(8);
    expect(rows[0]).toBe("Cases received46");
    expect(rows[2]).toBe("Existing-customer search4496% of previous step3 hit a blocker: 2 moved on, 1 still waiting");
    expect(rows[3]).toBe("Document verification4193% of previous step8 hit a blocker: 6 moved on, 2 still waiting");
    expect(rows[5]).toBe("Submission readiness3592% of previous step");
    expect(rows[6]).toBe("GoldTier submission package35100% of previous step1 hit a blocker: 1 still waiting");
    expect(rows[7]).toBe("Onboarded3497% of previous step");
  });

  it("splits processing from waiting per step and reports rework", () => {
    const host = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    const ownership = Array.from(card(host, "Processing vs waiting").querySelectorAll(".stack-row"))
      .find((row) => row.textContent?.startsWith("Ownership & UBO"))!;
    // 5 resolved ownership blockers took 116h in total over 38 cases that reached the step.
    expect(ownership.querySelector("strong")!.textContent).toMatch(/· 3h 3m$/);
    // 20 blockers sit on 19 cases (one case stopped at two different steps), and none repeats a step.
    expect(card(host, "Rework").querySelector(".rework-figures")!.textContent).toBe("0%of cases needed rework0rework cases19cases stopped at least once");
    const trend = card(host, "Turnaround trend");
    expect(trend.querySelectorAll(".trend-point")).toHaveLength(8);
    // Every sample week is far inside the 10-day target, so the chart scales to the data.
    expect(trend.querySelector(".trend-target")).toBeNull();
    expect(trend.querySelector(".trend-target-note")!.textContent).toBe("Target 10 days · every week is within it (slowest week 9h 14m, 4% of target)");
    expect(trend.querySelector(".trend-value--slowest")!.textContent).toBe("9h 14m");
    expect(Array.from(trend.querySelectorAll(".trend-cases")).map((item) => item.textContent)).toEqual(["3 cases", "3 cases", "6 cases", "4 cases", "4 cases", "7 cases", "5 cases", "2 cases"]);
    expect(Array.from(trend.querySelectorAll(".trend-axis")).slice(0, 6).map((item) => item.textContent)).toEqual(["0", "2h", "4h", "6h", "8h", "10h"]);
  });

  it("shows running, blocked, overdue and high-attention work per person", () => {
    const host = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    const ethan = rowTexts(card(host, "Workload by person").querySelector("table")!).find((row) => row[0] === "Ethan Tan")!;
    expect(ethan.slice(0, 6)).toEqual(["Ethan Tan", "4", "2", "2", "1", "1"]);
  });
});

describe("All cases triage", () => {
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
  });

  const allCases = () => Array.from(container!.querySelectorAll<HTMLElement>("article.card"))
    .find((article) => article.querySelector("h2")?.textContent === "All cases")!;
  const firstRowName = () => allCases().querySelector("tbody tr strong")!.textContent;
  const select = async (label: string, value: string) => {
    const field = Array.from(allCases().querySelectorAll("label")).find((item) => item.textContent?.startsWith(label))!.querySelector("select")!;
    await act(async () => {
      field.value = value;
      field.dispatchEvent(new Event("change", { bubbles: true }));
    });
  };

  it("puts the cases needing intervention first and filters by SLA, attention, country and exception", async () => {
    await act(async () => root?.render(<QueryClientProvider client={createSessionQueryClient()}><MemoryRouter><DashboardView
      actor={olivia} dashboard={withOnboardingSample(emptyLive(olivia), olivia)} dashScope="team" onScopeChange={() => undefined}
      dateRange="30d" onDateRangeChange={() => undefined} teamFilter="all"
      onTeamFilterChange={() => undefined} onRefresh={() => undefined} onBack={() => undefined}
    /></MemoryRouter></QueryClientProvider>));

    // Highest attention first, oldest first within it.
    expect(firstRowName()).toBe("Marine Parade Wellness Pte. Ltd.");
    const first = allCases().querySelector("tbody tr")!.textContent!;
    expect(first).toContain("Overdue");
    expect(first).toContain("Past the 10 days target");
    expect(first).toContain("Target partial review required");

    await select("Attention", "HIGH");
    expect(allCases().querySelector(".pagination .text-muted")!.textContent).toBe("1–4 of 4");
    await select("Attention", "all");
    await select("SLA", "AT_RISK");
    expect(allCases().querySelectorAll("tbody tr")).toHaveLength(1);
    expect(firstRowName()).toBe("Kranji Agritech Pte. Ltd.");
    await select("SLA", "all");
    await select("Country", "AU");
    expect(allCases().querySelector(".pagination .text-muted")!.textContent).toBe("1–5 of 5");
    await select("Country", "all");
    await select("Open exception", "DOCUMENT_LOW_CONFIDENCE");
    expect(firstRowName()).toBe("Hougang Pet Supplies Pte. Ltd.");
    expect(allCases().querySelectorAll("tbody tr")).toHaveLength(1);
    await select("Open exception", "all");

    await select("Sort", "deadline");
    expect(firstRowName()).toBe("Marine Parade Wellness Pte. Ltd.");
    await select("Sort", "waiting");
    expect(firstRowName()).toBe("Marine Parade Wellness Pte. Ltd.");
  });
});

function proposal(overrides: Partial<PolicyProposal>): PolicyProposal {
  return {
    proposal_id: "p1", version: 2, base_active_version: 1, proposer_id: "hr-admin", status: "PENDING_APPROVAL",
    rules: [], reason: "Synthetic change", created_at: "2026-11-01T00:00:00Z", updated_at: "2026-11-02T03:00:00Z",
    decided_by: null, decided_at: null, decision_reason: null, activated_version: null, ...overrides,
  };
}

function catalogue(proposals: PolicyProposal[]): PolicyCatalogue {
  return { active_version: 1, proposals } as unknown as PolicyCatalogue;
}

describe("Director: needs your action and team comparison", () => {
  it("counts only proposals the Director can decide, using the Policy page rule", () => {
    const value = catalogue([
      proposal({ proposal_id: "ok" }),
      proposal({ proposal_id: "own", proposer_id: "olivia-koh" }),
      proposal({ proposal_id: "stale", base_active_version: 0 }),
      proposal({ proposal_id: "draft", status: "DRAFT" }),
      proposal({ proposal_id: "done", status: "APPROVED" }),
    ]);
    expect(proposalsAwaitingDecision(value, olivia).map((item) => item.proposal_id)).toEqual(["ok"]);
    expect(proposalsAwaitingDecision(value, maya)).toEqual([]);
  });

  it("lists GoldTier recovery cases and pending policy changes for the Director", () => {
    const client = createSessionQueryClient();
    client.setQueryData(caseQueryKeys.policyCatalogue(olivia.user_id), catalogue([proposal({}), proposal({ proposal_id: "p2", version: 3, proposer_id: "olivia-koh" })]));
    const host = render(olivia, withOnboardingSample(emptyLive(olivia), olivia), "team", client);
    const actions = host.querySelector<HTMLElement>('[aria-label="Needs your action"]')!;
    expect(actions).not.toBeNull();
    const headings = Array.from(actions.querySelectorAll("h3")).map((item) => item.textContent);
    expect(headings).toEqual(["GoldTier recovery · 1 case", "Policy changes awaiting your decision · 1"]);
    const recovery = actions.querySelectorAll("section")[0].querySelectorAll(".blocked-case-row");
    expect(recovery).toHaveLength(1);
    expect(recovery[0].textContent).toContain("Marine Parade Wellness Pte. Ltd.");
    expect(recovery[0].textContent).toContain("Alpha · Ethan Tan · case age 26d 2h · overdue");
    const policyRows = actions.querySelectorAll("section")[1].querySelectorAll(".blocked-case-row");
    expect(policyRows).toHaveLength(1);
    expect(policyRows[0].textContent).toContain("Proposal version 2");
    expect(policyRows[0].querySelector("a")!.getAttribute("href")).toBe("/policy");
  });

  it("keeps the card for the Director only and leaves the rest of the dashboard working when policies fail", () => {
    expect(render(maya, withOnboardingSample(emptyLive(maya), maya)).querySelector('[aria-label="Needs your action"]')).toBeNull();
    const rm = { ...maya, user_id: "ethan-tan", display_name: "Ethan Tan", role: "RELATIONSHIP_MANAGER" as const };
    expect(render(rm, withOnboardingSample(emptyLive(rm), rm)).querySelector('[aria-label="Needs your action"]')).toBeNull();
    expect(render(olivia, withOnboardingSample(emptyLive(olivia, "mine"), olivia), "mine").querySelector('[aria-label="Needs your action"]')).toBeNull();
    // Not yet loaded: the card says so and every other panel still renders.
    const loading = render(olivia, withOnboardingSample(emptyLive(olivia), olivia));
    expect(loading.querySelector('[aria-label="Needs your action"]')!.textContent).toContain("Loading policy changes");
    expect(loading.textContent).toContain("Team comparison");
  });

  it("gives a relationship manager the same sample dashboard as an onboarder", () => {
    const rm = { ...maya, user_id: "ethan-tan", display_name: "Ethan Tan", role: "RELATIONSHIP_MANAGER" as const };
    for (const scope of ["team", "mine"] as const) {
      const onboarder = withOnboardingSample(emptyLive(maya, scope), maya);
      const manager = withOnboardingSample(emptyLive(rm, scope), rm);
      expect(manager.totals).toEqual(onboarder.totals);
      expect(manager.kpis).toEqual(onboarder.kpis);
      expect(manager.workload_by_person.length).toBe(onboarder.workload_by_person.length);
      expect(manager.workload_by_person.find((row) => row.user_id === rm.user_id)?.open_cases)
        .toBe(onboarder.workload_by_person.find((row) => row.user_id === maya.user_id)?.open_cases);
    }
  });

  it("compares team outcomes that add up to the overall figures", () => {
    const dashboard = withOnboardingSample(emptyLive(olivia), olivia);
    const teams = dashboard.team_breakdown;
    expect(teams.reduce((sum, team) => sum + team.overdue_count, 0)).toBe(dashboard.kpis.overdue_cases);
    expect(teams.reduce((sum, team) => sum + team.high_attention_count, 0)).toBe(dashboard.kpis.high_attention_cases);
    expect(teams.reduce((sum, team) => sum + team.sla_met_count, 0)).toBe(dashboard.kpis.sla_met_cases);
    // 20 sample blockers: 6 still open (cases 41–46), 14 resolved.
    expect(teams.reduce((sum, team) => sum + team.resolved_blockers, 0)).toBe(14);
    const rows = rowTexts(card(render(olivia, dashboard), "Team comparison").querySelector("table")!);
    const alpha = teams.find((team) => team.team_id === "TEAM_A")!;
    const alphaRow = rows.find((row) => row[0].startsWith("Alpha"))!;
    expect(alphaRow[8]).toBe("100%");
    expect(alphaRow[9]).toBe(formatDurationForTest(alpha.mean_end_to_end_ms!));
    expect(alphaRow[10]).toContain(`${alpha.resolved_blockers} resolved`);
  });
});
