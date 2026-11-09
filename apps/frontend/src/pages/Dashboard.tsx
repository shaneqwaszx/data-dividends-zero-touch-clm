import { Fragment, useEffect, useId, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import DirectorTeamFilter from "./DirectorTeamFilter";
import { MockCategoryCards } from "./mockDashboards/MockDashboards";
import { isSampleCaseId, sampleCaseCount, withOnboardingSample } from "./mockDashboards/onboardingSample";
import type { DashboardDateRange } from "../api";
import { activityQueryOptions, dashboardQueryOptions } from "../caseQueries";
import { paths } from "../navigation";
import { formatDateNoSeconds, formatDuration as formatRecordedDuration, formatTimestamp } from "../shared";
import type {
  AuthenticatedProfile,
  AutomationStage,
  AutomationStatus,
  BusinessExceptionType,
  DashboardCaseItem,
  DashboardSnapshot,
  DashboardStageTiming,
  JurisdictionCode,
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
  return { sorted, sortKey, sortDir, onSort };
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
  };
  const { sorted, sortKey, sortDir, onSort } = useSortableTable(indexed, accessors, "order");

  return (
    <article className="card">
      <h2>Time per pipeline step</h2>
      <p className="text-muted">Clean and With blocker group recorded processing-duration samples by retained blocker history. Waiting and blocker-resolution time are not included. Combined averages the available recorded samples.</p>
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
                </tr>

                  <tr className="step-detail" hidden={open !== row.stage}>
                    <td colSpan={6}><div id={`${detailPrefix}-${row.stage}-detail`} role="region" aria-labelledby={`${detailPrefix}-${row.stage}-toggle`}>
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

function WeeklyOnboardedChart({ weeks, includesSample }: { weeks: DashboardSnapshot["weekly_onboarded"]; includesSample: boolean }) {
  const totals = weeks.map((week) => Object.values(week.by_jurisdiction).reduce((sum, count) => sum + (count ?? 0), 0) + week.unresolved_count);
  const max = Math.max(1, ...totals);
  const jurisdictionsPresent = Array.from(
    new Set(weeks.flatMap((week) => Object.keys(week.by_jurisdiction) as JurisdictionCode[])),
  );
  const anyUnresolved = weeks.some((week) => week.unresolved_count > 0);

  return (
    <article className="card" style={{ flex: 1.25 }}>
      <div className="row-between">
        <h2>Onboarded per week</h2>
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
              {(Object.entries(week.by_jurisdiction) as Array<[JurisdictionCode, number]>).map(([code, count]) => (
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

function ExceptionBreakdown({ exceptions }: { exceptions: Array<{ exception_type: BusinessExceptionType; count: number }> }) {
  const max = Math.max(1, ...exceptions.map((item) => item.count));
  const total = exceptions.reduce((sum, item) => sum + item.count, 0);
  const { pageRows, page, setPage, pageCount, total: rowCount, pageSize } = usePagination(exceptions);
  return (
    <article className="card" style={{ flex: 1 }}>
      <h2>Why cases stopped · {total} exceptions</h2>
      {exceptions.length === 0 && <p className="empty-copy">No blockers were raised for your current scope.</p>}
      <div className="dashboard-bars">
        {pageRows.map((item) => (
          <div className="dashboard-bar" key={item.exception_type}>
            <span>{BUSINESS_EXCEPTION_TYPE_LABELS[item.exception_type]}</span>
            <div><i style={{ width: `${(item.count / max) * 100}%` }} /></div>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
      <Pagination page={page} setPage={setPage} pageCount={pageCount} total={rowCount} pageSize={pageSize} />
    </article>
  );
}

function WorkloadTable({ rows }: { rows: DashboardSnapshot["workload_by_person"] }) {
  const max = Math.max(1, ...rows.map((row) => row.open_cases));
  const totalOpen = rows.reduce((sum, row) => sum + row.open_cases, 0);
  const accessors = {
    person: (row: DashboardSnapshot["workload_by_person"][number]) => row.display_name,
    open: (row: DashboardSnapshot["workload_by_person"][number]) => row.open_cases,
    oldest: (row: DashboardSnapshot["workload_by_person"][number]) => row.oldest_open_age_ms,
    completed: (row: DashboardSnapshot["workload_by_person"][number]) => row.completed_cases,
    fixed: (row: DashboardSnapshot["workload_by_person"][number]) => row.blockers_resolved,
    fixtime: (row: DashboardSnapshot["workload_by_person"][number]) => row.mean_fix_time_ms,
  };
  const { sorted, sortKey, sortDir, onSort } = useSortableTable(rows, accessors, "open", "desc");
  const { pageRows, page, setPage, pageCount, total: rowCount, pageSize } = usePagination(sorted);

  return (
    <article className="card">
      <h2>Workload by person</h2><p className="text-muted">Case counts use the creator; blocker fixes use the recorded resolver within the selected case scope.</p>
      {rows.length === 0 && <p className="empty-copy">No cases have been created in this scope yet.</p>}
      {rows.length > 0 && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <SortableTh label="Person" sortKey="person" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Open cases" sortKey="open" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Oldest open" sortKey="oldest" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Onboarded" sortKey="completed" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Blockers fixed" sortKey="fixed" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Mean fix time" sortKey="fixtime" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <th>Load</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row) => (
                <tr key={row.user_id}>
                  <td>{row.display_name}</td>
                  <td>{row.open_cases}</td>
                  <td>{formatDuration(row.oldest_open_age_ms)}</td>
                  <td>{row.completed_cases}</td>
                  <td>{row.blockers_resolved}</td>
                  <td>{formatDuration(row.mean_fix_time_ms)}</td>
                  <td>
                    <div className="load-bar"><div style={{ width: `${(row.open_cases / max) * 100}%` }} /></div>
                    <p className="load-bar-note">{row.open_cases} of {totalOpen} open · {row.completed_cases} completed</p>
                  </td>
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

function AllCasesTable({ cases, actor, cohortTotal }: { cases: DashboardCaseItem[]; actor: AuthenticatedProfile; cohortTotal: number }) {
  const subsetId = useId();
  const capped = cases.length < cohortTotal;
  const [personFilter, setPersonFilter] = useState("all");
  const [ageFilter, setAgeFilter] = useState<AgeFilter>("any");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const hasFilters = personFilter !== "all" || ageFilter !== "any" || statusFilter !== "all";

  const people = useMemo(
    () => Array.from(new Set(cases.map((item) => item.created_by_display_name).filter((name): name is string => Boolean(name)))).sort(),
    [cases],
  );

  const filtered = useMemo(() => cases.filter((item) => {
    if (personFilter !== "all" && item.created_by_display_name !== personFilter) return false;
    if (statusFilter === "open" && (item.status === "COMPLETED" || BLOCKED_STATUSES.includes(item.status))) return false;
    if (statusFilter === "blocked" && !BLOCKED_STATUSES.includes(item.status)) return false;
    if (statusFilter === "completed" && item.status !== "COMPLETED") return false;
    if (ageFilter !== "any") {
      const days = item.case_elapsed_ms / 86_400_000;
      if (ageFilter === "lt7" && days >= 7) return false;
      if (ageFilter === "7to30" && (days < 7 || days > 30)) return false;
      if (ageFilter === "gt30" && days <= 30) return false;
    }
    return true;
  }), [cases, personFilter, statusFilter, ageFilter]);

  const accessors = {
    case: (item: DashboardCaseItem) => item.legal_name ?? item.requested_uen,
    team: (item: DashboardCaseItem) => item.team_display_name ?? "",
    person: (item: DashboardCaseItem) => item.created_by_display_name ?? "",
    age: (item: DashboardCaseItem) => item.case_elapsed_ms,
    status: (item: DashboardCaseItem) => item.status,
  };
  const { sorted, sortKey, sortDir, onSort } = useSortableTable(filtered, accessors, "age", "desc");
  const { pageRows, page, setPage, pageCount, total: rowCount, pageSize } = usePagination(sorted);

  return (
    <article className="card" aria-describedby={capped ? subsetId : undefined}>
      <h2>All cases</h2>
      <CaseSubsetNotice id={subsetId} loaded={cases.length} total={cohortTotal} mine={false} />
      <div className="ds-toolbar">
        <SegToggle value={statusFilter} onChange={(value) => { setStatusFilter(value); setPage(0); }} options={STATUS_FILTERS as unknown as Array<{ value: StatusFilter; label: string }>} />
        <label className="filter-label">Person
          <select className="input" value={personFilter} onChange={(event) => { setPersonFilter(event.target.value); setPage(0); }}>
            <option value="all">All</option>
            {people.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>
        <label className="filter-label">Case age / duration
          <select className="input" value={ageFilter} onChange={(event) => { setAgeFilter(event.target.value as AgeFilter); setPage(0); }}>
            {AGE_FILTERS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        {hasFilters && <button type="button" className="btn btn-ghost" onClick={() => { setPersonFilter("all"); setAgeFilter("any"); setStatusFilter("all"); setPage(0); }}>Clear filters</button>}
      </div>
      {sorted.length === 0 && <p className="empty-copy">{capped ? "No loaded cases match these filters." : "No cases match these filters."}</p>}
      {sorted.length > 0 && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <SortableTh label="Case" sortKey="case" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                {actor.role === "DIRECTOR" && <SortableTh label="Team" sortKey="team" activeKey={sortKey} dir={sortDir} onSort={onSort} />}
                <SortableTh label="Created by" sortKey="person" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Case age / duration" sortKey="age" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortableTh label="Status" sortKey="status" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((item) => (
                <tr key={item.case_id} className="clickable">
                  <td><strong>{item.legal_name ?? item.requested_uen}</strong><span className="cell-note">{item.requested_uen}{item.delay_note ? ` · ${item.delay_note}` : ""}</span></td>
                  {actor.role === "DIRECTOR" && <td>{item.team_display_name ?? "Unassigned"}</td>}
                  <td>{item.created_by_display_name ?? "—"}</td>
                  <td aria-label={`${item.status === "COMPLETED" ? "Case duration" : "Case age"}: ${formatDuration(item.case_elapsed_ms)}`}>{formatDuration(item.case_elapsed_ms)}</td>
                  <td><span className={statusTagClass(item.status)}>{item.status.replaceAll("_", " ")}</span></td>
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

function TeamDashboard({ dashboard, actor, includesSample }: { dashboard: DashboardSnapshot; actor: AuthenticatedProfile; includesSample: boolean }) {
  const totals = dashboard.totals;
  const runningCount = dashboard.status_breakdown
    .filter((item) => !BLOCKED_STATUSES.includes(item.status) && item.status !== "COMPLETED")
    .reduce((sum, item) => sum + item.count, 0);
  const blockedCount = dashboard.status_breakdown
    .filter((item) => BLOCKED_STATUSES.includes(item.status))
    .reduce((sum, item) => sum + item.count, 0);

  return (
    <>
      <div className="dashboard-kpis dashboard-kpis--4" aria-label="Dashboard totals">
        <article className="dashboard-kpi"><span>Open cases</span><strong>{totals.non_completed_cases}</strong><p className="text-muted">{runningCount} running · {blockedCount} blocked</p></article>
        <article className="dashboard-kpi"><span>Onboarded</span><strong>{totals.completed_cases}</strong></article>
        <article className="dashboard-kpi"><span>Zero-touch rate</span><strong>{formatPercent(dashboard.zero_touch_rate)}</strong><p className="text-muted">Completed cases with no recorded exception interventions; final review still required.</p></article>
        <article className="dashboard-kpi"><span>Mean recorded run time</span><strong>{formatDuration(dashboard.timing.mean_total_duration_ms)}</strong><p className="text-muted">{formatDuration(dashboard.timing.zero_touch_mean_duration_ms)} zero-touch · {formatDuration(dashboard.timing.blocked_mean_duration_ms)} for {dashboard.timing.blocked_count} cases with exception interventions</p></article>
      </div>

      {totals.total_cases === 0 && <div className="ds-banner">No onboarding cases are available for your current scope.</div>}

      <StageTimingTable stageTiming={dashboard.stage_timing} />

      <div className="dashboard-grid dashboard-grid--distributions">
        <WeeklyOnboardedChart weeks={dashboard.weekly_onboarded} includesSample={includesSample} />
        <ExceptionBreakdown exceptions={dashboard.exception_breakdown} />
      </div>

      <div className="section-divider"><span className="h2a">Workload</span><span className="section-divider-rule" /></div>
      <WorkloadTable rows={dashboard.workload_by_person} />
      <AllCasesTable cases={dashboard.scoped_cases} actor={actor} cohortTotal={totals.total_cases} />
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

      {dashScope === "team" ? <TeamDashboard dashboard={dashboard} actor={actor} includesSample={sampleCases > 0} /> : <MyWorkDashboard activityRefresh={activityRefresh} dashboard={dashboard} actor={actor} teamFilter={teamFilter} />}
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
