// Fixed sample cases for the Onboarding dashboard, added on top of the live backend snapshot.
//
// Frontend-only demo data: no API, storage or randomness, so every viewer on every device sees
// the same sample figures. Every number is derived from SAMPLE_CASES with the same rules the
// backend dashboard uses, so totals, charts and tables always agree with each other. Sample
// cases are not affected by the team or date-range filters. They open on a read-only case page
// (`sampleCaseDetail`) and are listed after the live cases in the Cases tab (`sampleCaseRows`).
// They are deliberately not labelled as sample data in the UI; see docs/demo/DEMO_RUNBOOK.md.
// Australia cases are illustrative only; Singapore ACRA is the sole implemented registry route.

import type {
  AuthenticatedProfile,
  AutomationStage,
  AutomationStatus,
  BusinessExceptionType,
  DashboardCaseItem,
  DashboardExceptionCount,
  DashboardSnapshot,
  DashboardStageCaseTiming,
  DashboardStageTiming,
  DashboardTimingSummary,
  DashboardWeeklyOnboarded,
  DashboardWorkloadRow,
  JurisdictionCode,
} from "../../types";
import { BUSINESS_EXCEPTION_TYPE_LABELS } from "../../types";

export const SAMPLE_CASE_ID_PREFIX = "sample-";

export function isSampleCaseId(caseId: string): boolean {
  return caseId.startsWith(SAMPLE_CASE_ID_PREFIX);
}

// Sample cases are addressed in the browser by fixed UUID-shaped IDs, so their pages sit at
// /cases/<id> like any other case. Backend case IDs are random version-4 UUIDs.
const SAMPLE_URL_ID_PREFIX = "7f3c9e21-5b84-4d6a-9c1e-a1b2c3d4";
const SAMPLE_URL_ID = /^7f3c9e21-5b84-4d6a-9c1e-a1b2c3d4([0-9]{4})$/;

/** URL ID for a sample case (`sample-0041`), or null when it is not a sample case ID. */
export function sampleCaseUrlId(caseId: string): string | null {
  const match = /^sample-([0-9]{4})$/.exec(caseId);
  return match ? `${SAMPLE_URL_ID_PREFIX}${match[1]}` : null;
}

/** Sample case ID (`sample-0041`) for a URL ID, or null when the URL is not a sample case's. */
export function sampleCaseIdFromUrlId(urlId: string): string | null {
  const match = SAMPLE_URL_ID.exec(urlId.toLowerCase());
  return match ? `${SAMPLE_CASE_ID_PREFIX}${match[1]}` : null;
}

const SECOND = 1_000;
const MINUTE = 60_000;
const HOUR = 3_600_000;
const DAY = 86_400_000;
const WEEK = 7 * DAY;

// Pipeline order shared with the backend; COMPLETE is not a timed step.
const PIPELINE: readonly AutomationStage[] = ["REGISTRY", "GOLDTIER_SEARCH", "DOCUMENT", "OWNERSHIP", "READINESS", "MOCK_GOLDTIER"];
const BLOCKED_STATUSES: readonly AutomationStatus[] = ["WAITING_FOR_REVIEW", "RECOVERY_PENDING", "TECHNICAL_FAILURE"];
const ALL_STATUSES: readonly AutomationStatus[] = ["PENDING_INPUTS", "RUNNING", "WAITING_FOR_REVIEW", "RESUMING", "RECOVERY_PENDING", "COMPLETED", "TECHNICAL_FAILURE"];
const WEEKLY_WEEKS = 8;
const STAGE_TOP_CASES = 3;

const BASE_STAGE_MS: Record<AutomationStage, number> = {
  REGISTRY: 38 * SECOND,
  GOLDTIER_SEARCH: 16 * SECOND,
  DOCUMENT: 2 * MINUTE + 40 * SECOND,
  OWNERSHIP: MINUTE + 25 * SECOND,
  READINESS: 11 * SECOND,
  MOCK_GOLDTIER: 24 * SECOND,
  COMPLETE: 0,
};
// Queueing between steps that is part of the recorded run time but not of any one step.
const RUN_OVERHEAD_MS = 50 * SECOND;

// "viewer" sample cases belong to whoever is signed in, so My work is populated for everyone.
type Owner = "ethan" | "ryan" | "viewer";

// Every sample case belongs to Alpha or Beta, the two configured teams.
const SAMPLE_TEAMS = { TEAM_A: "Alpha", TEAM_B: "Beta" } as const;
type SampleTeamId = keyof typeof SAMPLE_TEAMS;

// The other sample owners are the configured relationship managers, under their own user IDs
// and teams, so their sample and live work combine into one row.
const SAMPLE_PEOPLE: Record<Exclude<Owner, "viewer">, { user_id: string; name: string; team: SampleTeamId }> = {
  ethan: { user_id: "ethan-tan", name: "Ethan Tan", team: "TEAM_A" },
  ryan: { user_id: "ryan-lee", name: "Ryan Lee", team: "TEAM_B" },
};

