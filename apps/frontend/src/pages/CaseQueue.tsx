import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";

import { deleteZeroTouchCase, fetchZeroTouchCases } from "../api";
import type { CasePortfolioProgress, PriorityFilter, PrioritySort } from "../api";
import {
  CASES_PAGE_SIZE,
  caseDeletedEffect,
  casePortfolioQueryOptions,
  priorityMutationEffect,
} from "../caseQueries";
import { formatDateNoSeconds, formatDuration, formatTimestamp, targetOutcomeLabel } from "../shared";
import { paths } from "../navigation";
import type { CaseRowView } from "../viewModels";
import { mapZeroTouchCaseToCaseRow } from "../viewModels";
import DeleteCaseDialog from "./DeleteCaseDialog";
import PriorityControl, { PriorityFilterSelect, PrioritySortSelect } from "./PriorityControl";
import DirectorTeamFilter from "./DirectorTeamFilter";
import { sampleCaseRows, type SampleCaseRow } from "./mockDashboards/onboardingSample";
import {
  BUSINESS_EXCEPTION_TYPE_LABELS,
  BUSINESS_EXCEPTION_TYPES,
  type AuthenticatedProfile,
  type BusinessExceptionType,
} from "../types";

/** "Updated just now" / "Updated 3m 31s ago", re-rendered every 30 s; full time as tooltip. */
function UpdatedAgo({ observedAt }: { observedAt: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    setNow(Date.now());
    const interval = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(interval);
  }, [observedAt]);
  const elapsed = Math.max(0, now - Date.parse(observedAt));
  return (
    <span title={formatTimestamp(observedAt)}>
      Updated {elapsed < 60_000 ? "just now" : `${formatDuration(elapsed)} ago`}
    </span>
  );
}

