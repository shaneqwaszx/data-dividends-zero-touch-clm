// ADR-015 / D-128: fixed rules that pick the dashboard findings the AI insights panel describes.
//
// Everything here is deterministic and uses only the snapshot on screen (live plus the demo
// sample). Severity, the figures and the affected cases come from these rules; the model only
// words them. Case names and identifiers stay in the browser as link targets and are never sent.

import type { DashboardInsightsRequest, InsightFinding, InsightSeverity, InsightTopic } from "../aiAssistant";
import { formatDuration } from "../shared";
import type { AuthenticatedProfile, AutomationStage, DashboardCaseItem, DashboardSnapshot, PolicyCatalogue } from "../types";
import { BUSINESS_EXCEPTION_TYPE_LABELS } from "../types";

export interface InsightCaseLink {
  case_id: string;
  name: string;
}

/** What the panel shows next to the AI wording: never sent to the model. */
export interface InsightFindingView {
  id: string;
  severity: InsightSeverity;
  evidence: string;
  cases: InsightCaseLink[];
}

export interface DashboardInsightFindings {
  request: DashboardInsightsRequest;
  views: Record<string, InsightFindingView>;
}

const MAX_FINDINGS = 8;
const MAX_CASE_LINKS = 3;
const DAY_MS = 86_400_000;
const DIRECTOR_TOPICS: ReadonlySet<InsightTopic> = new Set(["DIRECTOR_RECOVERY", "DIRECTOR_POLICY", "TEAM_GAP"]);
const SEVERITY_ORDER: Record<InsightSeverity, number> = { CRITICAL: 0, WARNING: 1, INFO: 2 };
const STATUS_LABELS: Partial<Record<DashboardCaseItem["status"], string>> = {
  WAITING_FOR_REVIEW: "Waiting for review",
  RECOVERY_PENDING: "GoldTier recovery pending",
  PENDING_INPUTS: "Waiting for inputs",
  TECHNICAL_FAILURE: "Technical failure",
  RUNNING: "Running",
  RESUMING: "Resuming",
};

