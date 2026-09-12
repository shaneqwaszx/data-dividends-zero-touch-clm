import { useEffect, useMemo, useState } from "react";

import { ApiError, fetchZeroTouchCase, fetchZeroTouchCases } from "../api";
import type { PriorityFilter, PrioritySort } from "../api";
import { formatDateNoSeconds, stageProgressLabel } from "../shared";
import type { CaseRowView } from "../viewModels";
import { mapZeroTouchCaseToCaseRow } from "../viewModels";
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
  const details = await Promise.all(items.map((item) => fetchZeroTouchCase(item.case_id)));
  return items.map((item, index) => mapZeroTouchCaseToCaseRow(item, details[index]));
}

export default function CaseQueue({ actor, onOpenCase }: { actor: AuthenticatedProfile; onOpenCase: (caseId: string) => void }) {
  const [cases, setCases] = useState<CaseRowView[]>([]);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState<PriorityFilter>("all");
  const [prioritySort, setPrioritySort] = useState<PrioritySort>("highest_first");
  const [jurisdiction, setJurisdiction] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [teamFilter, setTeamFilter] = useState("all");

  useEffect(() => {
    let current = true;
    setIsLoading(true);
    void loadCaseQueueRows(
      status ? status as CaseRowView["status"] : undefined,
      priority,
      prioritySort,
      teamFilter,
    )
      .then((items) => {
        if (current) {
          setCases(items);
          setError(null);
        }
      })
      .catch((requestError) => {
        if (!current) return;
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : "The case queue is unavailable.",
        );
      })
      .finally(() => {
        if (current) setIsLoading(false);
      });
    return () => {
      current = false;
    };
  }, [priority, prioritySort, status, teamFilter]);

  async function refreshAfterPriorityUpdate(): Promise<void> {
    setIsLoading(true);
    setError(null);
    try {
      setCases(await loadCaseQueueRows(
        status ? status as CaseRowView["status"] : undefined,
        priority,
        prioritySort,
        teamFilter,
      ));
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "The case queue is unavailable.",
      );
      throw requestError;
    } finally {
      setIsLoading(false);
    }
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
          onChange={(event) => setStatus(event.target.value)}
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
          onFilterChange={setPriority}
          onSortChange={setPrioritySort}
        />
        <select
          className="input"
          style={{ width: 190 }}
          value={jurisdiction}
          onChange={(event) => setJurisdiction(event.target.value)}
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
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search case, UEN / ACN, or company…"
        />
      </div>

      {error && <div className="ds-banner ds-banner-warn">{error}</div>}
      {!error && isLoading && <p className="text-muted">Loading cases…</p>}
      {!error && !isLoading && filteredCases.length === 0 && (
        <p className="text-muted">No cases match these filters.</p>
      )}
      {!error && filteredCases.length > 0 && (
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
