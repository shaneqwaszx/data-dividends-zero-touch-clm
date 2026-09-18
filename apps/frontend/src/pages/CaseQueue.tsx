import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteZeroTouchCase, fetchZeroTouchCases } from "../api";
import type { PriorityFilter, PrioritySort } from "../api";
import { caseDeletedEffect, caseListQueryOptions, priorityMutationEffect } from "../caseQueries";
import { formatDateNoSeconds, stageProgressLabel } from "../shared";
import type { CaseRowView } from "../viewModels";
import { mapZeroTouchCaseToCaseRow } from "../viewModels";
import DeleteCaseDialog from "./DeleteCaseDialog";
import PriorityControl, { PriorityBadge, PriorityListControls } from "./PriorityControl";
import DirectorTeamFilter from "./DirectorTeamFilter";
import type { AuthenticatedProfile } from "../types";

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
): Promise<CaseRowView[]> {
  const items = await fetchZeroTouchCases(status, priority, prioritySort, teamFilter);
  return items.map(mapZeroTouchCaseToCaseRow);
}

export interface CaseQueuePresentationState {
  status: string;
  priority: PriorityFilter;
  prioritySort: PrioritySort;
  jurisdiction: string;
  search: string;
}

export const DEFAULT_CASE_QUEUE_PRESENTATION: CaseQueuePresentationState = {
  status: "",
  priority: "all",
  prioritySort: "highest_first",
  jurisdiction: "",
  search: "",
};

export default function CaseQueue({
  actor,
  presentation,
  onPresentationChange,
  onOpenCase,
}: {
  actor: AuthenticatedProfile;
  presentation: CaseQueuePresentationState;
  onPresentationChange: (value: CaseQueuePresentationState) => void;
  onOpenCase: (caseId: string) => void;
}) {
  const { status, priority, prioritySort, jurisdiction, search } = presentation;
  const [teamFilter, setTeamFilter] = useState("all");
  const updatePresentation = (change: Partial<CaseQueuePresentationState>) =>
    onPresentationChange({ ...presentation, ...change });
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<CaseRowView | null>(null);
  const query = useQuery(caseListQueryOptions(
    actor.user_id,
    status ? status as CaseRowView["status"] : undefined,
    priority,
    prioritySort,
    teamFilter,
  ));
  const cases = useMemo(
    () => (query.data ?? []).map(mapZeroTouchCaseToCaseRow),
    [query.data],
  );

  async function refreshAfterPriorityUpdate(): Promise<void> {
    await priorityMutationEffect(queryClient, actor.user_id);
  }

  const filteredCases = useMemo(() => {
    const query = search.trim().toLowerCase();
    return cases.filter((item) =>
      (!jurisdiction || item.jurisdiction === jurisdiction)
      && (!query || [item.company_name, item.requested_uen, item.case_id]
          .filter((value): value is string => Boolean(value))
          .some((value) => value.toLowerCase().includes(query))),
    );
  }, [cases, jurisdiction, search]);
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
        <DirectorTeamFilter actor={actor} value={teamFilter} onChange={setTeamFilter} />
        <select
          className="input"
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
        <select
          className="input"
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
          style={{ flex: 1, minWidth: 220 }}
          value={search}
          onChange={(event) => updatePresentation({ search: event.target.value })}
          placeholder="Search case, UEN / ACN, or company…"
        />
      </div>

      {query.isError && !query.data && <div className="ds-banner ds-banner-warn">{query.error instanceof Error ? query.error.message : "The case queue is unavailable."}</div>}
      {query.isError && query.data && <div className="ds-banner ds-banner-warn">Refresh failed; cached cases remain visible.</div>}
      {query.isPending && <p className="text-muted">Loading cases…</p>}
      {query.isFetching && !query.isPending && <p className="refreshing-indicator">Refreshing…</p>}
      {!query.isError && !query.isPending && filteredCases.length === 0 && (
        <p className="text-muted">No cases match these filters.</p>
      )}
      {filteredCases.length > 0 && (
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
                <th>Assigned to</th>
                <th>Created</th>
                <th>Updated</th>
                {canDelete && <th aria-label="Case actions" />}
              </tr>
            </thead>
            <tbody>
              {filteredCases.map((item) => (
                <tr
                  key={item.case_id}
                  className="clickable"
                  tabIndex={0}
                  onClick={() => onOpenCase(item.case_id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onOpenCase(item.case_id);
                    }
                  }}
                >
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
                  <td>{item.assigned_to ?? "—"}</td>
                  <td>{item.created_at ? formatDateNoSeconds(item.created_at) : "—"}</td>
                  <td>{formatDateNoSeconds(item.updated_at)}</td>
                  {canDelete && (
                    <td>
                      <button
                        type="button"
                        className="btn btn-ghost delete-case-action"
                        aria-label={`Delete ${item.company_name ?? item.requested_uen}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          setDeleteTarget(item);
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