/** Fixed per case so every viewer sees the same teams; the signed-in user's cases alternate. */
function teamOf(item: SampleCase): SampleTeamId {
  if (item.owner !== "viewer") return SAMPLE_PEOPLE[item.owner].team;
  return item.n % 2 === 0 ? "TEAM_A" : "TEAM_B";
}

interface SampleBlocker {
  type: BusinessExceptionType;
  stage: AutomationStage;
  // Present when the blocker was resolved; absent means it is still open.
  fix?: { ms: number; by: Owner };
}

interface SampleCase {
  n: number;
  name: string;
  registration: string;
  jurisdiction: JurisdictionCode;
  owner: Owner;
  status: AutomationStatus;
  stage: AutomationStage;
  // Completed cases: the onboarded week, counted back from the current week (0 = this week).
  weeksAgo?: number;
  // Open cases: fixed age.
  ageMs?: number;
  blockers: SampleBlocker[];
}

function done(n: number, name: string, registration: string, jurisdiction: JurisdictionCode, owner: Owner, weeksAgo: number, blockers: SampleBlocker[] = []): SampleCase {
  return { n, name, registration, jurisdiction, owner, status: "COMPLETED", stage: "COMPLETE", weeksAgo, blockers };
}

function open(n: number, name: string, registration: string, owner: Owner, status: AutomationStatus, stage: AutomationStage, ageMs: number, blockers: SampleBlocker[] = []): SampleCase {
  return { n, name, registration, jurisdiction: "SG", owner, status, stage, ageMs, blockers };
}

const fixed = (type: BusinessExceptionType, stage: AutomationStage, ms: number, by: Owner): SampleBlocker => ({ type, stage, fix: { ms, by } });
const raised = (type: BusinessExceptionType, stage: AutomationStage): SampleBlocker => ({ type, stage });

