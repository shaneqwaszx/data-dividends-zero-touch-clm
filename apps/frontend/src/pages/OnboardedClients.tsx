import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchZeroTouchCases } from "../api";
import type { PriorityFilter, PrioritySort } from "../api";
import { caseListQueryOptions, priorityMutationEffect } from "../caseQueries";
import type { AuthenticatedProfile } from "../types";
import type { OnboardedRowView } from "../viewModels";
import { mapCompletedCaseToOnboardedRow } from "../viewModels";
import PriorityControl, { PriorityBadge, PriorityListControls } from "./PriorityControl";

export function OnboardedActionColumnHeader() {
  return <th aria-label="Open" />;
}

export async function loadOnboardedRows(
  priority: PriorityFilter = "all",
  prioritySort: PrioritySort = "highest_first",
): Promise<OnboardedRowView[]> {
  const items = await fetchZeroTouchCases("COMPLETED", priority, prioritySort);
  return items.map(mapCompletedCaseToOnboardedRow);
}

export default function OnboardedClients({
  actor,
  onOpenClient,
}: {
  actor: AuthenticatedProfile;
  onOpenClient: (clientId: string) => void;
}) {
  const [jurisdiction, setJurisdiction] = useState("");
  const [priority, setPriority] = useState<PriorityFilter>("all");
  const [prioritySort, setPrioritySort] = useState<PrioritySort>("highest_first");
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();
  const query = useQuery(caseListQueryOptions(
    actor.user_id,
    "COMPLETED",
    priority,
    prioritySort,
  ));
  const clients = useMemo(
    () => (query.data ?? []).map(mapCompletedCaseToOnboardedRow),
    [query.data],
  );

  async function refreshAfterPriorityUpdate(): Promise<void> {
    await priorityMutationEffect(queryClient, actor.user_id);
  }

  const filteredClients = useMemo(() => {
    const query = search.trim().toLowerCase();
    return clients.filter((client) => {
      if (jurisdiction && client.jurisdiction !== jurisdiction) return false;
      if (!query) return true;
      return [client.company_name, client.case_id, client.registration_id, client.mock_goldtier_party_id]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLowerCase().includes(query));
    });
  }, [clients, jurisdiction, search]);

  return (
    <div className="ds-root ds-page">
      <h1>Onboarded</h1>
      <p className="text-muted">
        Completed Mock workflow cases from the backend are shown here. This POC does not
        provide a production client master, risk rating, scheduler, or periodic review date.
      </p>

      <div className="ds-toolbar">
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
        <select
          className="input"
          style={{ width: 170 }}
          value=""
          disabled
          aria-describedby="risk-filter-help"
          title="Risk assessment is not connected in this POC"
        >
          <option value="">Risk: All</option>
        </select>
        <input
          className="input"
          style={{ flex: 1, minWidth: 220 }}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search client, UEN / ACN, or company…"
        />
      </div>
      <p id="risk-filter-help" className="control-help">
        Risk assessment is not connected in this POC; risk and next-review values remain unavailable.
      </p>

      {query.isError && !query.data && <div className="ds-banner ds-banner-warn">{query.error instanceof Error ? query.error.message : "The onboarded client list is unavailable."}</div>}
      {query.isError && query.data && <div className="ds-banner ds-banner-warn">Refresh failed; cached clients remain visible.</div>}
      {query.isPending && <p className="text-muted">Loading clients…</p>}
      {query.isFetching && !query.isPending && <p className="refreshing-indicator">Refreshing…</p>}
      {!query.isError && !query.isPending && filteredClients.length === 0 && (
        <p className="text-muted">No clients match these filters.</p>
      )}
      {filteredClients.length > 0 && (
        <div className="table-card table-scroll" tabIndex={0} aria-label="Completed Mock workflow cases">
          <table className="table onboarded-table">
            <thead>
              <tr>
                <th>Mock GoldTier party ID</th>
                <th>Case</th>
                <th>Registration ID</th>
                <th>Company</th>
                <th>Jurisdiction</th>
                <th>Priority</th>
                <th>Client scope</th>
                <th>Risk</th>
                <th>Onboarded</th>
                <th>Next review</th>
                <OnboardedActionColumnHeader />
              </tr>
            </thead>
            <tbody>
              {filteredClients.map((client) => (
                <tr key={client.case_id} className="clickable" tabIndex={0} onClick={() => onOpenClient(client.case_id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onOpenClient(client.case_id); } }}>
                  <td>{client.mock_goldtier_party_id ?? "—"}</td>
                  <td>{client.case_id}</td>
                  <td>{client.registration_id}</td>
                  <td>{client.company_name ?? "—"}</td>
                  <td>{client.jurisdiction ?? "—"}</td>
                  <td>
                    <PriorityBadge priority={client.priority} />
                    <PriorityControl
                      caseId={client.case_id}
                      priority={client.priority}
                      onUpdated={refreshAfterPriorityUpdate}
                    />
                  </td>
                  <td>{client.client_scope_label ?? "Legacy unassigned"}</td>
                  <td>{client.risk_rating ?? "—"}</td>
                  <td>{new Date(client.onboarded_at).toLocaleDateString()}</td>
                  <td>{client.next_review_date ? new Date(client.next_review_date).toLocaleDateString() : "—"}</td>
                  <td><button type="button" className="btn btn-secondary" onClick={(event) => { event.stopPropagation(); onOpenClient(client.case_id); }}>Open</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