interface Draft {
  topic: InsightTopic;
  severity: InsightSeverity;
  actionable: boolean;
  facts: Record<string, string | number>;
  evidence: string;
  cases: DashboardCaseItem[];
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function days(ms: number): string {
  const count = Math.round(ms / DAY_MS);
  return `${count} day${count === 1 ? "" : "s"}`;
}

function caseName(item: DashboardCaseItem): string {
  return item.legal_name ?? item.requested_uen;
}

function oldestFirst(items: DashboardCaseItem[]): DashboardCaseItem[] {
  return [...items].sort((a, b) => b.case_elapsed_ms - a.case_elapsed_ms);
}

function slaFindings(dashboard: DashboardSnapshot): Draft[] {
  const target = days(dashboard.attention_policy.sla_target_ms);
  const open = dashboard.scoped_cases.filter((item) => item.status !== "COMPLETED");
  const drafts: Draft[] = [];
  const overdue = oldestFirst(open.filter((item) => item.sla_status === "OVERDUE"));
  if (dashboard.kpis.overdue_cases > 0) {
    const oldest = overdue[0];
    drafts.push({
      topic: "SLA_OVERDUE",
      severity: "CRITICAL",
      actionable: true,
      facts: {
        overdue_cases: dashboard.kpis.overdue_cases,
        target,
        ...(oldest ? {
          oldest_open: formatDuration(oldest.case_elapsed_ms),
          // Supplied so the model never has to subtract the target itself.
          oldest_past_target: formatDuration(Math.max(0, oldest.case_elapsed_ms - dashboard.attention_policy.sla_target_ms)),
          oldest_status: STATUS_LABELS[oldest.status] ?? "Open",
        } : {}),
      },
      evidence: `Overdue ${dashboard.kpis.overdue_cases}${oldest ? ` · oldest ${formatDuration(oldest.case_elapsed_ms)}` : ""} · target ${target}`,
      cases: overdue,
    });
  }
  if (dashboard.kpis.at_risk_cases > 0) {
    const atRisk = oldestFirst(open.filter((item) => item.sla_status === "AT_RISK"));
    const window = days(dashboard.attention_policy.at_risk_window_ms);
    drafts.push({
      topic: "SLA_AT_RISK",
      severity: "WARNING",
      actionable: true,
      facts: { at_risk_cases: dashboard.kpis.at_risk_cases, within: window, target },
      evidence: `At risk ${dashboard.kpis.at_risk_cases} · within ${window} of the ${target} target`,
      cases: atRisk,
    });
  }
  return drafts;
}

function waitingDriver(dashboard: DashboardSnapshot): Draft[] {
  const totalFix = dashboard.exception_breakdown.reduce((sum, item) => sum + item.total_fix_ms, 0);
  if (totalFix <= 0) return [];
  const top = [...dashboard.exception_breakdown].sort((a, b) => b.total_fix_ms - a.total_fix_ms)[0];
  const share = top.total_fix_ms / totalFix;
  const label = BUSINESS_EXCEPTION_TYPE_LABELS[top.exception_type];
  const heavy = share >= 0.3;
  return [{
    topic: "WAITING_DRIVER",
    severity: heavy ? "WARNING" : "INFO",
    actionable: heavy,
    facts: {
      exception: label,
      share_of_fix_time: percent(share),
      total_fix_time: formatDuration(top.total_fix_ms),
      mean_fix_time: formatDuration(top.mean_fix_ms ?? 0),
      resolved: top.resolved_count,
      still_open: top.open_count,
    },
    evidence: `${formatDuration(top.total_fix_ms)} of ${formatDuration(totalFix)} fix time · ${top.resolved_count} resolved, ${top.open_count} open`,
    cases: dashboard.scoped_cases.filter((item) => item.open_exception_types.includes(top.exception_type)),
  }];
}

function stopHotspot(dashboard: DashboardSnapshot, stageLabels: Record<AutomationStage, string>): Draft[] {
  const candidates = dashboard.stage_timing.filter((row) => row.reached_count >= 5 && row.blocked_count > 0);
  if (!candidates.length) return [];
  const top = [...candidates].sort((a, b) => b.blocked_count / b.reached_count - a.blocked_count / a.reached_count || b.blocked_count - a.blocked_count)[0];
  const rate = top.blocked_count / top.reached_count;
  const frequent = [...dashboard.exception_breakdown].sort((a, b) => b.count - a.count)[0];
  const notable = rate >= 0.15;
  return [{
    topic: "STOP_HOTSPOT",
    severity: notable ? "WARNING" : "INFO",
    actionable: notable,
    facts: {
      step: stageLabels[top.stage],
      stopped_cases: top.blocked_count,
      reached_cases: top.reached_count,
      still_waiting: top.open_blocked_count,
      ...(frequent ? { most_common_exception: BUSINESS_EXCEPTION_TYPE_LABELS[frequent.exception_type], times_raised: frequent.count } : {}),
    },
    evidence: `Stopped ${top.blocked_count}/${top.reached_count}${frequent ? ` · ${BUSINESS_EXCEPTION_TYPE_LABELS[frequent.exception_type].toLowerCase()} raised ${frequent.count} times` : ""}`,
    cases: [],
  }];
}

function weekCompletions(week: DashboardSnapshot["weekly_onboarded"][number]): number {
  return Object.values(week.by_jurisdiction).reduce((sum, count) => sum + (count ?? 0), 0) + week.unresolved_count;
}

function zeroTouch(dashboard: DashboardSnapshot): Draft[] {
  const rate = dashboard.kpis.zero_touch_rate;
  if (rate === null) return [];
  const weekly = dashboard.weekly_onboarded
    .map((week) => ({ completed: weekCompletions(week), zero: week.zero_touch_count }))
    .filter((week) => week.completed > 0)
    .map((week) => week.zero / week.completed);
  const zeroCount = Math.round(rate * dashboard.kpis.completed_cases);
  return [{
    topic: "ZERO_TOUCH",
    severity: "INFO",
    actionable: false,
    facts: {
      zero_touch_rate: percent(rate),
      zero_touch_cases: zeroCount,
      completed_cases: dashboard.kpis.completed_cases,
      ...(weekly.length > 1 ? { weekly_low: percent(Math.min(...weekly)), weekly_high: percent(Math.max(...weekly)) } : {}),
    },
    evidence: `${zeroCount} of ${dashboard.kpis.completed_cases} completed without intervention${weekly.length > 1 ? ` · weekly ${percent(Math.min(...weekly))}–${percent(Math.max(...weekly))}` : ""}`,
    cases: [],
  }];
}

function workload(dashboard: DashboardSnapshot): Draft[] {
  const rows = dashboard.workload_by_person.filter((row) => row.open_cases > 0);
  if (rows.length < 2) return [];
  const sorted = [...rows].sort((a, b) => b.open_cases - a.open_cases);
  const busiest = sorted[0];
  const lightest = sorted[sorted.length - 1];
  const uneven = busiest.open_cases >= 4 && busiest.open_cases >= 2 * lightest.open_cases;
  return [{
    topic: "WORKLOAD",
    severity: uneven ? "WARNING" : "INFO",
    actionable: uneven,
    facts: uneven
      ? { busiest: busiest.display_name, busiest_open: busiest.open_cases, lightest: lightest.display_name, lightest_open: lightest.open_cases }
      : { people_with_open_cases: rows.length, most_open: busiest.open_cases, fewest_open: lightest.open_cases },
    evidence: sorted.slice(0, 4).map((row) => `${row.display_name} ${row.open_cases}`).join(" · "),
    cases: [],
  }];
}

function turnaround(dashboard: DashboardSnapshot): Draft[] {
  const weeks = dashboard.weekly_onboarded.filter((week) => week.mean_end_to_end_ms !== null);
  if (!weeks.length) return [];
  const target = dashboard.attention_policy.sla_target_ms;
  const slowest = [...weeks].sort((a, b) => b.mean_end_to_end_ms! - a.mean_end_to_end_ms!)[0];
  const over = weeks.filter((week) => week.mean_end_to_end_ms! > target).length;
  return [{
    topic: "TURNAROUND",
    severity: over ? "WARNING" : "INFO",
    actionable: over > 0,
    facts: {
      slowest_week_mean: formatDuration(slowest.mean_end_to_end_ms!),
      slowest_week_cases: weekCompletions(slowest),
      share_of_target: percent(slowest.mean_end_to_end_ms! / target),
      weeks_over_target: over,
      target: days(target),
    },
    evidence: `Slowest week ${formatDuration(slowest.mean_end_to_end_ms!)} over ${weekCompletions(slowest)} cases · ${percent(slowest.mean_end_to_end_ms! / target)} of target`,
    cases: [],
  }];
}

function teamGap(dashboard: DashboardSnapshot, isDirector: boolean): Draft[] {
  if (!isDirector || dashboard.team_breakdown.length < 2) return [];
  const rows = dashboard.team_breakdown.map((team) => {
    const completed = team.status_breakdown.find((item) => item.status === "COMPLETED")?.count ?? 0;
    return { team, completed, sla: completed ? team.sla_met_count / completed : null };
  });
  const sorted = [...rows].sort((a, b) => b.team.overdue_count - a.team.overdue_count);
  const [most, least] = [sorted[0], sorted[sorted.length - 1]];
  if (most.team.overdue_count === least.team.overdue_count) return [];
  return [{
    topic: "TEAM_GAP",
    severity: "INFO",
    actionable: false,
    facts: {
      team_most_overdue: most.team.team_display_name,
      its_overdue: most.team.overdue_count,
      other_team: least.team.team_display_name,
      other_overdue: least.team.overdue_count,
      ...(most.sla !== null ? { its_sla_compliance: percent(most.sla) } : {}),
    },
    evidence: rows.map((row) => `${row.team.team_display_name}: ${row.team.overdue_count} overdue`).join(" · "),
    cases: [],
  }];
}

/** Same rule as the Policy page: pending, proposed by someone else, and based on the active version. */
export function proposalsAwaitingDecision(catalogue: PolicyCatalogue, actor: AuthenticatedProfile) {
  if (!actor.capabilities.includes("POLICY_APPROVE")) return [];
  return (catalogue.proposals ?? []).filter((proposal) => proposal.status === "PENDING_APPROVAL"
    && proposal.proposer_id !== actor.user_id
    && proposal.base_active_version === catalogue.active_version);
}

// Director only: work no one else can move forward, matching the "Needs your action" card.
function directorRecovery(dashboard: DashboardSnapshot): Draft[] {
  const total = dashboard.status_breakdown.find((item) => item.status === "RECOVERY_PENDING")?.count ?? 0;
  if (total === 0) return [];
  const waiting = oldestFirst(dashboard.scoped_cases.filter((item) => item.status === "RECOVERY_PENDING"));
  const oldest = waiting[0];
  const overdue = waiting.filter((item) => item.sla_status === "OVERDUE").length;
  return [{
    topic: "DIRECTOR_RECOVERY",
    severity: overdue > 0 ? "CRITICAL" : "WARNING",
    actionable: true,
    facts: {
      recovery_cases: total,
      ...(oldest ? { oldest_waiting: formatDuration(oldest.case_elapsed_ms), overdue_among_them: overdue } : {}),
    },
    evidence: `GoldTier recovery ${total}${oldest ? ` · oldest ${formatDuration(oldest.case_elapsed_ms)}` : ""}${overdue ? ` · ${overdue} overdue` : ""}`,
    cases: waiting,
  }];
}

function directorPolicy(pendingPolicyChanges: number | null): Draft[] {
  if (!pendingPolicyChanges) return [];
  return [{
    topic: "DIRECTOR_POLICY",
    severity: "WARNING",
    actionable: true,
    facts: { policy_changes_waiting: pendingPolicyChanges },
    evidence: `Policy changes awaiting your decision ${pendingPolicyChanges}`,
    cases: [],
  }];
}

function periodLabel(dashboard: DashboardSnapshot, dateRange: string): string {
  if (dateRange === "all") return "All time";
  const count = Number.parseInt(dateRange, 10);
  return Number.isFinite(count) ? `Last ${count} days` : "Selected period";
}

/** Findings for the AI insights panel, or null when there is nothing to describe. */
export function buildInsightFindings(
  dashboard: DashboardSnapshot,
  options: {
    isDirector: boolean;
    dateRange: string;
    stageLabels: Record<AutomationStage, string>;
    /** Director only: submitted policy changes waiting for this Director's decision. */
    pendingPolicyChanges?: number | null;
  },
): DashboardInsightFindings | null {
  if (dashboard.totals.total_cases === 0) return null;
  const director = options.isDirector
    ? [...directorRecovery(dashboard), ...directorPolicy(options.pendingPolicyChanges ?? null)]
    : [];
  const drafts = [
    ...director,
    ...slaFindings(dashboard),
    ...waitingDriver(dashboard),
    ...stopHotspot(dashboard, options.stageLabels),
    ...turnaround(dashboard),
    ...zeroTouch(dashboard),
    ...workload(dashboard),
    ...teamGap(dashboard, options.isDirector),
  ]
    .map((draft, index) => ({ draft, index }))
    // Director-only findings (their decisions and the team comparison) lead; then by severity,
    // keeping rule order on ties.
    .sort((a, b) => Number(!DIRECTOR_TOPICS.has(a.draft.topic)) - Number(!DIRECTOR_TOPICS.has(b.draft.topic))
      || SEVERITY_ORDER[a.draft.severity] - SEVERITY_ORDER[b.draft.severity] || a.index - b.index)
    .slice(0, MAX_FINDINGS)
    .map(({ draft }) => draft);
  if (!drafts.length) return null;
  const findings: InsightFinding[] = [];
  const views: Record<string, InsightFindingView> = {};
  drafts.forEach((draft, index) => {
    const id = `F${index + 1}`;
    findings.push({ id, topic: draft.topic, severity: draft.severity, actionable: draft.actionable, facts: draft.facts });
    views[id] = {
      id,
      severity: draft.severity,
      evidence: draft.evidence,
      cases: draft.cases.slice(0, MAX_CASE_LINKS).map((item) => ({ case_id: item.case_id, name: caseName(item) })),
    };
  });
  return { request: { period: periodLabel(dashboard, options.dateRange), findings }, views };
}