export const SAMPLE_CASES: readonly SampleCase[] = [
  // Onboarded 7 weeks ago
  done(1, "Harbourline Logistics Pte. Ltd.", "201603318K", "SG", "ethan", 7),
  done(2, "Tanjong Crest Foods Pte. Ltd.", "201711052M", "SG", "ryan", 7, [fixed("DOCUMENT_LOW_CONFIDENCE", "DOCUMENT", 5 * HOUR, "ryan")]),
  done(3, "Southern Reef Mining Pty Ltd", "51824753556", "AU", "ethan", 7),
  // 6 weeks ago
  done(4, "Kallang Precision Works Pte. Ltd.", "201509876D", "SG", "ryan", 6),
  done(5, "Emerald Quay Advisory Pte. Ltd.", "201814402W", "SG", "viewer", 6),
  done(6, "Lumen Grid Technologies Pte. Ltd.", "201920318H", "SG", "ethan", 6, [fixed("OWNERSHIP_REVIEW_REQUIRED", "OWNERSHIP", 26 * HOUR, "ethan")]),
  // 5 weeks ago
  done(7, "Bukit Timah Dental Group Pte. Ltd.", "201606621Z", "SG", "ethan", 5),
  done(8, "Redhill Interiors Pte. Ltd.", "201712087C", "SG", "ryan", 5),
  done(9, "Marina Coast Shipping Pte. Ltd.", "201502245E", "SG", "ryan", 5, [fixed("EXISTING_PARTY_REVIEW_REQUIRED", "GOLDTIER_SEARCH", 3.5 * HOUR, "ryan")]),
  done(10, "Orchard Lane Capital Pte. Ltd.", "202003114N", "SG", "ethan", 5),
  done(11, "Seletar Aero Components Pte. Ltd.", "201811930J", "SG", "viewer", 5, [fixed("DOCUMENT_REQUIRED_FIELD_MISSING", "DOCUMENT", 7 * HOUR, "viewer")]),
  done(12, "Banksia Ridge Agriculture Pty Ltd", "63109472815", "AU", "ryan", 5),
  // 4 weeks ago
  done(13, "Clementi Learning Hub Pte. Ltd.", "201707734P", "SG", "ethan", 4),
  done(14, "Pasir Panjang Cold Chain Pte. Ltd.", "201604409B", "SG", "ryan", 4),
  done(15, "Raffles Row Partners Pte. Ltd.", "201919821T", "SG", "ethan", 4, [
    fixed("REGISTRY_REVIEW_REQUIRED", "REGISTRY", 2.5 * HOUR, "ethan"),
    fixed("DOCUMENT_LOW_CONFIDENCE", "DOCUMENT", 4 * HOUR, "ethan"),
  ]),
  done(16, "Coral Coast Hospitality Pty Ltd", "74006138291", "AU", "ryan", 4, [fixed("OWNERSHIP_INCOMPLETE", "OWNERSHIP", 30 * HOUR, "ryan")]),
  // 3 weeks ago
  done(17, "Sentosa Leisure Holdings Pte. Ltd.", "201813356G", "SG", "ryan", 3),
  done(18, "Jurong Polymer Supplies Pte. Ltd.", "201508812V", "SG", "viewer", 3),
  done(19, "Novena Health Analytics Pte. Ltd.", "202104475Q", "SG", "ethan", 3, [fixed("DOCUMENT_LOW_CONFIDENCE", "DOCUMENT", 6 * HOUR, "ethan")]),
  done(20, "Changi Freight Brokers Pte. Ltd.", "201710093F", "SG", "ethan", 3),
  // 2 weeks ago
  done(21, "Tiong Bahru Bakehouse Pte. Ltd.", "201611578L", "SG", "ryan", 2),
  done(22, "Keppel Bay Marine Services Pte. Ltd.", "201505536S", "SG", "ryan", 2, [fixed("OWNERSHIP_REVIEW_REQUIRED", "OWNERSHIP", 20 * HOUR, "ethan")]),
  done(23, "Geylang Textile Traders Pte. Ltd.", "201802264X", "SG", "ethan", 2),
  done(24, "Punggol Green Energy Pte. Ltd.", "202006691A", "SG", "ethan", 2),
  done(25, "Queenstown Data Systems Pte. Ltd.", "201916107U", "SG", "viewer", 2),
  done(26, "Holland Village Studios Pte. Ltd.", "201714448Y", "SG", "ryan", 2),
  done(27, "Karri Valley Timber Pty Ltd", "85230617440", "AU", "ethan", 2),
  // Last week
  done(28, "Bedok Industrial Coatings Pte. Ltd.", "201609925R", "SG", "ethan", 1, [fixed("EXISTING_PARTY_REVIEW_REQUIRED", "GOLDTIER_SEARCH", 2 * HOUR, "ethan")]),
  done(29, "Serangoon Pharma Distribution Pte. Ltd.", "201807718K", "SG", "ryan", 1),
  done(30, "Woodlands Auto Parts Pte. Ltd.", "201503380M", "SG", "viewer", 1, [fixed("OWNERSHIP_INCOMPLETE", "OWNERSHIP", 18 * HOUR, "viewer")]),
  done(31, "Tampines Retail Collective Pte. Ltd.", "202011246D", "SG", "ryan", 1),
  done(32, "Wattle Creek Wines Pty Ltd", "96418205733", "AU", "ethan", 1, [fixed("DOCUMENT_REQUIRED_FIELD_MISSING", "DOCUMENT", 9 * HOUR, "ethan")]),
  // This week
  done(33, "Sembawang Hydraulics Pte. Ltd.", "201712659W", "SG", "ethan", 0),
  done(34, "Dhoby Ghaut Media Pte. Ltd.", "201920043E", "SG", "ryan", 0, [fixed("DOCUMENT_LOW_CONFIDENCE", "DOCUMENT", 1.5 * HOUR, "ryan")]),
  // Open cases
  open(35, "Ang Mo Kio Robotics Pte. Ltd.", "202008857H", "ethan", "RUNNING", "DOCUMENT", 3 * HOUR),
  open(36, "Telok Ayer Ventures Pte. Ltd.", "201817792B", "viewer", "RUNNING", "OWNERSHIP", 6 * HOUR),
  open(37, "Boon Lay Packaging Pte. Ltd.", "201604438N", "ryan", "PENDING_INPUTS", "DOCUMENT", 2 * DAY + 4 * HOUR),
  open(38, "Yishun Home Care Services Pte. Ltd.", "201911163C", "ryan", "RUNNING", "READINESS", DAY + 2 * HOUR),
  open(39, "Bishan Fintech Labs Pte. Ltd.", "202102290K", "viewer", "RESUMING", "OWNERSHIP", 4 * DAY + 5 * HOUR, [fixed("OWNERSHIP_REVIEW_REQUIRED", "OWNERSHIP", 22 * HOUR, "viewer")]),
  open(40, "Pioneer Steel Fabricators Pte. Ltd.", "201507741G", "ethan", "RUNNING", "GOLDTIER_SEARCH", 40 * MINUTE),
  open(41, "Hougang Pet Supplies Pte. Ltd.", "201713380T", "ethan", "WAITING_FOR_REVIEW", "DOCUMENT", 5 * DAY + 3 * HOUR, [raised("DOCUMENT_LOW_CONFIDENCE", "DOCUMENT")]),
  open(42, "Sengkang Solar Installers Pte. Ltd.", "202005518F", "ryan", "WAITING_FOR_REVIEW", "OWNERSHIP", 12 * DAY + 6 * HOUR, [raised("OWNERSHIP_INCOMPLETE", "OWNERSHIP")]),
  open(43, "Kranji Agritech Pte. Ltd.", "201810027L", "viewer", "WAITING_FOR_REVIEW", "DOCUMENT", 8 * DAY + HOUR, [raised("DOCUMENT_REQUIRED_FIELD_MISSING", "DOCUMENT")]),
  open(44, "Toa Payoh Electrical Pte. Ltd.", "201602289S", "ryan", "WAITING_FOR_REVIEW", "GOLDTIER_SEARCH", 3 * DAY + 7 * HOUR, [raised("EXISTING_PARTY_REVIEW_REQUIRED", "GOLDTIER_SEARCH")]),
  open(45, "Bugis Street Eateries Pte. Ltd.", "201916654V", "viewer", "WAITING_FOR_REVIEW", "REGISTRY", 19 * DAY + 4 * HOUR, [raised("REGISTRY_REVIEW_REQUIRED", "REGISTRY")]),
  open(46, "Marine Parade Wellness Pte. Ltd.", "201709913Q", "ethan", "RECOVERY_PENDING", "MOCK_GOLDTIER", 26 * DAY + 2 * HOUR, [raised("TARGET_PARTIAL_REVIEW_REQUIRED", "MOCK_GOLDTIER")]),
];

