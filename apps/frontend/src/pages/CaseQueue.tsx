import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";

import { deleteZeroTouchCase, fetchZeroTouchCases } from "../api";
import type { PriorityFilter, PrioritySort } from "../api";
import {
  caseDeletedEffect,
  casePortfolioQueryOptions,
  priorityMutationEffect,
} from "../caseQueries";
import { formatDateNoSeconds, formatDuration, formatTimestamp, stageProgressLabel } from "../shared";
import { paths } from "../navigation";
import type { CaseRowView } from "../viewModels";
import { mapZeroTouchCaseToCaseRow } from "../viewModels";
import DeleteCaseDialog from "./DeleteCaseDialog";
import PriorityControl, { PriorityBadge, PriorityListControls } from "./PriorityControl";
import DirectorTeamFilter from "./DirectorTeamFilter";
import {
  BUSINESS_EXCEPTION_TYPE_LABELS,
  BUSINESS_EXCEPTION_TYPES,
  type AuthenticatedProfile,
  type BusinessExceptionType,
} from "../types";

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

export interface CaseQueuePresentationState {
  status: string;
  priority: PriorityFilter;
  prioritySort: PrioritySort;
  jurisdiction: string;
  search: string;
  attentionType?: BusinessExceptionType | "";
}

export const DEFAULT_CASE_QUEUE_PRESENTATION: CaseQueuePresentationState = {
  status: "",
  priority: "all",
  prioritySort: "highest_first",
  jurisdiction: "",
  search: "",
  attentionType: "",
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
  const { status, priority, prioritySort, jurisdiction, search } = presentation;
  const attentionType = presentation.attentionType ?? "";
  const [teamFilter, setTeamFilter] = useState("all");
  const [offset, setOffset] = useState(0);
  const normalizedSearch = search.trim();
  const [debouncedSearch, setDebouncedSearch] = useState(normalizedSearch);
  const limit = 50;
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
      status: status ? status as CaseRowView["status"] : undefined,
      priority,
      prioritySort,
      teamFilter,
      attentionType: attentionType || undefined,
      jurisdiction: jurisdiction
        ? jurisdiction as "SG" | "AU" | "MY" | "HK"
        : undefined,
      search: debouncedSearch || undefined,
      offset,
      limit,
    }),
    enabled: !searchIsDebouncing,
  });
  const cases = useMemo(
    () => (query.data?.items ?? []).map(mapZeroTouchCaseToCaseRow),
    [query.data],
  );

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
            Onboarding runs on its own. A case only needs a person when a stage cannot clear
            itself.
          </p>
        </div>
      </div>
      <div className="ds-toolbar">
        <DirectorTeamFilter
          actor={actor}
          value={teamFilter}
          onChange={(value) => {
            setOffset(0);
            setTeamFilter(value);
          }}
        />
        <select
          className="input"
          aria-label="Status filter"
          style={{ width: 200 }}
          value={status}
          onChange={(event) => updatePresentation({ status: event.target.value })}
        >
          <option value="">Status: All</option>
          <option value="PENDING_INPUTS">Pending inputs</option>
          <option value="RUNNING">Running</option>
          <option value="WAITING_FOR_REVIEW">Attention required</option>
          <option value="RESUMING">Resuming</option>
          <option value="RECOVERY_PENDING">Recovery pending</option>
          <option value="TECHNICAL_FAILURE">Technical failure</option>
          <option value="COMPLETED">Completed</option>
        </select>
        <PriorityListControls
          filter={priority}
          sort={prioritySort}
          onFilterChange={(value) => updatePresentation({ priority: value })}
          onSortChange={(value) => updatePresentation({ prioritySort: value })}
        />
        <label className="attention-filter">
          <span>Open business exception type</span>
          <select
            className="input"
            value={attentionType}
            onChange={(event) => updatePresentation({
              attentionType: event.target.value as BusinessExceptionType | "",
            })}
          >
            <option value="">All types (no type filter)</option>
            {BUSINESS_EXCEPTION_TYPES.map((type) => (
              <option key={type} value={type}>{BUSINESS_EXCEPTION_TYPE_LABELS[type]}</option>
            ))}
          </select>
        </label>
        <select
          className="input"
          aria-label="Jurisdiction filter"
          style={{ width: 190 }}
          value={jurisdiction}
          onChange={(event) => updatePresentation({ jurisdiction: event.target.value })}
        >
          <option value="">Jurisdiction: All</option>
          <option value="SG">Singapore</option>
          <option value="AU">Australia</option>
          <option value="MY">Malaysia</option>
          <option value="HK">Hong Kong</option>
        </select>
        <input
          className="input"
          aria-label="Search cases"
          style={{ flex: 1, minWidth: 220 }}
          value={search}
          onChange={(event) => updatePresentation({ search: event.target.value })}
          placeholder="Search case, UEN / ACN, or company…"
        />
      </div>

      {searchIsDebouncing && <p className="text-muted" aria-live="polite">Updating search…</p>}
      {query.isError && !query.data && !searchIsDebouncing && <div className="ds-banner ds-banner-warn">{query.error instanceof Error ? query.error.message : "The case queue is unavailable."}</div>}
      {!searchIsDebouncing && query.isError && query.data && <div className="ds-banner ds-banner-warn">Refresh failed; cached cases remain visible.</div>}
      {query.isPending && !searchIsDebouncing && <p className="text-muted">Loading cases…</p>}
      {!searchIsDebouncing && query.isFetching && !query.isPending && <p className="refreshing-indicator">Refreshing…</p>}
      {!searchIsDebouncing && !query.isError && !query.isPending && cases.length === 0 && (
        <p className="text-muted">No cases match these filters.</p>
      )}
      {!searchIsDebouncing && cases.length > 0 && (
        <p className="text-muted" aria-live="polite">
          Showing {offset + 1}–{offset + cases.length} on page {Math.floor(offset / limit) + 1}.
          Total results are not calculated.
        </p>
      )}
      {!searchIsDebouncing && query.data?.observed_at && (
        <p className="text-muted timing-observation">
          Timing observed at {formatTimestamp(query.data.observed_at)}. Refresh to obtain a new observation.
        </p>
      )}
      {!searchIsDebouncing && cases.length > 0 && (
        <div className="table-card table-scroll" tabIndex={0} aria-label="Cases table">
          <table className="table case-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Registration ID</th>
                <th>Jurisdiction</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Client scope</th>
                <th>Stage</th>
                <th>Open business exceptions</th>
                <th>Created</th>
                <th>Updated</th>
                <th>Operational timing</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.case_id}>
                  <td>{item.company_name ?? item.requested_uen}</td>
                  <td>{item.requested_uen}</td>
                  <td>{item.jurisdiction ?? "—"}</td>
                  <td>
                    <span className={statusTagClass(item.status)}>
                      {item.status.replaceAll("_", " ")}
                    </span>
                    <span className="cell-note">
                      {item.active_exception_count} open · {item.human_interventions} human
                    </span>
                  </td>
                  <td>
                    <PriorityBadge priority={item.priority} />
                    <PriorityControl
                      caseId={item.case_id}
                      priority={item.priority}
                      onUpdated={refreshAfterPriorityUpdate}
                    />
                  </td>
                  <td>{item.client_scope_label ?? "Legacy unassigned"}</td>
                  <td>
                    {stageProgressLabel(item.current_stage)}
                    <span className="cell-note">{item.final_outcome ?? item.current_stage.replaceAll("_", " ")}</span>
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
                      <span className="cell-note">No open business exceptions recorded</span>
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
            </tbody>
          </table>
        </div>
      )}
      {!searchIsDebouncing && query.data && (
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
            disabled={!query.data.has_more || offset >= 10_000}
            onClick={() => setOffset((current) => Math.min(10_000, current + limit))}
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