/** Copies the GoldTier party ID so it can be looked up in GoldTier. */
function CopyGoldTierId({ value, company }: { value: string; company: string }) {
  const [copied, setCopied] = useState(false);
  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }
  return (
    <button type="button" className="btn btn-ghost case-goldtier-id__copy" aria-label={`Copy GoldTier ID for ${company}`} onClick={() => void copy()}>
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function manualStepsLabel(humanInterventions: number): string {
  return humanInterventions === 1 ? "1 manual step" : `${humanInterventions} manual steps`;
}

function statusTagClass(status: CaseRowView["status"]): string {
  if (status === "COMPLETED") return "tag tag-accent";
  if (status === "WAITING_FOR_REVIEW" || status === "RECOVERY_PENDING") return "tag tag-neutral";
  if (status === "TECHNICAL_FAILURE") return "tag tag-outline";
  return "tag tag-accent-2";
}

export async function loadCaseQueueRows(
  status?: CaseRowView["status"],
  priority: PriorityFilter = "all",
  prioritySort: PrioritySort = "highest_first",
  teamFilter?: string,
  attentionType?: BusinessExceptionType,
): Promise<CaseRowView[]> {
  const items = await fetchZeroTouchCases(
    status,
    priority,
    prioritySort,
    teamFilter,
    undefined,
    attentionType,
  );
  return items.map(mapZeroTouchCaseToCaseRow);
}

export type CaseQueueView = "all" | CasePortfolioProgress;

interface SampleCaseFilters {
  view: CaseQueueView;
  status: string;
  priority: PriorityFilter;
  prioritySort: PrioritySort;
  jurisdiction: string;
  search: string;
  attentionType: string;
  createdFrom: string;
  createdTo: string;
}

/** Apply the Cases tab filters (other than team) to the fixed sample cases. */
export function filterSampleCases(rows: SampleCaseRow[], filters: SampleCaseFilters): SampleCaseRow[] {
  const search = filters.search.trim().toLowerCase();
  return rows
    .filter((row) => filters.view !== "onboarded" || row.status === "COMPLETED")
    .filter((row) => filters.view !== "in_progress" || row.status !== "COMPLETED")
    .filter((row) => !filters.status || row.status === filters.status)
    .filter((row) => filters.priority === "all"
      || (filters.priority === "prioritised" ? row.priority !== null
        : filters.priority === "unset" ? row.priority === null
          : row.priority === Number(filters.priority)))
    .filter((row) => !filters.jurisdiction || row.jurisdiction === filters.jurisdiction)
    .filter((row) => !search || (row.legal_name ?? "").toLowerCase().includes(search) || row.requested_uen.toLowerCase().includes(search))
    .filter((row) => !filters.attentionType || row.open_blocker_types.includes(filters.attentionType as BusinessExceptionType))
    .filter((row) => !filters.createdFrom || row.created_at.slice(0, 10) >= filters.createdFrom)
    .filter((row) => !filters.createdTo || row.created_at.slice(0, 10) <= filters.createdTo)
    .sort((a, b) => {
      if (a.priority === b.priority) return a.case_id < b.case_id ? -1 : 1;
      if (a.priority === null) return 1;
      if (b.priority === null) return -1;
      return filters.prioritySort === "highest_first" ? b.priority - a.priority : a.priority - b.priority;
    });
}

/**
 * A fixed dashboard sample case as a row of the Cases table. It opens the read-only case page;
 * priority is shown as text and there is no delete, because neither exists in the backend.
 */
function SampleCaseTableRow({ row }: { row: SampleCaseRow }) {
  return (
    <tr>
      <td>{row.legal_name ?? row.requested_uen}</td>
      <td>{row.requested_uen}</td>
      <td>{row.jurisdiction}</td>
      <td>
        <span className={statusTagClass(row.status)}>{row.status.replaceAll("_", " ")}</span>
        {row.blocker_count > 0
          ? <span className="cell-note">{manualStepsLabel(row.blocker_count)}</span>
          : row.status === "COMPLETED"
            ? <strong className="cell-note zero-touch-note">Zero-touch</strong>
            : <span className="cell-note">No manual steps yet</span>}
      </td>
      <td>{row.priority ?? "Not set"}</td>
      <td>{row.team_display_name ?? "—"}</td>
      <td>
        Current stage
        <span className="cell-note">{row.final_outcome ? targetOutcomeLabel(row.final_outcome) : row.current_stage.replaceAll("_", " ")}</span>
      </td>
      <td>
        {row.open_blocker_types.length > 0 ? (
          <div className="attention-type-list">
            {row.open_blocker_types.map((type) => (
              <span className="tag tag-neutral" key={type}>{BUSINESS_EXCEPTION_TYPE_LABELS[type]}</span>
            ))}
          </div>
        ) : <span className="text-muted">—</span>}
      </td>
      <td>{formatDateNoSeconds(row.created_at)}</td>
      <td>{formatDateNoSeconds(row.updated_at)}</td>
      <td>
        <div className="case-timing-cell">
          <span>{row.completed_at ? "Case duration" : "Case age"}: {formatDuration(row.case_elapsed_ms)}</span>
          <span className="cell-note">Last updated: {formatDuration(Math.max(0, Date.now() - Date.parse(row.updated_at)))} ago</span>
        </div>
      </td>
      <td><Link className="btn btn-secondary" to={paths.sampleCaseDetail(row.case_id)}>Open</Link></td>
    </tr>
  );
}

export interface CaseQueuePresentationState {
  /** Show: all cases, only cases still in progress, or only onboarded (completed) cases. */
  view?: CaseQueueView;
  status: string;
  priority: PriorityFilter;
  prioritySort: PrioritySort;
  jurisdiction: string;
  search: string;
  attentionType?: BusinessExceptionType | "";
  createdFrom?: string;
  createdTo?: string;
}

export const DEFAULT_CASE_QUEUE_PRESENTATION: CaseQueuePresentationState = {
  view: "all",
  status: "",
  priority: "all",
  prioritySort: "highest_first",
  jurisdiction: "",
  search: "",
  attentionType: "",
  createdFrom: "",
  createdTo: "",
};

export default function CaseQueue({
  actor,
  presentation,
  onPresentationChange,
}: {
  actor: AuthenticatedProfile;
  presentation: CaseQueuePresentationState;
  onPresentationChange: (value: CaseQueuePresentationState) => void;
}) {
  const { priority, prioritySort, jurisdiction, search } = presentation;
  const view = presentation.view ?? "all";
  // The Onboarded view fixes Status to Completed; In progress never offers Completed.
  const status = view === "onboarded" ? "COMPLETED"
    : view === "in_progress" && presentation.status === "COMPLETED" ? "" : presentation.status;
  const attentionType = presentation.attentionType ?? "";
  const createdFrom = presentation.createdFrom ?? "";
  const createdTo = presentation.createdTo ?? "";
  const createdRangeInvalid = Boolean(createdFrom && createdTo && createdFrom > createdTo);
  const [teamFilter, setTeamFilter] = useState("all");
  const [offset, setOffset] = useState(0);
  // Live case count learned when leaving the last live page; places later sample-only pages.
  const [liveTotal, setLiveTotal] = useState<number | null>(null);
  const normalizedSearch = search.trim();
  const [debouncedSearch, setDebouncedSearch] = useState(normalizedSearch);
  const limit = CASES_PAGE_SIZE;
  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearch(normalizedSearch), 300);
    return () => window.clearTimeout(timeout);
  }, [normalizedSearch]);
  const searchIsDebouncing = normalizedSearch !== debouncedSearch;
  const updatePresentation = (change: Partial<CaseQueuePresentationState>) => {
    setOffset(0);
    onPresentationChange({ ...presentation, ...change });
  };
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<CaseRowView | null>(null);
  const query = useQuery({
    ...casePortfolioQueryOptions(actor.user_id, {
      status: view !== "onboarded" && status ? status as CaseRowView["status"] : undefined,
      progress: view === "all" ? undefined : view,
      priority,
      prioritySort,
      teamFilter,
      attentionType: attentionType || undefined,
      jurisdiction: jurisdiction
        ? jurisdiction as "SG" | "AU" | "MY" | "HK"
        : undefined,
      search: debouncedSearch || undefined,
      createdFrom: createdFrom || undefined,
      createdTo: createdTo || undefined,
      offset,
      limit,
    }),
    enabled: !searchIsDebouncing && !createdRangeInvalid,
  });
  const cases = useMemo(
    () => (createdRangeInvalid ? [] : query.data?.items ?? []).map(mapZeroTouchCaseToCaseRow),
    [query.data, createdRangeInvalid],
  );
  // Dates are placed relative to when the tab opened, like the dashboard does.
  const allSampleRows = useMemo(() => sampleCaseRows(actor), [actor]);
  const sampleRows = useMemo(() => (createdRangeInvalid ? [] : filterSampleCases(allSampleRows, {
    view, status, priority, prioritySort, jurisdiction, search: normalizedSearch,
    attentionType, createdFrom, createdTo,
  })), [allSampleRows, createdRangeInvalid, view, status, priority, prioritySort, jurisdiction, normalizedSearch, attentionType, createdFrom, createdTo]);
  // Sample cases continue the live sequence at the same page size: they fill the rest of the
  // last live page, then follow on their own pages. The portfolio API reports only has_more,
  // so the live count is known on the last live page and remembered when paging past it.
  const liveEnd = query.data && !query.data.has_more
    ? (cases.length > 0 || offset === 0 ? offset + cases.length : liveTotal ?? offset)
    : null;
  const sampleStart = liveEnd === null ? 0 : Math.max(0, offset - liveEnd);
  const pageSampleRows = liveEnd === null ? [] : sampleRows.slice(sampleStart, sampleStart + Math.max(0, limit - cases.length));
  const samplesRemain = liveEnd !== null && sampleStart + pageSampleRows.length < sampleRows.length;
  const shownCount = cases.length + pageSampleRows.length;

  async function refreshAfterPriorityUpdate(): Promise<void> {
    await priorityMutationEffect(queryClient, actor.user_id);
  }

  const canDelete = actor.role === "DIRECTOR" || actor.role === "RELATIONSHIP_MANAGER";

  async function deleteSelectedCase(): Promise<void> {
    if (!deleteTarget) return;
    await deleteZeroTouchCase(deleteTarget.case_id);
    await caseDeletedEffect(queryClient, actor.user_id, deleteTarget.case_id);
    setDeleteTarget(null);
  }

  return (
    <div className="ds-root ds-page">
      <div className="ds-page-header">
        <div>
          <h1>Cases</h1>
          <p className="text-muted">
            Every case you can access, including completed ones. One customer may have more than
            one case.
          </p>
        </div>
      </div>
      <div className="case-view">
        <span id="case-view-label" className="case-filter__label">Show</span>
        <div className="seg-toggle" role="group" aria-labelledby="case-view-label">
          {([["all", "All cases"], ["in_progress", "In progress"], ["onboarded", "Onboarded"]] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={view === value}
              onClick={() => updatePresentation({
                view: value,
                status: value === "onboarded" || (value === "in_progress" && presentation.status === "COMPLETED")
                  ? "" : presentation.status,
              })}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="case-filters" role="search" aria-label="Filter cases">
        <div className="case-filter case-filter--search">
          <label htmlFor="case-filter-search">Search</label>
          <div className="case-search-field">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <input
              id="case-filter-search"
              type="search"
              value={search}
              onChange={(event) => updatePresentation({ search: event.target.value })}
              placeholder="Company, UEN or case ID"
            />
          </div>
        </div>
        <div className="case-filter">
          <label htmlFor="case-filter-status">Status</label>
          <select
            id="case-filter-status"
            className="input"
            value={status}
            disabled={view === "onboarded"}
            onChange={(event) => updatePresentation({ status: event.target.value })}
          >
            {view !== "onboarded" && <option value="">All</option>}
            <option value="PENDING_INPUTS">Pending inputs</option>
            <option value="RUNNING">Running</option>
            <option value="WAITING_FOR_REVIEW">Attention required</option>
            <option value="RESUMING">Resuming</option>
            <option value="RECOVERY_PENDING">Recovery pending</option>
            <option value="TECHNICAL_FAILURE">Technical failure</option>
            {view !== "in_progress" && <option value="COMPLETED">Completed</option>}
          </select>
        </div>
        <div className="case-filter">
          <label htmlFor="case-filter-priority">Priority</label>
          <PriorityFilterSelect
            id="case-filter-priority"
            allLabel="All"
            value={priority}
            onChange={(value) => updatePresentation({ priority: value })}
          />
        </div>
        <div className="case-filter case-filter--wide">
          <label htmlFor="case-filter-attention">Needs attention</label>
          <select
            id="case-filter-attention"
            className="input"
            value={attentionType}
            onChange={(event) => updatePresentation({
              attentionType: event.target.value as BusinessExceptionType | "",
            })}
          >
            <option value="">Any</option>
            {BUSINESS_EXCEPTION_TYPES.map((type) => (
              <option key={type} value={type}>{BUSINESS_EXCEPTION_TYPE_LABELS[type]}</option>
            ))}
          </select>
        </div>
        <div className="case-filter">
          <label htmlFor="case-filter-jurisdiction">Jurisdiction</label>
          <select
            id="case-filter-jurisdiction"
            className="input"
            value={jurisdiction}
            onChange={(event) => updatePresentation({ jurisdiction: event.target.value })}
          >
            <option value="">All</option>
            <option value="SG">Singapore</option>
            <option value="AU">Australia</option>
            <option value="MY">Malaysia</option>
            <option value="HK">Hong Kong</option>
          </select>
        </div>
        <DirectorTeamFilter
          actor={actor}
          value={teamFilter}
          onChange={(value) => {
            setOffset(0);
            setTeamFilter(value);
          }}
        />
        <div className="case-filter case-filter--dates" role="group" aria-labelledby="case-filter-created">
          <span id="case-filter-created" className="case-filter__label">Created between</span>
          <div className="case-filter__pair">
            <label>
              <span className="sr-only">Created from</span>
              <input
                className="input"
                type="date"
                value={createdFrom}
                max={createdTo || undefined}
                aria-describedby="case-created-date-help"
                onChange={(event) => updatePresentation({ createdFrom: event.target.value })}
              />
            </label>
            <label>
              <span className="sr-only">Created to</span>
              <input
                className="input"
                type="date"
                value={createdTo}
                min={createdFrom || undefined}
                aria-describedby="case-created-date-help"
                onChange={(event) => updatePresentation({ createdTo: event.target.value })}
              />
            </label>
          </div>
        </div>
        <div className="case-filter case-filter--sort">
          <label htmlFor="case-filter-sort">Sort</label>
          <PrioritySortSelect
            id="case-filter-sort"
            value={prioritySort}
            onChange={(value) => updatePresentation({ prioritySort: value })}
          />
        </div>
      </div>
      <p id="case-created-date-help" className="control-help">
        Creation dates include both selected days in Singapore (Asia/Singapore, UTC+08:00).
      </p>
      {createdRangeInvalid && <p className="ds-banner ds-banner-warn" role="alert">Created from must be on or before Created to.</p>}

      {searchIsDebouncing && <p className="text-muted" aria-live="polite">Updating search…</p>}
      {query.isError && !query.data && !searchIsDebouncing && <div className="ds-banner ds-banner-warn">{query.error instanceof Error ? query.error.message : "The case queue is unavailable."}</div>}
      {!searchIsDebouncing && query.isError && query.data && <div className="ds-banner ds-banner-warn">Refresh failed; cached cases remain visible.</div>}
      {query.isPending && !searchIsDebouncing && !createdRangeInvalid && <p className="text-muted">Loading cases…</p>}
      {!searchIsDebouncing && query.isFetching && !query.isPending && <p className="refreshing-indicator">Refreshing…</p>}
      {!searchIsDebouncing && !createdRangeInvalid && !query.isError && !query.isPending && shownCount === 0 && (
        <p className="text-muted">No cases match these filters.</p>
      )}
      {!searchIsDebouncing && (shownCount > 0 || query.data?.observed_at) && (
        <div className="case-queue-meta">
          {shownCount > 0 ? (
            <p className="text-muted" aria-live="polite">Showing {offset + 1}–{offset + shownCount}</p>
          ) : <span />}
          {query.data?.observed_at && (
            <div className="case-queue-meta__refresh text-muted">
              <UpdatedAgo observedAt={query.data.observed_at} />
              <button
                type="button"
                className="btn btn-secondary"
                disabled={query.isFetching}
                onClick={() => void query.refetch()}
              >
                Refresh
              </button>
            </div>
          )}
        </div>
      )}
      {!searchIsDebouncing && shownCount > 0 && (
        <div className="table-card table-scroll" tabIndex={0} aria-label="Cases table">
          <table className="table case-table">
            <colgroup>
              <col /><col /><col /><col /><col /><col />
              <col /><col /><col /><col /><col /><col />
            </colgroup>
            <thead>
              <tr>
                <th>Company</th>
                <th>Registration ID</th>
                <th>Jurisdiction</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Client scope</th>
                <th>Stage</th>
                <th>Needs attention</th>
                <th>Created</th>
                <th>Updated</th>
                <th>Operational timing</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.case_id}>
                  <td>
                    {item.company_name ?? item.requested_uen}
                    {item.goldtier_party_id && (
                      <span className="case-goldtier-id">
                        <span className="cell-note">GoldTier ID: <code>{item.goldtier_party_id}</code></span>
                        <CopyGoldTierId value={item.goldtier_party_id} company={item.company_name ?? item.requested_uen} />
                        <span className="case-goldtier-id__tip" aria-hidden="true">{item.goldtier_party_id}</span>
                      </span>
                    )}
                  </td>
                  <td>{item.requested_uen}</td>
                  <td>{item.jurisdiction ?? "—"}</td>
                  <td>
                    <span className={statusTagClass(item.status)}>
                      {item.status.replaceAll("_", " ")}
                    </span>
                    {/* Zero-touch is an outcome: only a completed case can claim it. */}
                    {item.human_interventions > 0
                      ? <span className="cell-note">{manualStepsLabel(item.human_interventions)}</span>
                      : item.status === "COMPLETED"
                        ? <strong className="cell-note zero-touch-note">Zero-touch</strong>
                        : <span className="cell-note">No manual steps yet</span>}
                  </td>
                  <td>
                    <PriorityControl
                      caseId={item.case_id}
                      priority={item.priority}
                      onUpdated={refreshAfterPriorityUpdate}
                      saveOnChange
                      label={`Priority for ${item.company_name ?? item.requested_uen}`}
                    />
                  </td>
                  <td>{item.client_scope_label ?? "Legacy unassigned"}</td>
                  <td>
                    Current stage
                    <span className="cell-note">{item.final_outcome ? targetOutcomeLabel(item.final_outcome) : item.current_stage.replaceAll("_", " ")}</span>
                  </td>
                  <td>
                    {item.active_exception_types.length > 0 ? (
                      <div className="attention-type-list">
                        {item.active_exception_types.map((type) => (
                          <span className="tag tag-neutral" key={type}>
                            {BUSINESS_EXCEPTION_TYPE_LABELS[type]}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td>{item.created_at ? formatDateNoSeconds(item.created_at) : "—"}</td>
                  <td>{formatDateNoSeconds(item.updated_at)}</td>
                  <td>
                    {item.timing ? (
                      <div className="case-timing-cell">
                        <span>
                          {item.completed_at ? "Case duration" : "Case age"}: {formatDuration(item.timing.case_elapsed_ms)}
                        </span>
                        <span className="cell-note">
                          Last updated: {formatDuration(item.timing.time_since_last_update_ms)} ago
                        </span>
                      </div>
                    ) : "—"}
                  </td>
                  <td>
                    <Link className="btn btn-secondary" to={paths.caseDetail(item.case_id)}>Open</Link>
                    {canDelete && (
                      <button
                        type="button"
                        className="btn btn-ghost delete-case-action"
                        aria-label={`Delete ${item.company_name ?? item.requested_uen}`}
                        onClick={() => setDeleteTarget(item)}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {pageSampleRows.map((row) => <SampleCaseTableRow key={row.case_id} row={row} />)}
            </tbody>
          </table>
        </div>
      )}
      {!searchIsDebouncing && !createdRangeInvalid && query.data && (
        <nav className="activity-pagination" aria-label="Cases pagination">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={offset === 0}
            onClick={() => setOffset((current) => Math.max(0, current - limit))}
          >
            Previous
          </button>
          <span>Page {Math.floor(offset / limit) + 1}</span>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!(query.data.has_more || samplesRemain) || offset >= 10_000}
            onClick={() => {
              if (liveEnd !== null) setLiveTotal(liveEnd);
              setOffset((current) => Math.min(10_000, current + limit));
            }}
          >
            Next
          </button>
        </nav>
      )}
      {!searchIsDebouncing && query.data?.has_more && offset >= 10_000 && (
        <p className="ds-banner ds-banner-warn">
          More cases may exist beyond the paging limit. Narrow the filters or search.
        </p>
      )}
      {deleteTarget && (
        <DeleteCaseDialog
          caseId={deleteTarget.case_id}
          companyName={deleteTarget.company_name ?? deleteTarget.requested_uen}
          requestedUen={deleteTarget.requested_uen}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={deleteSelectedCase}
        />
      )}
    </div>
  );
}