// ---- Per-case derivations (deterministic) ----

function caseId(item: SampleCase): string {
  return `${SAMPLE_CASE_ID_PREFIX}${String(item.n).padStart(4, "0")}`;
}

function priorityOf(item: SampleCase): number | null {
  return item.n % 3 === 0 ? null : ((item.n * 7) % 10) + 1;
}

// Steps with a recorded processing duration: all of them once complete; for an open case the
// steps before its current one, plus the current step when it stopped there for review.
function recordedStages(item: SampleCase): AutomationStage[] {
  if (item.status === "COMPLETED") return [...PIPELINE];
  const index = PIPELINE.indexOf(item.stage);
  return PIPELINE.slice(0, BLOCKED_STATUSES.includes(item.status) ? index + 1 : index);
}

function stageDurationMs(item: SampleCase, stage: AutomationStage): number {
  const speed = 80 + ((item.n * 13) % 45); // 80%..124% of the typical step time
  const blockedHere = item.blockers.some((blocker) => blocker.stage === stage);
  const ms = (BASE_STAGE_MS[stage] * speed * (blockedHere ? 1.4 : 1)) / 100;
  return Math.round(ms / SECOND) * SECOND;
}

function stageDurations(item: SampleCase): Map<AutomationStage, number> {
  return new Map(recordedStages(item).map((stage) => [stage, stageDurationMs(item, stage)]));
}

function fixTotalMs(item: SampleCase): number {
  return item.blockers.reduce((sum, blocker) => sum + (blocker.fix?.ms ?? 0), 0);
}

// Completed cases: recorded processing + time spent fixing blockers + queueing between steps.
function completedDurationMs(item: SampleCase): number {
  let processing = 0;
  for (const ms of stageDurations(item).values()) processing += ms;
  return processing + fixTotalMs(item) + RUN_OVERHEAD_MS;
}

function elapsedMs(item: SampleCase): number {
  return item.status === "COMPLETED" ? completedDurationMs(item) : item.ageMs ?? 0;
}

function hadIntervention(item: SampleCase): boolean {
  return item.blockers.length > 0;
}

function formatFixHours(ms: number): string {
  return `${(ms / HOUR).toFixed(1)}h`;
}

// Same wording rules as the backend delay note.
function delayNote(item: SampleCase): string | null {
  if (item.status === "COMPLETED") {
    if (!hadIntervention(item)) return "Zero-touch";
    const slowest = item.blockers
      .filter((blocker) => blocker.fix)
      .reduce<SampleBlocker | null>((best, blocker) => (best === null || blocker.fix!.ms > best.fix!.ms ? blocker : best), null);
    return slowest ? `${BUSINESS_EXCEPTION_TYPE_LABELS[slowest.type]} · ${formatFixHours(slowest.fix!.ms)} fix` : null;
  }
  const openBlocker = item.blockers.find((blocker) => !blocker.fix);
  return openBlocker ? BUSINESS_EXCEPTION_TYPE_LABELS[openBlocker.type] : null;
}

function progressPercent(item: SampleCase): number {
  if (item.status === "COMPLETED") return 100;
  return Math.round((PIPELINE.indexOf(item.stage) / PIPELINE.length) * 100);
}

function ownerUserId(owner: Owner, actor: AuthenticatedProfile): string {
  return owner === "viewer" ? actor.user_id : SAMPLE_PEOPLE[owner].user_id;
}

function ownerName(owner: Owner, actor: AuthenticatedProfile): string {
  return owner === "viewer" ? actor.display_name : SAMPLE_PEOPLE[owner].name;
}

function mean(values: number[]): number | null {
  return values.length ? Math.floor(values.reduce((sum, value) => sum + value, 0) / values.length) : null;
}

// ---- Time anchoring ----
// Sample ages and durations are fixed. Dates are only placed relative to the live snapshot so
// the sample weeks line up with the live weekly buckets; they are never displayed.

function mondayUtc(iso: string): number {
  const day = new Date(iso);
  const midnight = Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate());
  return midnight - ((day.getUTCDay() + 6) % 7) * DAY;
}

function weekStarts(live: DashboardSnapshot): string[] {
  const liveWeeks = live.weekly_onboarded.map((week) => week.week_start);
  if (liveWeeks.length) return liveWeeks;
  const current = mondayUtc(live.data_as_of);
  return Array.from({ length: WEEKLY_WEEKS }, (_, index) => new Date(current - (WEEKLY_WEEKS - 1 - index) * WEEK).toISOString().slice(0, 10));
}

