import { Fragment, useEffect, useId, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import AiInsights from "./AiInsights";
import { proposalsAwaitingDecision } from "./aiInsightFindings";
import DirectorTeamFilter from "./DirectorTeamFilter";
import { MockCategoryCards } from "./mockDashboards/MockDashboards";
import { isSampleCaseId, sampleCaseCount, withOnboardingSample } from "./mockDashboards/onboardingSample";
import type { DashboardDateRange } from "../api";
import { activityQueryOptions, dashboardQueryOptions, policyCatalogueQueryOptions } from "../caseQueries";
import { paths } from "../navigation";
import { formatDateNoSeconds, formatDuration as formatRecordedDuration, formatTimestamp } from "../shared";
import type {
  AttentionLevel,
  AttentionReason,
  AuthenticatedProfile,
  AutomationStage,
  AutomationStatus,
  BusinessExceptionType,
  DashboardCaseItem,
  DashboardExceptionCount,
  DashboardSnapshot,
  DashboardStageTiming,
  DashboardAttentionPolicy,
  DashboardTeamCount,
  JurisdictionCode,
  PolicyCatalogue,
  SlaStatus,
} from "../types";
import { BUSINESS_EXCEPTION_TYPE_LABELS } from "../types";

export const STAGE_LABELS: Record<AutomationStage, string> = {
  REGISTRY: "Registry verification",
  GOLDTIER_SEARCH: "Existing-customer search",
  DOCUMENT: "Document verification",
  OWNERSHIP: "Ownership & UBO",
  READINESS: "Submission readiness",
  MOCK_GOLDTIER: "GoldTier submission package",
  COMPLETE: "Complete",
};

export const JURISDICTION_LABELS: Record<JurisdictionCode, string> = {
  SG: "Singapore",
  AU: "Australia",
  MY: "Malaysia",
  HK: "Hong Kong",
};

const JURISDICTION_COLORS: Record<JurisdictionCode, string> = {
  SG: "var(--color-accent-400)",
  AU: "var(--color-accent-700)",
  MY: "var(--color-accent-200)",
  HK: "var(--color-neutral-400)",
};

const BLOCKED_STATUSES: readonly AutomationStatus[] = ["WAITING_FOR_REVIEW", "RECOVERY_PENDING", "TECHNICAL_FAILURE"];

function statusTagClass(status: AutomationStatus): string {
  if (status === "COMPLETED") return "tag tag-neutral";
  if (BLOCKED_STATUSES.includes(status)) return "tag tag-warn";
  return "tag tag-accent";
}

function formatDuration(ms: number | null | undefined): string {
  return ms === null || ms === undefined ? "—" : formatRecordedDuration(ms);
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatRate(value: number | null): string {
  return value === null ? "—" : formatPercent(value);
}

const DAY_MS = 86_400_000;

function formatDays(ms: number): string {
  const days = Math.round(ms / DAY_MS);
  return `${days} day${days === 1 ? "" : "s"}`;
}

// Provisional D-127 display rules (see DashboardSnapshot.attention_policy).
export const SLA_LABELS: Record<SlaStatus, string> = {
  ON_TRACK: "On track",
  AT_RISK: "At risk",
  OVERDUE: "Overdue",
  MET: "Met",
  MISSED: "Missed",
};
const SLA_TAGS: Record<SlaStatus, string> = {
  ON_TRACK: "tag tag-ok",
  AT_RISK: "tag tag-amber",
  OVERDUE: "tag tag-critical",
  MET: "tag tag-ok",
  MISSED: "tag tag-critical",
};
export const ATTENTION_LABELS: Record<AttentionLevel, string> = { HIGH: "High", MEDIUM: "Medium", LOW: "Low" };
const ATTENTION_TAGS: Record<AttentionLevel, string> = { HIGH: "tag tag-critical", MEDIUM: "tag tag-amber", LOW: "tag tag-ok" };
const ATTENTION_RANK: Record<AttentionLevel, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

function attentionReasonLabel(reason: AttentionReason, policy: DashboardAttentionPolicy): string {
  switch (reason) {
    case "OVERDUE": return `Past the ${formatDays(policy.sla_target_ms)} target`;
    case "BLOCKER_OPEN_OVER_7_DAYS": return `Blocker open over ${formatDays(policy.stale_blocker_ms)}`;
    case "NO_UPDATE_5_DAYS": return `No update for ${formatDays(policy.inactivity_ms)}`;
    case "SLA_AT_RISK": return `Target within ${formatDays(policy.at_risk_window_ms)}`;
    case "AWAITING_REVIEW": return "Waiting for review";
    case "AWAITING_RECOVERY": return "Waiting for recovery";
    case "AWAITING_INPUTS": return "Waiting for inputs";
    case "TECHNICAL_FAILURE": return "Technical failure";
  }
}

function SlaTag({ status }: { status: SlaStatus | null }) {
  return status ? <span className={SLA_TAGS[status]}>{SLA_LABELS[status]}</span> : <span className="text-muted">—</span>;
}

function AttentionTag({ level }: { level: AttentionLevel | null }) {
  return level ? <span className={ATTENTION_TAGS[level]}>{ATTENTION_LABELS[level]}</span> : <span className="text-muted">—</span>;
}

function SegToggle<T extends string>({ value, options, onChange }: {
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  return (
    <div className="seg-toggle">
      {options.map((option) => (
        <button key={option.value} type="button" aria-pressed={value === option.value} onClick={() => onChange(option.value)}>{option.label}</button>
      ))}
    </div>
  );
}

type SortDir = "asc" | "desc";

function useSortableTable<T>(
  rows: T[],
  accessors: Record<string, (row: T) => string | number | null>,
  initialKey: string,
  initialDir: SortDir = "asc",
) {
  const [sortKey, setSortKey] = useState(initialKey);
  const [sortDir, setSortDir] = useState<SortDir>(initialDir);
  const sorted = useMemo(() => {
    const accessor = accessors[sortKey];
    if (!accessor) return rows;
    return [...rows].sort((a, b) => {
      const av = accessor(a);
      const bv = accessor(b);
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [rows, sortKey, sortDir]);
  const onSort = (key: string) => {
    if (key === sortKey) setSortDir((direction) => (direction === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  };
  const setSort = (key: string, dir: SortDir) => { setSortKey(key); setSortDir(dir); };
  return { sorted, sortKey, sortDir, onSort, setSort };
}

function SortableTh({ label, sortKey: key, activeKey, dir, onSort, align }: {
  label: string;
  sortKey: string;
  activeKey: string;
  dir: SortDir;
  onSort: (key: string) => void;
  align?: "right";
}) {
  const active = key === activeKey;
  return (
    <th scope="col" className="sortable-th" aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : undefined} style={align === "right" ? { textAlign: "right" } : undefined}>
      <button type="button" className="sort-control" onClick={() => onSort(key)}>
        {label}<span aria-hidden="true" className={`sort-caret${active ? " active" : ""}`}>{active ? (dir === "asc" ? "▲" : "▼") : "↕"}</span>
      </button>
    </th>
  );
}

const DEFAULT_PAGE_SIZE = 5;

function usePagination<T>(rows: T[], pageSize: number = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState(0);
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const clampedPage = Math.min(page, pageCount - 1);
  const pageRows = useMemo(
    () => rows.slice(clampedPage * pageSize, clampedPage * pageSize + pageSize),
    [rows, clampedPage, pageSize],
  );
  return { pageRows, page: clampedPage, setPage, pageCount, total: rows.length, pageSize };
}

function Pagination({ page, setPage, pageCount, total, pageSize }: {
  page: number;
  setPage: (page: number) => void;
  pageCount: number;
  total: number;
  pageSize: number;
}) {
  return (
    <div className="pagination">
      <span className="text-muted">{total === 0 ? "0 of 0" : `${page * pageSize + 1}–${Math.min(total, (page + 1) * pageSize)} of ${total}`}</span>
      <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>‹ Prev</button>
      {Array.from({ length: pageCount }, (_, index) => (
        <button key={index} type="button" aria-current={index === page} onClick={() => setPage(index)}>{index + 1}</button>
      ))}
      <button type="button" disabled={page >= pageCount - 1} onClick={() => setPage(page + 1)}>Next ›</button>
    </div>
  );
}

export function DashboardCategoryPicker({
  dashboard,
  onSelectOnboarding,
  unavailable = false,
}: {
  dashboard: DashboardSnapshot | undefined;
  onSelectOnboarding: () => void;
  unavailable?: boolean;
}) {
  const totals = dashboard?.totals;
  const blocked = dashboard?.status_breakdown
    .filter((item) => BLOCKED_STATUSES.includes(item.status))
    .reduce((sum, item) => sum + item.count, 0);

  return (
    <section className="ds-root ds-page dashboard-page">
      <header className="ds-page-header dashboard-header">
        <div><p className="dashboard-kicker">Client lifecycle</p><h1>Dashboard</h1><p>Choose a part of the client lifecycle to see its dashboard.</p></div>
      </header>

      <div className="category-grid">
        <article
          className="card category-card category-card--live"
          role="button"
          tabIndex={0}
          onClick={onSelectOnboarding}
          onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelectOnboarding(); } }}
        >
          <div className="category-card-top"><span className="dashboard-kicker">01</span><span className="tag tag-accent">Available</span></div>
          <h2>Onboarding</h2>
          <p className="text-muted">Registry extract, automatic checks, blockers and time per pipeline step</p>
          <div className="category-card-foot">
            {totals ? <><span>{totals.non_completed_cases} open</span><span>{blocked ?? 0} blocked</span><span>{totals.completed_cases} completed</span></> : <span>{unavailable ? "Unavailable" : "Loading…"}</span>}
            <span className="category-card-cta">View dashboard →</span>
          </div>
        </article>
        <MockCategoryCards />
      </div>
    </section>
  );
}

function StageTimingTable({ stageTiming }: { stageTiming: DashboardStageTiming[] }) {
  const detailPrefix = useId();
  const [open, setOpen] = useState<AutomationStage | null>(null);
  const indexed = useMemo(() => stageTiming.map((row, index) => ({ ...row, index })), [stageTiming]);
  const accessors = {
    order: (row: (typeof indexed)[number]) => row.index,
    step: (row: (typeof indexed)[number]) => STAGE_LABELS[row.stage],
    clean: (row: (typeof indexed)[number]) => row.clean_mean_ms,
    blocker: (row: (typeof indexed)[number]) => row.with_blocker_mean_ms,
    combined: (row: (typeof indexed)[number]) => row.combined_mean_ms,
    blocked: (row: (typeof indexed)[number]) => row.blocked_count,
    waiting: (row: (typeof indexed)[number]) => row.resolution_mean_ms,
  };
  const { sorted, sortKey, sortDir, onSort } = useSortableTable(indexed, accessors, "order");

  return (
    <article className="card">
      <h2>Time per pipeline step</h2>
      <div className="table-scroll">
        <table className="table stage-timing-table">
          <thead>
            <tr>
              <th></th>
              <SortableTh label="Step" sortKey="step" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Clean" sortKey="clean" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="With blocker" sortKey="blocker" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Combined" sortKey="combined" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Blocked" sortKey="blocked" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Waiting on a person" sortKey="waiting" activeKey={sortKey} dir={sortDir} onSort={onSort} />
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <Fragment key={row.stage}>
                <tr className="step-row">
                  <td><span className="step-index">{row.index + 1}</span></td>
                  <td><button type="button" className="sort-control" id={`${detailPrefix}-${row.stage}-toggle`} aria-expanded={open === row.stage} aria-controls={`${detailPrefix}-${row.stage}-detail`} onClick={() => setOpen(open === row.stage ? null : row.stage)}><span aria-hidden="true" className={`step-chevron${open === row.stage ? " open" : ""}`}>›</span>{STAGE_LABELS[row.stage]}</button></td>
                  <td>{formatDuration(row.clean_mean_ms)}</td>
                  <td>{formatDuration(row.with_blocker_mean_ms)}</td>
                  <td><strong>{formatDuration(row.combined_mean_ms)}</strong></td>
                  <td>{row.blocked_count > 0 ? <span className="tag tag-warn">{row.blocked_count}</span> : <span className="text-muted">—</span>}</td>
                  <td>{row.resolution_mean_ms === null ? <span className="text-muted">—</span> : <><strong>{formatDuration(row.resolution_mean_ms)}</strong><span className="cell-note">mean · {row.resolution_count} resolved</span></>}</td>
                </tr>

                  <tr className="step-detail" hidden={open !== row.stage}>
                    <td colSpan={7}><div id={`${detailPrefix}-${row.stage}-detail`} role="region" aria-labelledby={`${detailPrefix}-${row.stage}-toggle`}>
                      {row.top_cases.length === 0 && <p className="text-muted" style={{ margin: 0 }}>No recorded durations for this step.</p>}
                      {row.top_cases.map((item, index) => (
                        <div className="step-detail-row" key={item.case_id}>
                          <span>{index + 1}. {item.legal_name ?? item.requested_uen}</span>
                          <span>{item.had_blocker && <span className="tag tag-warn" style={{ marginRight: 8 }}>blocked</span>}{formatDuration(item.duration_ms)}</span>
                        </div>
                      ))}
                    </div></td>
                  </tr>

              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function WeeklyOnboardedChart({ weeks: allWeeks, includesSample }: { weeks: DashboardSnapshot["weekly_onboarded"]; includesSample: boolean }) {
  const [country, setCountry] = useState<"all" | JurisdictionCode>("all");
  const allJurisdictions = Array.from(
    new Set(allWeeks.flatMap((week) => Object.keys(week.by_jurisdiction) as JurisdictionCode[])),
  );
  const weeks = country === "all" ? allWeeks : allWeeks.map((week) => ({
    ...week,
    by_jurisdiction: { [country]: week.by_jurisdiction[country] ?? 0 },
    unresolved_count: 0,
  }));
  const totals = weeks.map((week) => Object.values(week.by_jurisdiction).reduce((sum, count) => sum + (count ?? 0), 0) + week.unresolved_count);
  const max = Math.max(1, ...totals);
  const jurisdictionsPresent = country === "all" ? allJurisdictions : [country];
  const anyUnresolved = weeks.some((week) => week.unresolved_count > 0);

  return (
    <article className="card">
      <div className="row-between">
        <h2>Onboarded per week</h2>
        {allJurisdictions.length > 1 && (
          <SegToggle value={country} onChange={setCountry} options={[{ value: "all", label: "All" }, ...allJurisdictions.map((code) => ({ value: code, label: JURISDICTION_LABELS[code] }))]} />
        )}
      </div>
      <div className="row-between">
        <span className="text-muted weekly-chart-total">{totals.reduce((sum, count) => sum + count, 0)} onboarded in 8 weeks{country === "all" ? "" : ` · ${JURISDICTION_LABELS[country]}`}</span>
        <span className="weekly-chart-legend">
          {jurisdictionsPresent.map((code) => <span key={code}><span className="weekly-chart-swatch" style={{ background: JURISDICTION_COLORS[code] }} />{JURISDICTION_LABELS[code]}</span>)}
          {anyUnresolved && <span><span className="weekly-chart-swatch" style={{ background: "var(--color-neutral-300)" }} />Unresolved</span>}
        </span>
      </div>
      <div className="weekly-chart">
        {weeks.map((week, index) => {
          const total = totals[index];
          return (
            <div className="weekly-chart-bar" key={week.week_start} style={{ height: `${Math.max(4, (total / max) * 100)}%` }}>
              <span className="weekly-chart-count">{total || ""}</span>
              {(Object.entries(week.by_jurisdiction) as Array<[JurisdictionCode, number]>).filter(([, count]) => count > 0).map(([code, count]) => (
                <div key={code} className="weekly-chart-seg" style={{ height: `${(count / Math.max(1, total)) * 100}%`, background: JURISDICTION_COLORS[code] }} title={`${JURISDICTION_LABELS[code]}: ${count}`} />
              ))}
              {week.unresolved_count > 0 && <div className="weekly-chart-seg" style={{ height: `${(week.unresolved_count / Math.max(1, total)) * 100}%`, background: "var(--color-neutral-300)" }} title={`Unresolved: ${week.unresolved_count}`} />}
            </div>
          );
        })}
      </div>
      <div className="weekly-chart-axis">{weeks.map((week) => <span key={week.week_start} className="weekly-chart-label">{week.week_start.slice(5)}</span>)}</div>
      <p className="text-muted" style={{ fontSize: 10.5, margin: "8px 0 0" }}>{includesSample ? "Completed onboardings" : "Completions recorded in this environment"} · weeks starting Monday.</p>
    </article>
  );
}

function ExceptionBreakdown({ exceptions }: { exceptions: DashboardExceptionCount[] }) {
  const total = exceptions.reduce((sum, item) => sum + item.count, 0);
  const totalFix = exceptions.reduce((sum, item) => sum + item.total_fix_ms, 0);
  const mostFrequent = exceptions.length ? Math.max(...exceptions.map((item) => item.count)) : 0;
  const accessors = {
    type: (item: DashboardExceptionCount) => BUSINESS_EXCEPTION_TYPE_LABELS[item.exception_type],
    raised: (item: DashboardExceptionCount) => item.count,
    open: (item: DashboardExceptionCount) => item.open_count,
    resolved: (item: DashboardExceptionCount) => item.resolved_count,
    mean: (item: DashboardExceptionCount) => item.mean_fix_ms,
    total: (item: DashboardExceptionCount) => item.total_fix_ms,
  };
  const { sorted, sortKey, sortDir, onSort } = useSortableTable(exceptions, accessors, "total", "desc");
  return (
    <article className="card">
      <h2>Why cases stopped · {total} exceptions</h2>
      {exceptions.length === 0 && <p className="empty-copy">No blockers were raised for your current scope.</p>}
      {exceptions.length > 0 && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <SortableTh label="Exception" sortKey="type" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Raised" sortKey="raised" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <th scope="col">Share</th>
                <th scope="col">Countries</th>
                <th scope="col">Last 8 weeks</th>
                <SortableTh label="Open" sortKey="open" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Resolved" sortKey="resolved" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Mean fix time" sortKey="mean" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Total fix time" sortKey="total" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              </tr>
            </thead>
            <tbody>
              {sorted.map((item) => (
                <tr key={item.exception_type}>
                  <td>{BUSINESS_EXCEPTION_TYPE_LABELS[item.exception_type]}{item.count === mostFrequent && <span className="tag tag-amber exception-flag">Most frequent</span>}</td>
                  <td>{item.count}</td>
                  <td>{total ? formatPercent(item.count / total) : "—"}</td>
                  <td>{countryBreakdown(item)}</td>
                  <td><Sparkline counts={item.weekly_counts} label={BUSINESS_EXCEPTION_TYPE_LABELS[item.exception_type]} /></td>
                  <td>{item.open_count > 0 ? <span className="tag tag-warn">{item.open_count}</span> : <span className="text-muted">—</span>}</td>
                  <td>{item.resolved_count}</td>
                  <td>{formatDuration(item.mean_fix_ms)}</td>
                  <td>
                    <strong>{item.resolved_count ? formatDuration(item.total_fix_ms) : "—"}</strong>
                    {totalFix > 0 && item.total_fix_ms > 0 && (
                      <>
                        <div className="load-bar"><div style={{ width: `${(item.total_fix_ms / totalFix) * 100}%` }} /></div>
                        <p className="load-bar-note">{formatPercent(item.total_fix_ms / totalFix)} of all fix time</p>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

function countryBreakdown(item: DashboardExceptionCount): string {
  const parts = (Object.entries(item.by_jurisdiction) as Array<[JurisdictionCode, number]>)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([code, count]) => `${code} ${count}`);
  if (item.unresolved_jurisdiction_count) parts.push(`Unresolved ${item.unresolved_jurisdiction_count}`);
  return parts.length ? parts.join(" · ") : "—";
}

function Sparkline({ counts, label }: { counts: number[]; label: string }) {
  const max = Math.max(1, ...counts);
  return (
    <span className="sparkline" role="img" aria-label={`${label}: ${counts.join(", ")} raised per week, oldest first`}>
      {counts.map((count, index) => <i key={index} style={{ height: `${Math.max(count ? 18 : 6, (count / max) * 100)}%` }} className={count ? "" : "sparkline-empty"} title={`${count}`} />)}
    </span>
  );
}

function StraightThroughPanel({ weeks, stageTiming }: { weeks: DashboardSnapshot["weekly_onboarded"]; stageTiming: DashboardStageTiming[] }) {
  const weekly = weeks.map((week) => {
    const completed = Object.values(week.by_jurisdiction).reduce((sum, count) => sum + (count ?? 0), 0) + week.unresolved_count;
    return { week_start: week.week_start, completed, rate: completed ? week.zero_touch_count / completed : null };
  });
  return (
    <article className="card">
      <h2>Straight-through processing</h2>
      <h3 className="h2a">Zero-touch rate per week</h3>
      <div className="weekly-chart weekly-chart--short" aria-label="Zero-touch rate per week">
        {weekly.map((week) => (
          <div className="weekly-chart-bar" key={week.week_start} style={{ height: `${week.rate === null ? 0 : Math.max(4, week.rate * 100)}%` }}>
            <span className="weekly-chart-count">{week.rate === null ? "—" : formatPercent(week.rate)}</span>
            {week.rate !== null && <div className="weekly-chart-seg" style={{ height: "100%", background: "var(--color-accent-400)" }} title={`${week.week_start}: ${formatPercent(week.rate)} of ${week.completed} completed`} />}
          </div>
        ))}
      </div>
      <div className="weekly-chart-axis">{weekly.map((week) => <span key={week.week_start} className="weekly-chart-label">{week.week_start.slice(5)}</span>)}</div>
      <p className="text-muted stp-note">Completed cases in the week with no recorded exception interventions. “—” means no completions that week.</p>
      <h3 className="h2a">Passed each step without stopping</h3>
      <div className="dashboard-bars">
        {stageTiming.map((row) => {
          const passed = Math.max(0, row.reached_count - row.blocked_count);
          const rate = row.reached_count ? passed / row.reached_count : null;
          return (
            <div className="dashboard-bar dashboard-bar--wide" key={row.stage}>
              <span>{STAGE_LABELS[row.stage]}</span>
              <div><i style={{ width: `${(rate ?? 0) * 100}%` }} /></div>
              <strong>{rate === null ? "—" : `${formatPercent(rate)} · ${passed}/${row.reached_count}`}</strong>
            </div>
          );
        })}
      </div>
      <p className="text-muted stp-note">Out of the cases that reached each step, including open cases.</p>
    </article>
  );
}

function TeamComparison({ teams }: { teams: DashboardTeamCount[] }) {
  const rows = teams.map((team) => {
    const countOf = (statuses: readonly AutomationStatus[]) => team.status_breakdown
      .filter((item) => statuses.includes(item.status))
      .reduce((sum, item) => sum + item.count, 0);
    const completed = countOf(["COMPLETED"]);
    return {
      team,
      completed,
      open: team.count - completed,
      blocked: countOf(BLOCKED_STATUSES),
      zeroTouchRate: completed ? team.zero_touch_count / completed : null,
      slaRate: completed ? team.sla_met_count / completed : null,
    };
  });
  type Row = (typeof rows)[number];
  const accessors = {
    team: (row: Row) => row.team.team_display_name,
    cases: (row: Row) => row.team.count,
    open: (row: Row) => row.open,
    blocked: (row: Row) => row.blocked,
    overdue: (row: Row) => row.team.overdue_count,
    high: (row: Row) => row.team.high_attention_count,
    completed: (row: Row) => row.completed,
    zerotouch: (row: Row) => row.zeroTouchRate,
    sla: (row: Row) => row.slaRate,
    e2e: (row: Row) => row.team.mean_end_to_end_ms,
    fix: (row: Row) => row.team.mean_fix_ms,
  };
  const { sorted, sortKey, sortDir, onSort } = useSortableTable(rows, accessors, "team");
  return (
    <article className="card">
      <h2>Team comparison</h2>
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <SortableTh label="Team" sortKey="team" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Cases" sortKey="cases" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Open" sortKey="open" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Blocked" sortKey="blocked" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Overdue" sortKey="overdue" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="High attention" sortKey="high" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Onboarded" sortKey="completed" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Zero-touch rate" sortKey="zerotouch" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="SLA compliance" sortKey="sla" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Mean end-to-end" sortKey="e2e" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              <SortableTh label="Mean blocker fix" sortKey="fix" activeKey={sortKey} dir={sortDir} onSort={onSort} />
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr key={row.team.team_id}>
                <td><strong>{row.team.team_display_name}</strong><span className="cell-note">{row.team.client_scope_label}</span></td>
                <td>{row.team.count}</td>
                <td>{row.open}</td>
                <td>{row.blocked > 0 ? <span className="tag tag-amber">{row.blocked}</span> : <span className="text-muted">—</span>}</td>
                <td>{row.team.overdue_count > 0 ? <span className="tag tag-critical">{row.team.overdue_count}</span> : <span className="text-muted">—</span>}</td>
                <td>{row.team.high_attention_count > 0 ? <span className="tag tag-critical">{row.team.high_attention_count}</span> : <span className="text-muted">—</span>}</td>
                <td>{row.completed}</td>
                <td>{formatRate(row.zeroTouchRate)}</td>
                <td>{formatRate(row.slaRate)}</td>
                <td>{formatDuration(row.team.mean_end_to_end_ms)}</td>
                <td>{formatDuration(row.team.mean_fix_ms)}{row.team.resolved_blockers > 0 && <span className="cell-note">{row.team.resolved_blockers} resolved</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function WorkloadTable({ rows }: { rows: DashboardSnapshot["workload_by_person"] }) {
  const max = Math.max(1, ...rows.map((row) => row.open_cases));
  const totalOpen = rows.reduce((sum, row) => sum + row.open_cases, 0);
  type Row = DashboardSnapshot["workload_by_person"][number];
  const accessors = {
    person: (row: Row) => row.display_name,
    open: (row: Row) => row.open_cases,
    running: (row: Row) => row.running_cases,
    blocked: (row: Row) => row.blocked_cases,
    overdue: (row: Row) => row.overdue_cases,
    high: (row: Row) => row.high_attention_cases,
    oldest: (row: Row) => row.oldest_open_age_ms,
    completed: (row: Row) => row.completed_cases,
    fixed: (row: Row) => row.blockers_resolved,
    fixtime: (row: Row) => row.mean_fix_time_ms,
  };
  const { sorted, sortKey, sortDir, onSort } = useSortableTable(rows, accessors, "open", "desc");
  const { pageRows, page, setPage, pageCount, total: rowCount, pageSize } = usePagination(sorted);

  return (
    <article className="card">
      <h2>Workload by person</h2>
      {rows.length === 0 && <p className="empty-copy">No cases have been created in this scope yet.</p>}
      {rows.length > 0 && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <SortableTh label="Person" sortKey="person" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Open" sortKey="open" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Running" sortKey="running" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Blocked" sortKey="blocked" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Overdue" sortKey="overdue" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="High attention" sortKey="high" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Oldest open" sortKey="oldest" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Onboarded" sortKey="completed" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Blockers fixed" sortKey="fixed" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Mean fix time" sortKey="fixtime" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <th>Open workload</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row) => (
                <tr key={row.user_id}>
                  <td>{row.display_name}</td>
                  <td>{row.open_cases}</td>
                  <td>{row.running_cases}</td>
                  <td>{row.blocked_cases > 0 ? <span className="tag tag-amber">{row.blocked_cases}</span> : <span className="text-muted">—</span>}</td>
                  <td>{row.overdue_cases > 0 ? <span className="tag tag-critical">{row.overdue_cases}</span> : <span className="text-muted">—</span>}</td>
                  <td>{row.high_attention_cases > 0 ? <span className="tag tag-critical">{row.high_attention_cases}</span> : <span className="text-muted">—</span>}</td>
                  <td>{formatDuration(row.oldest_open_age_ms)}</td>
                  <td>{row.completed_cases}</td>
                  <td>{row.blockers_resolved}</td>
                  <td>{formatDuration(row.mean_fix_time_ms)}</td>
                  <td>
                    <div className="workload-bar" role="img" aria-label={`${row.running_cases} running and ${row.blocked_cases} blocked of ${totalOpen} open`}>
                      <i className="workload-running" style={{ width: `${(row.running_cases / max) * 100}%` }} />
                      <i className="workload-blocked" style={{ width: `${(row.blocked_cases / max) * 100}%` }} />
                    </div>
                    <p className="load-bar-note">{row.open_cases} of {totalOpen} open{totalOpen ? ` (${formatPercent(row.open_cases / totalOpen)})` : ""}</p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rows.length > 0 && <p className="text-muted stack-legend"><span><i className="stack-swatch workload-running" />Running</span><span><i className="stack-swatch workload-blocked" />Blocked</span></p>}
      <Pagination page={page} setPage={setPage} pageCount={pageCount} total={rowCount} pageSize={pageSize} />
    </article>
  );
}

function CaseOpenAction({ caseId }: { caseId: string }) {
  return <Link className="btn open-btn" to={isSampleCaseId(caseId) ? paths.sampleCaseDetail(caseId) : paths.caseDetail(caseId)}>Open</Link>;
}

function CaseSubsetNotice({ loaded, total, mine, id }: { loaded: number; total: number; mine: boolean; id: string }) {
  if (loaded >= total) return null;
  return <p id={id} className="text-muted">
    Loaded subset: {loaded} of {total} {mine ? "creator-only cases" : "cases in the authorized cohort"}.
    {" "}Person, status, age and progress filters apply only to the loaded subset; pagination counts loaded matches.
    {" "}<Link to={paths.cases}>View or search Cases</Link>. Cases uses its own authorized scope and filters.
  </p>;
}

const CASE_SORTS = [
  { value: "attention", label: "Highest attention", dir: "asc" },
  { value: "age", label: "Oldest case", dir: "desc" },
  { value: "deadline", label: "Nearest SLA deadline", dir: "asc" },
  { value: "waiting", label: "Longest waiting", dir: "desc" },
] as const;

function caseAttentionOrder(item: DashboardCaseItem): number {
  // Highest level first, then the oldest case within a level; completed cases last.
  const rank = item.attention_level ? ATTENTION_RANK[item.attention_level] : 3;
  return rank * 1e13 - Math.min(item.case_elapsed_ms, 1e13 - 1);
}

function outstandingIssue(item: DashboardCaseItem): string {
  if (item.open_exception_types.length) return item.open_exception_types.map((type) => BUSINESS_EXCEPTION_TYPE_LABELS[type]).join(", ");
  return item.status === "COMPLETED" ? "—" : item.delay_note ?? "—";
}

function AllCasesTable({ cases, actor, cohortTotal, policy }: { cases: DashboardCaseItem[]; actor: AuthenticatedProfile; cohortTotal: number; policy: DashboardAttentionPolicy }) {
  const subsetId = useId();
  const capped = cases.length < cohortTotal;
  const [personFilter, setPersonFilter] = useState("all");
  const [ageFilter, setAgeFilter] = useState<AgeFilter>("any");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [countryFilter, setCountryFilter] = useState("all");
  const [attentionFilter, setAttentionFilter] = useState<"all" | AttentionLevel>("all");
  const [slaFilter, setSlaFilter] = useState<"all" | SlaStatus>("all");
  const [exceptionFilter, setExceptionFilter] = useState("all");
  const hasFilters = personFilter !== "all" || ageFilter !== "any" || statusFilter !== "all" || countryFilter !== "all"
    || attentionFilter !== "all" || slaFilter !== "all" || exceptionFilter !== "all";

  const people = useMemo(
    () => Array.from(new Set(cases.map((item) => item.created_by_display_name).filter((name): name is string => Boolean(name)))).sort(),
    [cases],
  );
  const countries = useMemo(
    () => Array.from(new Set(cases.map((item) => item.jurisdiction).filter((code): code is JurisdictionCode => code !== null))).sort(),
    [cases],
  );
  const exceptionTypes = useMemo(
    () => Array.from(new Set(cases.flatMap((item) => item.open_exception_types))).sort((a, b) => BUSINESS_EXCEPTION_TYPE_LABELS[a].localeCompare(BUSINESS_EXCEPTION_TYPE_LABELS[b])),
    [cases],
  );

  const filtered = useMemo(() => cases.filter((item) => {
    if (personFilter !== "all" && item.created_by_display_name !== personFilter) return false;
    if (statusFilter === "open" && (item.status === "COMPLETED" || BLOCKED_STATUSES.includes(item.status))) return false;
    if (statusFilter === "blocked" && !BLOCKED_STATUSES.includes(item.status)) return false;
    if (statusFilter === "completed" && item.status !== "COMPLETED") return false;
    if (countryFilter !== "all" && item.jurisdiction !== countryFilter) return false;
    if (attentionFilter !== "all" && item.attention_level !== attentionFilter) return false;
    if (slaFilter !== "all" && item.sla_status !== slaFilter) return false;
    if (exceptionFilter !== "all" && !item.open_exception_types.includes(exceptionFilter as BusinessExceptionType)) return false;
    if (ageFilter !== "any") {
      const days = item.case_elapsed_ms / 86_400_000;
      if (ageFilter === "lt7" && days >= 7) return false;
      if (ageFilter === "7to30" && (days < 7 || days > 30)) return false;
      if (ageFilter === "gt30" && days <= 30) return false;
    }
    return true;
  }), [cases, personFilter, statusFilter, ageFilter, countryFilter, attentionFilter, slaFilter, exceptionFilter]);

  const accessors = {
    case: (item: DashboardCaseItem) => item.legal_name ?? item.requested_uen,
    team: (item: DashboardCaseItem) => item.team_display_name ?? "",
    person: (item: DashboardCaseItem) => item.created_by_display_name ?? "",
    country: (item: DashboardCaseItem) => item.jurisdiction,
    stage: (item: DashboardCaseItem) => STAGE_LABELS[item.current_stage],
    age: (item: DashboardCaseItem) => item.case_elapsed_ms,
    status: (item: DashboardCaseItem) => item.status,
    sla: (item: DashboardCaseItem) => item.sla_status,
    attention: (item: DashboardCaseItem) => caseAttentionOrder(item),
    deadline: (item: DashboardCaseItem) => (item.status === "COMPLETED" || item.sla_due_at === null ? null : Date.parse(item.sla_due_at)),
    waiting: (item: DashboardCaseItem) => item.oldest_open_blocker_age_ms,
    updated: (item: DashboardCaseItem) => item.updated_at,
  };
  const { sorted, sortKey, sortDir, onSort, setSort } = useSortableTable(filtered, accessors, "attention", "asc");
  const { pageRows, page, setPage, pageCount, total: rowCount, pageSize } = usePagination(sorted);
  const preset = CASE_SORTS.find((option) => option.value === sortKey && option.dir === sortDir)?.value ?? "custom";
  const resetPage = <T,>(set: (value: T) => void) => (value: T) => { set(value); setPage(0); };

  return (
    <article className="card" aria-describedby={capped ? subsetId : undefined}>
      <h2>All cases</h2>
      <CaseSubsetNotice id={subsetId} loaded={cases.length} total={cohortTotal} mine={false} />
      <div className="ds-toolbar">
        <SegToggle value={statusFilter} onChange={resetPage(setStatusFilter)} options={STATUS_FILTERS as unknown as Array<{ value: StatusFilter; label: string }>} />
        <label className="filter-label">Person
          <select className="input" value={personFilter} onChange={(event) => resetPage(setPersonFilter)(event.target.value)}>
            <option value="all">All</option>
            {people.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>
        <label className="filter-label">Case age / duration
          <select className="input" value={ageFilter} onChange={(event) => resetPage(setAgeFilter)(event.target.value as AgeFilter)}>
            {AGE_FILTERS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label className="filter-label">Country
          <select className="input" value={countryFilter} onChange={(event) => resetPage(setCountryFilter)(event.target.value)}>
            <option value="all">All</option>
            {countries.map((code) => <option key={code} value={code}>{JURISDICTION_LABELS[code]}</option>)}
          </select>
        </label>
        <label className="filter-label">Attention
          <select className="input" value={attentionFilter} onChange={(event) => resetPage(setAttentionFilter)(event.target.value as "all" | AttentionLevel)}>
            <option value="all">All</option>
            {(["HIGH", "MEDIUM", "LOW"] as const).map((level) => <option key={level} value={level}>{ATTENTION_LABELS[level]}</option>)}
          </select>
        </label>
        <label className="filter-label">SLA
          <select className="input" value={slaFilter} onChange={(event) => resetPage(setSlaFilter)(event.target.value as "all" | SlaStatus)}>
            <option value="all">All</option>
            {(["OVERDUE", "AT_RISK", "ON_TRACK", "MET", "MISSED"] as const).map((status) => <option key={status} value={status}>{SLA_LABELS[status]}</option>)}
          </select>
        </label>
        <label className="filter-label">Open exception
          <select className="input" value={exceptionFilter} onChange={(event) => resetPage(setExceptionFilter)(event.target.value)}>
            <option value="all">All</option>
            {exceptionTypes.map((type) => <option key={type} value={type}>{BUSINESS_EXCEPTION_TYPE_LABELS[type]}</option>)}
          </select>
        </label>
        <label className="filter-label">Sort
          <select className="input" value={preset} onChange={(event) => {
            const option = CASE_SORTS.find((item) => item.value === event.target.value);
            if (option) { setSort(option.value, option.dir); setPage(0); }
          }}>
            {CASE_SORTS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            {preset === "custom" && <option value="custom">Column order</option>}
          </select>
        </label>
        {hasFilters && <button type="button" className="btn btn-ghost" onClick={() => {
          setPersonFilter("all"); setAgeFilter("any"); setStatusFilter("all"); setCountryFilter("all");
          setAttentionFilter("all"); setSlaFilter("all"); setExceptionFilter("all"); setPage(0);
        }}>Clear filters</button>}
      </div>
      {sorted.length === 0 && <p className="empty-copy">{capped ? "No loaded cases match these filters." : "No cases match these filters."}</p>}
      {sorted.length > 0 && (
        <div className="table-scroll">
          <table className="table all-cases-table">
            <thead>
              <tr>
                <SortableTh label="Case" sortKey="case" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                {actor.role === "DIRECTOR" && <SortableTh label="Team" sortKey="team" activeKey={sortKey} dir={sortDir} onSort={onSort} />}
                <SortableTh label="Created by" sortKey="person" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Country" sortKey="country" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Stage" sortKey="stage" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Case age / duration" sortKey="age" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Status" sortKey="status" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="SLA" sortKey="deadline" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Attention" sortKey="attention" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <th scope="col">Outstanding issue</th>
                <SortableTh label="Last updated" sortKey="updated" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((item) => (
                <tr key={item.case_id} className="clickable">
                  <td><strong>{item.legal_name ?? item.requested_uen}</strong><span className="cell-note">{item.requested_uen}{item.delay_note ? ` · ${item.delay_note}` : ""}</span></td>
                  {actor.role === "DIRECTOR" && <td>{item.team_display_name ?? "Unassigned"}</td>}
                  <td>{item.created_by_display_name ?? "—"}</td>
                  <td>{item.jurisdiction ?? "—"}</td>
                  <td>{STAGE_LABELS[item.current_stage]}</td>
                  <td aria-label={`${item.status === "COMPLETED" ? "Case duration" : "Case age"}: ${formatDuration(item.case_elapsed_ms)}`}>{formatDuration(item.case_elapsed_ms)}</td>
                  <td><span className={statusTagClass(item.status)}>{item.status.replaceAll("_", " ")}</span></td>
                  <td><SlaTag status={item.sla_status} /></td>
                  <td><AttentionTag level={item.attention_level} />{item.attention_reasons.length > 0 && <span className="cell-note">{item.attention_reasons.map((reason) => attentionReasonLabel(reason, policy)).join(" · ")}</span>}</td>
                  <td>{outstandingIssue(item)}{item.oldest_open_blocker_age_ms !== null && <span className="cell-note">open {formatDuration(item.oldest_open_blocker_age_ms)}</span>}</td>
                  <td>{formatDateNoSeconds(item.updated_at)}</td>
                  <td style={{ textAlign: "right" }}><CaseOpenAction caseId={item.case_id} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} setPage={setPage} pageCount={pageCount} total={rowCount} pageSize={pageSize} />
    </article>
  );
}

const AGE_FILTERS = [
  { value: "any", label: "Any" },
  { value: "lt7", label: "Under 7 days" },
  { value: "7to30", label: "7–30 days" },
  { value: "gt30", label: "Over 30 days" },
] as const;
type AgeFilter = (typeof AGE_FILTERS)[number]["value"];

const STATUS_FILTERS = [
  { value: "all", label: "All" },
  { value: "open", label: "Running" },
  { value: "blocked", label: "Blocked" },
  { value: "completed", label: "Completed" },
] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number]["value"];

const PROGRESS_FILTERS = [
  { value: "any", label: "Any" },
  { value: "lt50", label: "Under 50%" },
  { value: "50to99", label: "50–99%" },
  { value: "done", label: "100%" },
] as const;
type ProgressFilter = (typeof PROGRESS_FILTERS)[number]["value"];

function YourCasesTable({ cases, cohortTotal }: { cases: DashboardCaseItem[]; cohortTotal: number }) {
  const subsetId = useId();
  const capped = cases.length < cohortTotal;
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [ageFilter, setAgeFilter] = useState<AgeFilter>("any");
  const [progressFilter, setProgressFilter] = useState<ProgressFilter>("any");
  const hasFilters = statusFilter !== "all" || ageFilter !== "any" || progressFilter !== "any";

  const filtered = useMemo(() => {
    return cases.filter((item) => {
      if (statusFilter === "open" && (item.status === "COMPLETED" || BLOCKED_STATUSES.includes(item.status))) return false;
      if (statusFilter === "blocked" && !BLOCKED_STATUSES.includes(item.status)) return false;
      if (statusFilter === "completed" && item.status !== "COMPLETED") return false;
      if (ageFilter !== "any") {
        const days = item.case_elapsed_ms / 86_400_000;
        if (ageFilter === "lt7" && days >= 7) return false;
        if (ageFilter === "7to30" && (days < 7 || days > 30)) return false;
        if (ageFilter === "gt30" && days <= 30) return false;
      }
      if (progressFilter === "lt50" && item.progress_percent >= 50) return false;
      if (progressFilter === "50to99" && (item.progress_percent < 50 || item.progress_percent >= 100)) return false;
      if (progressFilter === "done" && item.progress_percent < 100) return false;
      return true;
    });
  }, [cases, statusFilter, ageFilter, progressFilter]);

  const caseAccessors = {
    case: (item: DashboardCaseItem) => item.legal_name ?? item.requested_uen,
    stage: (item: DashboardCaseItem) => STAGE_LABELS[item.current_stage],
    age: (item: DashboardCaseItem) => item.case_elapsed_ms,
    progress: (item: DashboardCaseItem) => item.progress_percent,
    status: (item: DashboardCaseItem) => item.status,
  };
  const { sorted, sortKey, sortDir, onSort } = useSortableTable(filtered, caseAccessors, "age", "desc");
  const { pageRows, page, setPage, pageCount, total: rowCount, pageSize } = usePagination(sorted);

  return (
    <article className="card" aria-describedby={capped ? subsetId : undefined}>
      <h2>Your cases</h2>
      <CaseSubsetNotice id={subsetId} loaded={cases.length} total={cohortTotal} mine={true} />
      <div className="ds-toolbar">
        <SegToggle value={statusFilter} onChange={(value) => { setStatusFilter(value); setPage(0); }} options={STATUS_FILTERS as unknown as Array<{ value: StatusFilter; label: string }>} />
        <label className="filter-label">Case age / duration
          <select className="input" value={ageFilter} onChange={(event) => { setAgeFilter(event.target.value as AgeFilter); setPage(0); }}>
            {AGE_FILTERS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label className="filter-label">Progress
          <select className="input" value={progressFilter} onChange={(event) => { setProgressFilter(event.target.value as ProgressFilter); setPage(0); }}>
            {PROGRESS_FILTERS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        {hasFilters && <button type="button" className="btn btn-ghost" onClick={() => { setStatusFilter("all"); setAgeFilter("any"); setProgressFilter("any"); setPage(0); }}>Clear filters</button>}
      </div>
      {pageRows.length === 0 && <p className="empty-copy">{capped ? "No loaded cases match these filters." : "No cases match these filters."}</p>}
      {pageRows.length > 0 && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <SortableTh label="Case" sortKey="case" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Stage" sortKey="stage" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Case age / duration" sortKey="age" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Progress" sortKey="progress" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Status" sortKey="status" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <th scope="col">SLA</th>
                <th scope="col">Attention</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((item) => (
                <tr key={item.case_id} className="clickable">
                  <td><strong>{item.legal_name ?? item.requested_uen}</strong><span className="cell-note">{item.requested_uen}</span></td>
                  <td>{STAGE_LABELS[item.current_stage]}</td>
                  <td aria-label={`${item.status === "COMPLETED" ? "Case duration" : "Case age"}: ${formatDuration(item.case_elapsed_ms)}`}>{formatDuration(item.case_elapsed_ms)}</td>
                  <td>{item.progress_percent}%</td>
                  <td><span className={statusTagClass(item.status)}>{item.status.replaceAll("_", " ")}</span></td>
                  <td><SlaTag status={item.sla_status} /></td>
                  <td><AttentionTag level={item.attention_level} /></td>
                  <td style={{ textAlign: "right" }}><CaseOpenAction caseId={item.case_id} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} setPage={setPage} pageCount={pageCount} total={rowCount} pageSize={pageSize} />
    </article>
  );
}

function BlockedCases({ cases, cohortTotal }: { cases: DashboardCaseItem[]; cohortTotal: number }) {
  const subsetId = useId();
  const capped = cases.length < cohortTotal;
  const blocked = cases.filter((item) => BLOCKED_STATUSES.includes(item.status));
  const { pageRows, page, setPage, pageCount, total, pageSize } = usePagination(blocked);
  return (
    <article className="card" aria-describedby={capped ? subsetId : undefined}>
      <h2>Blocked cases</h2>
      <CaseSubsetNotice id={subsetId} loaded={cases.length} total={cohortTotal} mine={true} />
      {blocked.length === 0 && <p className="empty-copy">{capped ? "No blocked cases in the loaded subset." : "None of your cases are currently blocked."}</p>}
      <div className="blocked-case-list">
        {pageRows.map((item) => (
          <div className="blocked-case-row" key={item.case_id}>
            <div><div>{item.legal_name ?? item.requested_uen}</div><p className="cell-note">{item.delay_note ?? "Returned for review"}</p></div>
            <Link className="btn btn-secondary" to={isSampleCaseId(item.case_id) ? paths.sampleCaseDetail(item.case_id) : paths.caseDetail(item.case_id)}>Review</Link>
          </div>
        ))}
      </div>
      <Pagination page={page} setPage={setPage} pageCount={pageCount} total={total} pageSize={pageSize} />
    </article>
  );
}

function countDelta(current: number, previous: number): string {
  const diff = current - previous;
  return diff === 0 ? "No change" : `${diff > 0 ? "+" : "−"}${Math.abs(diff)}`;
}

function rateDelta(current: number | null, previous: number | null): string | null {
  if (current === null || previous === null) return null;
  const points = Math.round((current - previous) * 100);
  return points === 0 ? "No change" : `${points > 0 ? "+" : "−"}${Math.abs(points)} pts`;
}

function durationDelta(current: number | null, previous: number | null): string | null {
  if (current === null || previous === null) return null;
  const diff = Math.round(current - previous);
  if (diff === 0) return "No change";
  return `${formatDuration(Math.abs(diff))} ${diff > 0 ? "longer" : "shorter"}`;
}

function Kpi({ label, value, sub, delta, tone }: {
  label: string;
  value: string | number;
  sub?: string;
  delta?: string | null;
  tone?: "critical" | "warning";
}) {
  return (
    <article className={`dashboard-kpi${tone ? ` dashboard-kpi--${tone}` : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {sub && <p className="text-muted">{sub}</p>}
      {delta && <p className="kpi-delta">{delta}</p>}
    </article>
  );
}

function shortDate(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString("en-SG", { day: "numeric", month: "short", timeZone: "UTC" });
}

function ManagementOverview({ dashboard, dateRange }: { dashboard: DashboardSnapshot; dateRange: DashboardDateRange }) {
  const kpis = dashboard.kpis;
  const policy = dashboard.attention_policy;
  const previous = dashboard.previous_period;
  const comparable = previous !== null && previous.completed_cases > 0;
  const vs = previous ? ` vs ${shortDate(previous.created_from)}–${shortDate(previous.created_to)}` : "";
  const delta = (text: string | null) => (comparable && text ? `${text}${vs}` : null);
  const target = formatDays(policy.sla_target_ms);
  return (
    <section aria-label="Management overview">
      <div className="dashboard-kpis dashboard-kpis--4" aria-label="Dashboard totals">
        <Kpi label="Open cases" value={kpis.open_cases} sub={`${kpis.running_cases} running · ${kpis.blocked_cases} blocked · ${kpis.awaiting_review_cases} awaiting review`} />
        <Kpi label="Onboarded" value={kpis.completed_cases} delta={previous && comparable ? `${countDelta(kpis.completed_cases, previous.completed_cases)}${vs}` : null} />
        <Kpi label="Zero-touch rate" value={formatRate(kpis.zero_touch_rate)} sub="Completed cases with no recorded exception interventions; final review still required." delta={delta(rateDelta(kpis.zero_touch_rate, previous?.zero_touch_rate ?? null))} />
        <Kpi label="Mean processing time" value={formatDuration(kpis.mean_processing_ms)} sub={`Recorded step processing of completed cases, excluding waiting. Recorded run time (workflow start to completion): ${formatDuration(dashboard.timing.mean_total_duration_ms)}.`} delta={delta(durationDelta(kpis.mean_processing_ms, previous?.mean_processing_ms ?? null))} />
      </div>
      <div className="dashboard-kpis dashboard-kpis--4" aria-label="SLA and attention totals">
        <Kpi label="SLA compliance" value={formatRate(kpis.sla_compliance_rate)} sub={`${kpis.sla_met_cases} of ${kpis.completed_cases} completed within the ${target} target`} delta={delta(rateDelta(kpis.sla_compliance_rate, previous?.sla_compliance_rate ?? null))} />
        <Kpi label="Overdue cases" value={kpis.overdue_cases} tone={kpis.overdue_cases > 0 ? "critical" : undefined} sub={`Open past the ${target} target · ${kpis.high_attention_cases} open cases need high attention`} />
        <Kpi label="At-risk cases" value={kpis.at_risk_cases} tone={kpis.at_risk_cases > 0 ? "warning" : undefined} sub={`Open and within ${formatDays(policy.at_risk_window_ms)} of the target`} />
        <Kpi label="Mean end-to-end time" value={formatDuration(kpis.mean_end_to_end_ms)} sub={`Case creation to onboarded, including waiting · target ${target}`} delta={delta(durationDelta(kpis.mean_end_to_end_ms, previous?.mean_end_to_end_ms ?? null))} />
      </div>
      <p className="text-muted dashboard-footnote">
        SLA and attention use provisional project rules ({policy.decision}): a {target} target from case creation, at risk within {formatDays(policy.at_risk_window_ms)} of it. They are display aids, not a sponsor SLA or a compliance measure.
        {" "}{dateRange === "all" ? "Choose a bounded date range to compare with the previous period." : comparable ? "" : "No earlier completions are available to compare with."}
      </p>
    </section>
  );
}

function funnelBlockerNote(blocked: number, stillOpen: number): string {
  const movedOn = blocked - stillOpen;
  const parts = [movedOn > 0 ? `${movedOn} moved on` : "", stillOpen > 0 ? `${stillOpen} still waiting` : ""].filter(Boolean);
  return `${blocked} hit a blocker: ${parts.join(", ")}`;
}

function OnboardingFunnel({ dashboard }: { dashboard: DashboardSnapshot }) {
  const rows: Array<{ key: string; label: string; count: number; blocked: number; stillOpen: number }> = [
    { key: "received", label: "Cases received", count: dashboard.totals.total_cases, blocked: 0, stillOpen: 0 },
    ...dashboard.stage_timing.map((row) => ({ key: row.stage, label: STAGE_LABELS[row.stage], count: row.reached_count, blocked: row.blocked_count, stillOpen: row.open_blocked_count })),
    { key: "onboarded", label: "Onboarded", count: dashboard.totals.completed_cases, blocked: 0, stillOpen: 0 },
  ];
  const top = Math.max(1, rows[0].count);
  return (
    <article className="card">
      <h2>Onboarding funnel</h2>
      <div className="funnel">
        {rows.map((row, index) => {
          const previous = index > 0 ? rows[index - 1].count : null;
          return (
            <div className="funnel-row" key={row.key}>
              <span className="funnel-label">{row.label}</span>
              <div className="funnel-track"><i style={{ width: `${(row.count / top) * 100}%` }} /></div>
              <strong>{row.count}</strong>
              <span className="funnel-note">
                {previous ? `${formatPercent(row.count / previous)} of previous step` : index === 0 ? "" : "—"}
                {row.blocked > 0 && <span className="funnel-blockers">{funnelBlockerNote(row.blocked, row.stillOpen)}</span>}
              </span>
            </div>
          );
        })}
      </div>
    </article>
  );
}

// Candidate gridline spacings, smallest first; the chart uses the first giving at most 5 lines.
const TREND_STEPS_MS = [60_000, 5 * 60_000, 15 * 60_000, 30 * 60_000, 3_600_000, 2 * 3_600_000, 4 * 3_600_000, 6 * 3_600_000, 12 * 3_600_000, DAY_MS, 2 * DAY_MS, 5 * DAY_MS, 10 * DAY_MS, 30 * DAY_MS];

function weekCompletions(week: DashboardSnapshot["weekly_onboarded"][number]): number {
  return Object.values(week.by_jurisdiction).reduce((sum, count) => sum + (count ?? 0), 0) + week.unresolved_count;
}

function TurnaroundTrend({ weeks, targetMs }: { weeks: DashboardSnapshot["weekly_onboarded"]; targetMs: number }) {
  const values = weeks.map((week) => week.mean_end_to_end_ms);
  const known = values.filter((value): value is number => value !== null);
  const slowest = known.length ? Math.max(...known) : 0;
  const overTarget = known.filter((value) => value > targetMs).length;
  // Draw the target only when a week comes within half of it; otherwise it would flatten the line.
  const showTarget = slowest >= targetMs / 2;
  const top = showTarget ? Math.max(slowest, targetMs) : slowest;
  const step = TREND_STEPS_MS.find((candidate) => top / candidate <= 5) ?? TREND_STEPS_MS[TREND_STEPS_MS.length - 1];
  const max = Math.max(step, Math.ceil((top * 1.08) / step) * step);
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, index) => index * step);
  const width = 340;
  const left = 34;
  const right = 12;
  const plotTop = 16;
  const plot = 120;
  // Inset the first and last weeks so their value labels clear the axis labels.
  const inset = 18;
  const x = (index: number) => left + inset + (index * (width - left - right - 2 * inset)) / Math.max(1, weeks.length - 1);
  const y = (value: number) => plotTop + plot - (value / max) * plot;
  const segments: string[] = [];
  let current = "";
  values.forEach((value, index) => {
    if (value === null) { if (current) segments.push(current); current = ""; return; }
    current += `${current ? " L" : "M"} ${x(index).toFixed(1)} ${y(value).toFixed(1)}`;
  });
  if (current) segments.push(current);
  const target = formatDays(targetMs);
  return (
    <article className="card">
      <h2>Turnaround trend</h2>
      {known.length > 0 && (overTarget > 0
        ? <span className="tag tag-critical trend-target-note">{overTarget} week{overTarget === 1 ? "" : "s"} above the {target} target</span>
        : <span className="tag tag-ok trend-target-note">Target {target} · every week is within it (slowest week {formatDuration(slowest)}, {formatPercent(slowest / targetMs)} of target)</span>)}
      {known.length === 0 ? <p className="empty-copy">No completions in these weeks, so no turnaround can be shown.</p> : (
        <svg className="trend-chart" viewBox={`0 0 ${width} ${plotTop + plot + 34}`} role="img" aria-label="Mean end-to-end onboarding time per week">
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className="trend-grid" />
              <text x={left - 5} y={y(tick) + 2.5} textAnchor="end" className="trend-axis">{tick === 0 ? "0" : formatDuration(tick)}</text>
            </g>
          ))}
          {showTarget && <line x1={left} x2={width - right} y1={y(targetMs)} y2={y(targetMs)} className="trend-target" />}
          {segments.map((d) => <path key={d} d={d} className="trend-line" />)}
          {values.map((value, index) => {
            const week = weeks[index];
            const isSlowest = value !== null && value === slowest;
            return (
              <g key={week.week_start}>
                {value !== null && <>
                  <circle cx={x(index)} cy={y(value)} r={isSlowest ? 3.6 : 3} className={isSlowest ? "trend-point trend-point--slowest" : "trend-point"}><title>{`${week.week_start}: ${formatDuration(value)} over ${weekCompletions(week)} cases`}</title></circle>
                  <text x={x(index)} y={y(value) - 7} textAnchor="middle" className={isSlowest ? "trend-value trend-value--slowest" : "trend-value"}>{formatDuration(value)}</text>
                </>}
                <text x={x(index)} y={plotTop + plot + 14} textAnchor="middle" className="trend-axis">{week.week_start.slice(5)}</text>
                <text x={x(index)} y={plotTop + plot + 25} textAnchor="middle" className="trend-cases">{weekCompletions(week)} {weekCompletions(week) === 1 ? "case" : "cases"}</text>
              </g>
            );
          })}
        </svg>
      )}
      {known.length > 0 && <p className="text-muted stp-note"><span className="trend-slowest-key" /> slowest week{showTarget ? ` · dashed line: ${target} target` : ""}</p>}
    </article>
  );
}

function ProcessingVsWaiting({ stageTiming }: { stageTiming: DashboardStageTiming[] }) {
  const rows = stageTiming.map((row) => ({
    stage: row.stage,
    reached: row.reached_count,
    processing: row.reached_count ? Math.round(row.processing_total_ms / row.reached_count) : 0,
    waiting: row.reached_count ? Math.round(row.resolution_total_ms / row.reached_count) : 0,
  }));
  const max = Math.max(1, ...rows.map((row) => row.processing + row.waiting));
  return (
    <article className="card">
      <h2>Processing vs waiting</h2>
      <div className="stack-legend"><span><i className="stack-swatch stack-processing" />Processing</span><span><i className="stack-swatch stack-waiting" />Waiting on a person</span></div>
      <div className="stack-bars">
        {rows.map((row) => (
          <div className="stack-row" key={row.stage}>
            <span>{STAGE_LABELS[row.stage]}</span>
            <div className="stack-track">
              <i className="stack-processing" style={{ width: `${(row.processing / max) * 100}%` }} />
              <i className="stack-waiting" style={{ width: `${(row.waiting / max) * 100}%` }} />
            </div>
            <strong>{row.reached ? `${formatDuration(row.processing)} · ${row.waiting ? formatDuration(row.waiting) : "0s"}` : "—"}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}

function ReworkCard({ rework }: { rework: DashboardSnapshot["rework"] }) {
  return (
    <article className="card">
      <h2>Rework</h2>
      <div className="rework-figures rework-figures--stacked">
        <div><strong>{rework.total_cases ? formatPercent(rework.rework_cases / rework.total_cases) : "—"}</strong><span>of cases needed rework</span></div>
        <div><strong>{rework.rework_cases}</strong><span>rework cases</span></div>
        <div><strong>{rework.cases_with_blockers}</strong><span>cases stopped at least once</span></div>
      </div>
    </article>
  );
}

const ACTION_LIST_LIMIT = 5;

// Re-exported: the rule now lives with the AI insights findings, which also use it.
export { proposalsAwaitingDecision };

function DirectorActions({ dashboard, actor, refreshToken }: { dashboard: DashboardSnapshot; actor: AuthenticatedProfile; refreshToken: number }) {
  const canApprove = actor.capabilities.includes("POLICY_APPROVE");
  const policies = useQuery({ ...policyCatalogueQueryOptions(actor.user_id), enabled: canApprove, refetchOnMount: "always" });
  const refetchPolicies = policies.refetch;
  useEffect(() => {
    if (refreshToken > 0 && canApprove) void refetchPolicies();
  }, [refreshToken, canApprove, refetchPolicies]);
  const recoveryTotal = dashboard.status_breakdown.find((item) => item.status === "RECOVERY_PENDING")?.count ?? 0;
  const recovery = dashboard.scoped_cases
    .filter((item) => item.status === "RECOVERY_PENDING")
    .sort((a, b) => b.case_elapsed_ms - a.case_elapsed_ms);
  const awaiting = policies.data ? proposalsAwaitingDecision(policies.data, actor) : [];
  return (
    <article className="card director-actions" aria-label="Needs your action">
      <h2>Needs your action</h2>
      <p className="text-muted">Work only a Director can move forward.</p>
      <div className="director-actions-grid">
        <section>
          <h3 className="h2a">GoldTier recovery · {recoveryTotal} {recoveryTotal === 1 ? "case" : "cases"}</h3>
          <p className="text-muted director-actions-note">Cases waiting for a recovery decision, in the selected date range.</p>
          {recovery.length === 0 && <p className="empty-copy">No case is waiting for GoldTier recovery.</p>}
          <div className="blocked-case-list">
            {recovery.slice(0, ACTION_LIST_LIMIT).map((item) => (
              <div className="blocked-case-row" key={item.case_id}>
                <div>
                  <div>{item.legal_name ?? item.requested_uen}</div>
                  <p className="cell-note">{item.team_display_name ?? "Unassigned"} · {item.created_by_display_name ?? "—"} · case age {formatDuration(item.case_elapsed_ms)}{item.sla_status === "OVERDUE" ? " · overdue" : ""}</p>
                </div>
                <CaseOpenAction caseId={item.case_id} />
              </div>
            ))}
          </div>
          {recovery.length > ACTION_LIST_LIMIT && <p className="text-muted director-actions-note">Showing the {ACTION_LIST_LIMIT} oldest. Filter All cases by status to see the rest.</p>}
        </section>
        <section>
          <h3 className="h2a">Policy changes awaiting your decision{policies.data ? ` · ${awaiting.length}` : ""}</h3>
          <p className="text-muted director-actions-note">Submitted proposals from others, based on the active policy version.</p>
          {!canApprove && <p className="empty-copy">Your role does not approve policy changes.</p>}
          {canApprove && policies.isPending && <p className="text-muted">Loading policy changes…</p>}
          {canApprove && policies.isError && <p role="alert" className="text-muted">Policy changes are unavailable right now. The rest of the dashboard is not affected.</p>}
          {canApprove && policies.data && awaiting.length === 0 && <p className="empty-copy">No policy change is waiting for you.</p>}
          <div className="blocked-case-list">
            {awaiting.slice(0, ACTION_LIST_LIMIT).map((proposal) => (
              <div className="blocked-case-row" key={proposal.proposal_id}>
                <div>
                  <div>Proposal version {proposal.version}</div>
                  <p className="cell-note">Proposed by {proposal.proposer_id} · updated {formatDateNoSeconds(proposal.updated_at)}</p>
                </div>
                <Link className="btn btn-secondary" to={paths.policy}>Review</Link>
              </div>
            ))}
          </div>
        </section>
      </div>
    </article>
  );
}

function TeamDashboard({ dashboard, actor, includesSample, dateRange, teamFilter, refreshToken }: { dashboard: DashboardSnapshot; actor: AuthenticatedProfile; includesSample: boolean; dateRange: DashboardDateRange; teamFilter: string; refreshToken: number }) {
  const totals = dashboard.totals;

  return (
    <>
      <ManagementOverview dashboard={dashboard} dateRange={dateRange} />

      <AiInsights dashboard={dashboard} actor={actor} dateRange={dateRange} teamFilter={teamFilter} stageLabels={STAGE_LABELS} />

      {actor.role === "DIRECTOR" && <DirectorActions dashboard={dashboard} actor={actor} refreshToken={refreshToken} />}

      {totals.total_cases === 0 && <div className="ds-banner">No onboarding cases are available for your current scope.</div>}

      <div className="section-divider"><span className="h2a">Onboarding performance</span><span className="section-divider-rule" /></div>
      {/* Paired by height: two weekly charts, then two step-by-step lists. */}
      <div className="dashboard-grid dashboard-grid--halves dashboard-grid--matched">
        <WeeklyOnboardedChart weeks={dashboard.weekly_onboarded} includesSample={includesSample} />
        <TurnaroundTrend weeks={dashboard.weekly_onboarded} targetMs={dashboard.attention_policy.sla_target_ms} />
      </div>
      <div className="dashboard-grid dashboard-grid--halves dashboard-grid--matched">
        <OnboardingFunnel dashboard={dashboard} />
        <StraightThroughPanel weeks={dashboard.weekly_onboarded} stageTiming={dashboard.stage_timing} />
      </div>

      <div className="section-divider"><span className="h2a">Process efficiency</span><span className="section-divider-rule" /></div>
      <StageTimingTable stageTiming={dashboard.stage_timing} />
      <div className="dashboard-grid dashboard-grid--two-one dashboard-grid--matched">
        <ProcessingVsWaiting stageTiming={dashboard.stage_timing} />
        <ReworkCard rework={dashboard.rework} />
      </div>
      <ExceptionBreakdown exceptions={dashboard.exception_breakdown} />

      {actor.role === "DIRECTOR" && dashboard.team_breakdown.length > 0 && <>
        <div className="section-divider"><span className="h2a">Teams</span><span className="section-divider-rule" /></div>
        <TeamComparison teams={dashboard.team_breakdown} />
      </>}

      <div className="section-divider"><span className="h2a">Workload</span><span className="section-divider-rule" /></div>
      <WorkloadTable rows={dashboard.workload_by_person} />
      <div className="section-divider"><span className="h2a">Cases</span><span className="section-divider-rule" /></div>
      <AllCasesTable cases={dashboard.scoped_cases} actor={actor} cohortTotal={totals.total_cases} policy={dashboard.attention_policy} />
    </>
  );
}

function RecentActivity({ actor, teamFilter }: { actor: AuthenticatedProfile; teamFilter: string }) {
  const limit = 10;
  const [offset, setOffset] = useState(0);
  const [refreshFromFirst, setRefreshFromFirst] = useState(false);
  const query = useQuery({
    ...activityQueryOptions(actor.user_id, { createdBy: actor.user_id, teamFilter, offset, limit }, actor),
    refetchOnMount: "always",
  });
  const refetch = query.refetch;
  useEffect(() => {
    if (refreshFromFirst && offset === 0) {
      setRefreshFromFirst(false);
      void refetch({ cancelRefetch: false });
    }
  }, [offset, refreshFromFirst, refetch]);
  const items = query.data?.items ?? [];
  const capReached = Boolean(query.data?.has_more && offset + limit > 10_000);
  return (
    <article className="card">
      <div className="row-between">
        <h2>Recent activity on your cases · all dates</h2>
        <Link className="btn btn-ghost" to={paths.audit}>Audit →</Link>
      </div>
      {query.isPending && <p className="text-muted">Loading activity…</p>}
      {query.isFetching && query.data && <p className="text-muted">Refreshing activity…</p>}
      {query.isError && <p role="alert">Activity is unavailable. {query.data ? "The last result for this page remains visible." : "Try again."}</p>}
      {query.isSuccess && items.length === 0 && <p className="empty-copy">No recorded activity on this page.</p>}
      <div className="activity-list">
        {items.map((item) => (
          <div className="activity-row" key={`${item.case_id}-${item.sequence}`}>
            <div>{item.message}</div>
            <p className="cell-note">{item.current_client_scope_label ?? "—"} · {formatTimestamp(item.timestamp)}</p>
          </div>
        ))}
      </div>
      <div className="pagination" aria-label="Recent activity pages">
        {query.data && <span className="text-muted">{items.length ? `${offset + 1}–${offset + items.length} events` : "0 events on this page"}</span>}
        <button type="button" disabled={offset === 0 || query.isFetching} onClick={() => setOffset(offset - limit)}>‹ Prev</button>
        <button type="button" disabled={query.isFetching || query.isError || !query.data?.has_more || capReached} onClick={() => setOffset(offset + limit)}>Next ›</button>
        <button type="button" disabled={query.isFetching} onClick={() => {
          if (offset === 0) void refetch();
          else { setRefreshFromFirst(true); setOffset(0); }
        }}>Refresh activity</button>
        {query.isError && <button type="button" disabled={query.isFetching} onClick={() => void refetch()}>Retry activity page</button>}
      </div>
      {capReached && <p className="text-muted">More history is available. Open Audit to narrow the filters.</p>}
      <p className="cell-note">Pages are a live view; new events or deletion can move page boundaries.</p>
    </article>
  );
}

function MyWorkDashboard({ dashboard, actor, teamFilter, activityRefresh }: { dashboard: DashboardSnapshot; actor: AuthenticatedProfile; teamFilter: string; activityRefresh: number }) {
  const totals = dashboard.totals;
  const mine = dashboard.workload_by_person.find((row) => row.user_id === actor.user_id);

  return (
    <>
      <div className="dashboard-kpis dashboard-kpis--4" aria-label="Your dashboard totals">
        <article className="dashboard-kpi"><span>Your open cases</span><strong>{totals.non_completed_cases}</strong></article>
        <article className="dashboard-kpi"><span>Your created cases onboarded</span><strong>{totals.completed_cases}</strong></article>
        <article className="dashboard-kpi"><span>Time to resolve a blocker</span><strong>{formatDuration(mine?.mean_fix_time_ms)}</strong><p className="text-muted">mean · {mine?.blockers_resolved ?? 0} blockers resolved</p></article>
        <article className="dashboard-kpi"><span>Recorded run time</span><strong>{formatDuration(dashboard.timing.mean_total_duration_ms)}</strong><p className="text-muted">mean · recorded workflow start to completion</p></article>
      </div>

      {totals.total_cases === 0 && <div className="ds-banner">You have not created any onboarding cases in this scope yet.</div>}

      <YourCasesTable cases={dashboard.scoped_cases} cohortTotal={totals.total_cases} />
      <div className="dashboard-grid dashboard-grid--distributions">
        <BlockedCases cases={dashboard.scoped_cases} cohortTotal={totals.total_cases} />
        <RecentActivity key={`${actor.user_id}:${actor.role}:${actor.team_id}:${teamFilter}:${activityRefresh}`} actor={actor} teamFilter={actor.role === "DIRECTOR" ? teamFilter : "all"} />
      </div>
    </>
  );
}

const DATE_RANGE_OPTIONS: Array<{ value: DashboardDateRange; label: string }> = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
  { value: "all", label: "All time" },
];

export function DashboardView({
  actor,
  dashboard,
  dashScope,
  onScopeChange,
  dateRange,
  onDateRangeChange,
  teamFilter,
  onTeamFilterChange,
  onRefresh,
  onBack,
  sampleCases = 0,
}: {
  actor: AuthenticatedProfile;
  dashboard: DashboardSnapshot;
  dashScope: "team" | "mine";
  onScopeChange: (value: "team" | "mine") => void;
  dateRange: DashboardDateRange;
  onDateRangeChange: (value: DashboardDateRange) => void;
  teamFilter: string;
  onTeamFilterChange: (value: string) => void;
  onRefresh: () => void;
  onBack: () => void;
  /** Number of fixed sample cases included in `dashboard`; 0 when it is live data only. */
  sampleCases?: number;
}) {
  const [activityRefresh, setActivityRefresh] = useState(0);
  return (
    <section className="ds-root ds-page dashboard-page">
      <header className="ds-page-header dashboard-header">
        <div><button className="btn btn-ghost dashboard-back" type="button" onClick={onBack}>← All categories</button><h1>Onboarding Dashboard</h1></div>
        <div className="dashboard-meta-row">
          <div className="dashboard-filters">
            <SegToggle value={dashScope} onChange={onScopeChange} options={[{ value: "team", label: "Manager" }, { value: "mine", label: "My work" }]} />
            <DirectorTeamFilter actor={actor} value={teamFilter} onChange={onTeamFilterChange} />
            <select aria-label="Dashboard date range" className="input dashboard-date-range" value={dateRange} onChange={(event) => onDateRangeChange(event.target.value as DashboardDateRange)}>
              {DATE_RANGE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
          <div className="dashboard-as-of">
            <span>Data as of</span><strong>{formatDateNoSeconds(dashboard.data_as_of)}</strong>
            <button className="btn btn-ghost" type="button" onClick={() => { setActivityRefresh(value => value + 1); onRefresh(); }}>Refresh</button>
          </div>
        </div>
      </header>

      {dashScope === "team" ? <TeamDashboard dashboard={dashboard} actor={actor} includesSample={sampleCases > 0} dateRange={dateRange} teamFilter={teamFilter} refreshToken={activityRefresh} /> : <MyWorkDashboard activityRefresh={activityRefresh} dashboard={dashboard} actor={actor} teamFilter={teamFilter} />}
    </section>
  );
}

export default function Dashboard({
  actor,
}: {
  actor: AuthenticatedProfile;
}) {
  const [teamFilter, setTeamFilter] = useState("all");
  const [view, setView] = useState<"picker" | "onboarding">("picker");
  const [dashScope, setDashScope] = useState<"team" | "mine">("team");
  const [dateRange, setDateRange] = useState<DashboardDateRange>("30d");
  const query = useQuery(dashboardQueryOptions(actor.user_id, teamFilter, dashScope, dateRange));
  const live = query.data;
  // Fixed sample cases are added on top of the live snapshot for display only; the query cache
  // keeps the backend response unchanged.
  const dashboard = useMemo(() => (live ? withOnboardingSample(live, actor) : undefined), [live, actor]);
  const sampleCases = live ? sampleCaseCount(live.view, actor) : 0;

  const feedback = <>
    {(query.isPending || query.isFetching) && <p className="refreshing-indicator" role="status">{dashboard ? "Refreshing dashboard…" : "Loading dashboard…"}</p>}
    {query.isError && <>
      <div className="ds-banner ds-banner-warn" role="alert">{dashboard ? "Refresh failed; the last dashboard snapshot remains visible." : "Dashboard data is unavailable. Please try again."}</div>
      <button className="btn btn-secondary" type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>Try again</button>
    </>}
  </>;

  if (view === "picker") return <>{feedback}<DashboardCategoryPicker dashboard={dashboard} unavailable={query.isError && !dashboard} onSelectOnboarding={() => setView("onboarding")} /></>;

  if (!dashboard) return <section className="ds-root ds-page">
    <button className="btn btn-ghost dashboard-back" type="button" onClick={() => setView("picker")}>← All categories</button>
    <h1>Onboarding Dashboard</h1>
    <DirectorTeamFilter actor={actor} value={teamFilter} onChange={setTeamFilter} />
    {feedback}
  </section>;

  return <>{feedback}<DashboardView actor={actor} dashboard={dashboard} dashScope={dashScope} onScopeChange={setDashScope} dateRange={dateRange} onDateRangeChange={setDateRange} teamFilter={teamFilter} onTeamFilterChange={setTeamFilter} onRefresh={() => void query.refetch()} onBack={() => setView("picker")} sampleCases={sampleCases} /></>;
}