function toCaseItem(item: SampleCase, actor: AuthenticatedProfile, asOf: number, currentMonday: number): DashboardCaseItem {
  const elapsed = elapsedMs(item);
  let createdAt: number;
  let updatedAt: number;
  let completedAt: number | null = null;
  if (item.status === "COMPLETED") {
    // Mid-week for past weeks; this week's completions sit at the start of the week.
    const target = currentMonday - (item.weeksAgo ?? 0) * WEEK + (item.weeksAgo ? 2 * DAY + (item.n % 3) * DAY : HOUR);
    completedAt = Math.min(target, asOf);
    createdAt = completedAt - elapsed;
    updatedAt = completedAt;
  } else {
    createdAt = asOf - elapsed;
    updatedAt = asOf - Math.min(elapsed, 2 * HOUR);
  }
  return {
    case_id: caseId(item),
    requested_uen: item.registration,
    legal_name: item.name,
    team_id: teamOf(item),
    team_display_name: SAMPLE_TEAMS[teamOf(item)],
    priority: priorityOf(item),
    status: item.status,
    current_stage: item.stage,
    progress_percent: progressPercent(item),
    final_outcome: item.status === "COMPLETED" ? "MOCK_GOLDTIER_SUBMITTED" : null,
    created_at: new Date(createdAt).toISOString(),
    updated_at: new Date(updatedAt).toISOString(),
    completed_at: completedAt === null ? null : new Date(completedAt).toISOString(),
    case_elapsed_ms: elapsed,
    delay_note: delayNote(item),
    created_by_display_name: ownerName(item.owner, actor),
  };
}

// ---- Aggregates (mirror the backend dashboard rules) ----

function stageTiming(cases: readonly SampleCase[]): DashboardStageTiming[] {
  return PIPELINE.map((stage) => {
    const clean: number[] = [];
    const withBlocker: number[] = [];
    const timings: DashboardStageCaseTiming[] = [];
    let blockedCount = 0;
    for (const item of cases) {
      const hadBlocker = item.blockers.some((blocker) => blocker.stage === stage);
      if (hadBlocker) blockedCount += 1;
      const duration = stageDurations(item).get(stage);
      if (duration === undefined) continue;
      (hadBlocker ? withBlocker : clean).push(duration);
      timings.push({ case_id: caseId(item), requested_uen: item.registration, legal_name: item.name, duration_ms: duration, had_blocker: hadBlocker });
    }
    return {
      stage,
      clean_mean_ms: mean(clean),
      clean_count: clean.length,
      with_blocker_mean_ms: mean(withBlocker),
      with_blocker_count: withBlocker.length,
      combined_mean_ms: mean([...clean, ...withBlocker]),
      blocked_count: blockedCount,
      top_cases: timings.sort((a, b) => b.duration_ms - a.duration_ms).slice(0, STAGE_TOP_CASES),
    };
  });
}

function exceptionBreakdown(cases: readonly SampleCase[]): DashboardExceptionCount[] {
  const counts = new Map<BusinessExceptionType, number>();
  for (const item of cases) for (const blocker of item.blockers) counts.set(blocker.type, (counts.get(blocker.type) ?? 0) + 1);
  return rankExceptions(counts);
}

function rankExceptions(counts: Map<BusinessExceptionType, number>): DashboardExceptionCount[] {
  return [...counts.entries()]
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
    .map(([exception_type, count]) => ({ exception_type, count }));
}

function weeklyOnboarded(cases: readonly SampleCase[], weeks: string[]): DashboardWeeklyOnboarded[] {
  return weeks.map((week_start, index) => {
    const weeksAgo = weeks.length - 1 - index;
    const by_jurisdiction: Partial<Record<JurisdictionCode, number>> = {};
    for (const item of cases) {
      if (item.status !== "COMPLETED" || item.weeksAgo !== weeksAgo) continue;
      by_jurisdiction[item.jurisdiction] = (by_jurisdiction[item.jurisdiction] ?? 0) + 1;
    }
    return { week_start, by_jurisdiction, unresolved_count: 0 };
  });
}

function timingSummary(cases: readonly SampleCase[]): DashboardTimingSummary {
  const completed = cases.filter((item) => item.status === "COMPLETED");
  const zeroTouch = completed.filter((item) => !hadIntervention(item));
  const blocked = completed.filter(hadIntervention);
  return {
    mean_total_duration_ms: mean(completed.map(completedDurationMs)),
    zero_touch_mean_duration_ms: mean(zeroTouch.map(completedDurationMs)),
    zero_touch_count: zeroTouch.length,
    blocked_mean_duration_ms: mean(blocked.map(completedDurationMs)),
    blocked_count: blocked.length,
  };
}

// Case load belongs to the creator; blocker fixes belong to the recorded resolver. Like the
// backend, rows are built over the whole sample portfolio and narrowed for My work.
function workload(actor: AuthenticatedProfile): DashboardWorkloadRow[] {
  // Keyed by user ID: when Ethan or Ryan is signed in, their "viewer" cases join their own row.
  const people = new Map<string, { owner: Owner; open: SampleCase[]; completed: number; fixes: number[] }>();
  const entry = (owner: Owner) => {
    const userId = ownerUserId(owner, actor);
    let row = people.get(userId);
    if (!row) { row = { owner, open: [], completed: 0, fixes: [] }; people.set(userId, row); }
    return row;
  };
  for (const item of SAMPLE_CASES) {
    const row = entry(item.owner);
    if (item.status === "COMPLETED") row.completed += 1;
    else row.open.push(item);
    for (const blocker of item.blockers) if (blocker.fix) entry(blocker.fix.by).fixes.push(blocker.fix.ms);
  }
  return sortWorkload([...people.entries()].map(([userId, row]) => ({
    user_id: userId,
    display_name: ownerName(row.owner, actor),
    open_cases: row.open.length,
    oldest_open_age_ms: row.open.length ? Math.max(...row.open.map(elapsedMs)) : null,
    completed_cases: row.completed,
    blockers_resolved: row.fixes.length,
    mean_fix_time_ms: mean(row.fixes),
  })));
}

function sortWorkload(rows: DashboardWorkloadRow[]): DashboardWorkloadRow[] {
  return rows.sort((a, b) => b.open_cases - a.open_cases || (a.user_id < b.user_id ? -1 : a.user_id > b.user_id ? 1 : 0));
}

function casesInView(view: DashboardSnapshot["view"], actor: AuthenticatedProfile): readonly SampleCase[] {
  return view === "mine" ? SAMPLE_CASES.filter((item) => ownerUserId(item.owner, actor) === actor.user_id) : SAMPLE_CASES;
}

/** The sample portfolio on its own, shaped like a backend snapshot for the same view. */
export function buildSampleSnapshot(live: DashboardSnapshot, actor: AuthenticatedProfile): DashboardSnapshot {
  const cases = casesInView(live.view, actor);
  const asOf = Date.parse(live.data_as_of);
  const weeks = weekStarts(live);
  const currentMonday = Date.parse(`${weeks[weeks.length - 1]}T00:00:00Z`);
  const items = cases.map((item) => toCaseItem(item, actor, asOf, currentMonday));
  const total = cases.length;
  const completed = cases.filter((item) => item.status === "COMPLETED");
  const prioritised = cases.filter((item) => priorityOf(item) !== null).length;
  const priorities = [...Array.from({ length: 10 }, (_, index) => 10 - index), null];
  return {
    historical_trend: [],
    scope: live.scope,
    view: live.view,
    data_as_of: live.data_as_of,
    totals: {
      total_cases: total,
      completed_cases: completed.length,
      non_completed_cases: total - completed.length,
      completion_rate: total ? completed.length / total : 0,
      prioritised_cases: prioritised,
      unprioritised_cases: total - prioritised,
    },
    zero_touch_rate: completed.length ? completed.filter((item) => !hadIntervention(item)).length / completed.length : 0,
    timing: timingSummary(cases),
    status_breakdown: ALL_STATUSES.map((status) => ({ status, count: cases.filter((item) => item.status === status).length })),
    priority_breakdown: priorities.map((priority) => ({ priority, count: cases.filter((item) => priorityOf(item) === priority).length })),
    team_breakdown: (Object.keys(SAMPLE_TEAMS) as SampleTeamId[])
      .map((teamId) => ({
        team_id: teamId,
        team_display_name: SAMPLE_TEAMS[teamId],
        client_scope_label: SAMPLE_TEAMS[teamId],
        count: items.filter((item) => item.team_id === teamId).length,
      }))
      .filter((row) => row.count > 0),
    stage_timing: stageTiming(cases),
    exception_breakdown: exceptionBreakdown(cases),
    weekly_onboarded: weeklyOnboarded(cases, weeks),
    workload_by_person: workload(actor).filter((row) => live.view === "team" || row.user_id === actor.user_id),
    recent_cases: [...items].sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1)).slice(0, 10),
    top_active_cases: items.filter((item) => item.status !== "COMPLETED").slice(0, 5),
    scoped_cases: items,
  };
}

// ---- Adding the sample portfolio on top of the live snapshot ----

// Combine two means by their sample counts. A mean reported without a count still counts once.
function combineMeans(parts: Array<[number | null, number]>): number | null {
  let weight = 0;
  let sum = 0;
  for (const [value, count] of parts) {
    if (value === null || value === undefined) continue;
    const n = Math.max(1, count);
    weight += n;
    sum += value * n;
  }
  return weight ? Math.floor(sum / weight) : null;
}

function addCounts<K>(live: Array<{ key: K; count: number }>, sample: Array<{ key: K; count: number }>): Array<{ key: K; count: number }> {
  const merged = live.map((item) => ({ ...item }));
  for (const item of sample) {
    const match = merged.find((entry) => entry.key === item.key);
    if (match) match.count += item.count;
    else merged.push({ ...item });
  }
  return merged;
}

function mergeStage(live: DashboardStageTiming | undefined, sample: DashboardStageTiming | undefined): DashboardStageTiming {
  if (!live) return sample!;
  if (!sample) return live;
  return {
    stage: live.stage,
    clean_mean_ms: combineMeans([[live.clean_mean_ms, live.clean_count], [sample.clean_mean_ms, sample.clean_count]]),
    clean_count: live.clean_count + sample.clean_count,
    with_blocker_mean_ms: combineMeans([[live.with_blocker_mean_ms, live.with_blocker_count], [sample.with_blocker_mean_ms, sample.with_blocker_count]]),
    with_blocker_count: live.with_blocker_count + sample.with_blocker_count,
    combined_mean_ms: combineMeans([
      [live.combined_mean_ms, live.clean_count + live.with_blocker_count],
      [sample.combined_mean_ms, sample.clean_count + sample.with_blocker_count],
    ]),
    blocked_count: live.blocked_count + sample.blocked_count,
    top_cases: [...live.top_cases, ...sample.top_cases].sort((a, b) => b.duration_ms - a.duration_ms).slice(0, STAGE_TOP_CASES),
  };
}

function mergeWorkload(live: DashboardWorkloadRow[], sample: DashboardWorkloadRow[]): DashboardWorkloadRow[] {
  const rows = live.map((row) => ({ ...row }));
  for (const extra of sample) {
    const row = rows.find((item) => item.user_id === extra.user_id);
    if (!row) { rows.push({ ...extra }); continue; }
    row.mean_fix_time_ms = combineMeans([[row.mean_fix_time_ms, row.blockers_resolved], [extra.mean_fix_time_ms, extra.blockers_resolved]]);
    row.open_cases += extra.open_cases;
    row.completed_cases += extra.completed_cases;
    row.blockers_resolved += extra.blockers_resolved;
    row.oldest_open_age_ms = row.oldest_open_age_ms === null ? extra.oldest_open_age_ms
      : extra.oldest_open_age_ms === null ? row.oldest_open_age_ms
      : Math.max(row.oldest_open_age_ms, extra.oldest_open_age_ms);
  }
  return sortWorkload(rows);
}

/**
 * The live snapshot with the fixed sample portfolio added on top. Live counts, cases and
 * timings are kept and the sample figures are added to them, so newly created or completed
 * cases still change the dashboard. The input snapshot is not modified.
 */
export function withOnboardingSample(live: DashboardSnapshot, actor: AuthenticatedProfile): DashboardSnapshot {
  const sample = buildSampleSnapshot(live, actor);
  const completed = live.totals.completed_cases + sample.totals.completed_cases;
  const total = live.totals.total_cases + sample.totals.total_cases;
  const liveZeroTouch = Math.round(live.zero_touch_rate * live.totals.completed_cases);
  const sampleZeroTouch = Math.round(sample.zero_touch_rate * sample.totals.completed_cases);
  const liveTimingCount = live.timing.zero_touch_count + live.timing.blocked_count;
  const sampleTimingCount = sample.timing.zero_touch_count + sample.timing.blocked_count;
  const exceptionCounts = new Map<BusinessExceptionType, number>();
  for (const item of [...live.exception_breakdown, ...sample.exception_breakdown]) {
    exceptionCounts.set(item.exception_type, (exceptionCounts.get(item.exception_type) ?? 0) + item.count);
  }
  const stages = [...live.stage_timing.map((row) => row.stage), ...sample.stage_timing.map((row) => row.stage)]
    .filter((stage, index, all) => all.indexOf(stage) === index);
  return {
    ...live,
    totals: {
      total_cases: total,
      completed_cases: completed,
      non_completed_cases: live.totals.non_completed_cases + sample.totals.non_completed_cases,
      completion_rate: total ? completed / total : 0,
      prioritised_cases: live.totals.prioritised_cases + sample.totals.prioritised_cases,
      unprioritised_cases: live.totals.unprioritised_cases + sample.totals.unprioritised_cases,
    },
    zero_touch_rate: completed ? (liveZeroTouch + sampleZeroTouch) / completed : 0,
    timing: {
      mean_total_duration_ms: combineMeans([[live.timing.mean_total_duration_ms, liveTimingCount], [sample.timing.mean_total_duration_ms, sampleTimingCount]]),
      zero_touch_mean_duration_ms: combineMeans([[live.timing.zero_touch_mean_duration_ms, live.timing.zero_touch_count], [sample.timing.zero_touch_mean_duration_ms, sample.timing.zero_touch_count]]),
      zero_touch_count: live.timing.zero_touch_count + sample.timing.zero_touch_count,
      blocked_mean_duration_ms: combineMeans([[live.timing.blocked_mean_duration_ms, live.timing.blocked_count], [sample.timing.blocked_mean_duration_ms, sample.timing.blocked_count]]),
      blocked_count: live.timing.blocked_count + sample.timing.blocked_count,
    },
    status_breakdown: addCounts(
      live.status_breakdown.map((item) => ({ key: item.status, count: item.count })),
      sample.status_breakdown.map((item) => ({ key: item.status, count: item.count })),
    ).map((item) => ({ status: item.key, count: item.count })),
    priority_breakdown: addCounts(
      live.priority_breakdown.map((item) => ({ key: item.priority, count: item.count })),
      sample.priority_breakdown.map((item) => ({ key: item.priority, count: item.count })),
    ).map((item) => ({ priority: item.key, count: item.count })),
    team_breakdown: [...live.team_breakdown, ...sample.team_breakdown].reduce<DashboardSnapshot["team_breakdown"]>((merged, row) => {
      const match = merged.find((entry) => entry.team_id === row.team_id);
      if (match) match.count += row.count;
      else merged.push({ ...row });
      return merged;
    }, []),
    stage_timing: stages.map((stage) => mergeStage(
      live.stage_timing.find((row) => row.stage === stage),
      sample.stage_timing.find((row) => row.stage === stage),
    )),
    exception_breakdown: rankExceptions(exceptionCounts),
    weekly_onboarded: (live.weekly_onboarded.length ? live.weekly_onboarded : sample.weekly_onboarded).map((week) => {
      const extra = sample.weekly_onboarded.find((item) => item.week_start === week.week_start);
      if (!extra || week === extra) return week;
      const by_jurisdiction = { ...week.by_jurisdiction };
      for (const [code, count] of Object.entries(extra.by_jurisdiction) as Array<[JurisdictionCode, number]>) {
        by_jurisdiction[code] = (by_jurisdiction[code] ?? 0) + count;
      }
      return { week_start: week.week_start, by_jurisdiction, unresolved_count: week.unresolved_count + extra.unresolved_count };
    }),
    workload_by_person: mergeWorkload(live.workload_by_person, sample.workload_by_person),
    recent_cases: [...live.recent_cases, ...sample.recent_cases],
    top_active_cases: [...live.top_active_cases, ...sample.top_active_cases],
    scoped_cases: [...live.scoped_cases, ...sample.scoped_cases],
  };
}

/** Number of sample cases added to a snapshot of this view. */
export function sampleCaseCount(view: DashboardSnapshot["view"], actor: AuthenticatedProfile): number {
  return casesInView(view, actor).length;
}

// ---- Sample cases outside the dashboard (Cases tab and read-only case page) ----

/** Dates are placed relative to `asOf`, the same way the dashboard places them. */
function anchoredItems(actor: AuthenticatedProfile, asOf: number): Array<{ source: SampleCase; item: DashboardCaseItem }> {
  const currentMonday = mondayUtc(new Date(asOf).toISOString());
  return SAMPLE_CASES.map((source) => ({ source, item: toCaseItem(source, actor, asOf, currentMonday) }));
}

export interface SampleCaseRow extends DashboardCaseItem {
  jurisdiction: JurisdictionCode;
  /** Blocker types still open on the case. */
  open_blocker_types: BusinessExceptionType[];
  /** Number of blockers raised on the case, open or resolved. */
  blocker_count: number;
}

function toRow(source: SampleCase, item: DashboardCaseItem): SampleCaseRow {
  return {
    ...item,
    jurisdiction: source.jurisdiction,
    open_blocker_types: source.blockers.filter((blocker) => !blocker.fix).map((blocker) => blocker.type),
    blocker_count: source.blockers.length,
  };
}

/** Every sample case as a list row, for the Cases tab. */
export function sampleCaseRows(actor: AuthenticatedProfile, asOf: number = Date.now()): SampleCaseRow[] {
  return anchoredItems(actor, asOf).map(({ source, item }) => toRow(source, item));
}

export type SampleStepState = "done" | "review" | "in_progress" | "waiting_inputs" | "not_started";

export interface SampleCaseStep {
  stage: AutomationStage;
  state: SampleStepState;
  /** Recorded processing time; null when the step has not run yet or is still running. */
  duration_ms: number | null;
}

export interface SampleCaseBlocker {
  type: BusinessExceptionType;
  stage: AutomationStage;
  resolved: boolean;
  fix_ms: number | null;
  resolved_by: string | null;
}

export interface SampleCaseDetail extends SampleCaseRow {
  steps: SampleCaseStep[];
  blockers: SampleCaseBlocker[];
}

function stepState(source: SampleCase, stage: AutomationStage, recorded: boolean): SampleStepState {
  if (source.status === "COMPLETED") return "done";
  if (stage === source.stage) return recorded ? "review" : source.status === "PENDING_INPUTS" ? "waiting_inputs" : "in_progress";
  return recorded ? "done" : "not_started";
}

/** One sample case with its steps and blockers, or null when the ID is not a sample case. */
export function sampleCaseDetail(caseId: string, actor: AuthenticatedProfile, asOf: number = Date.now()): SampleCaseDetail | null {
  const match = anchoredItems(actor, asOf).find(({ item }) => item.case_id === caseId);
  if (!match) return null;
  const { source, item } = match;
  const durations = stageDurations(source);
  return {
    ...toRow(source, item),
    steps: PIPELINE.map((stage) => ({
      stage,
      state: stepState(source, stage, durations.has(stage)),
      duration_ms: durations.get(stage) ?? null,
    })),
    blockers: source.blockers.map((blocker) => ({
      type: blocker.type,
      stage: blocker.stage,
      resolved: Boolean(blocker.fix),
      fix_ms: blocker.fix?.ms ?? null,
      resolved_by: blocker.fix ? ownerName(blocker.fix.by, actor) : null,
    })),
  };
}
