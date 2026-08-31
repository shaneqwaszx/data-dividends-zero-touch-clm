import { useEffect, useMemo, useState } from "react";

import { ApiError, fetchClients } from "../api";
import type { ClientRecord } from "../types";

export default function OnboardedClients({
  onOpenClient,
}: {
  onOpenClient: (clientId: string) => void;
}) {
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [jurisdiction, setJurisdiction] = useState("");
  const [risk, setRisk] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    void fetchClients({ jurisdiction: jurisdiction || undefined })
      .then((items) => {
        setClients(items);
        setError(null);
      })
      .catch((requestError) => {
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : "The onboarded client list is unavailable.",
        );
      })
      .finally(() => setIsLoading(false));
  }, [jurisdiction]);

  const filteredClients = useMemo(() => {
    const query = search.trim().toLowerCase();
    return clients.filter((client) => {
      if (risk && client.risk_rating !== risk) return false;
      if (!query) return true;
      return [client.company_name, client.client_id, client.registration_id]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLowerCase().includes(query));
    });
  }, [clients, risk, search]);

  return (
    <div className="ds-root ds-page">
      <h1>Onboarded</h1>
      <p className="text-muted">
        Clients written to the client database. Completed cases leave the case list and land
        here; the scheduler holds the next-review dates and runs re-screening against the
        sanctions lists.
      </p>

      <div className="ds-toolbar">
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
          value={risk}
          onChange={(event) => setRisk(event.target.value)}
        >
          <option value="">Risk: All</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
        </select>
        <input
          className="input"
          style={{ flex: 1, minWidth: 220 }}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search client, UEN / ACN, or company…"
        />
      </div>

      {error && <div className="ds-banner ds-banner-warn">{error}</div>}
      {!error && isLoading && <p className="text-muted">Loading clients…</p>}
      {!error && !isLoading && filteredClients.length === 0 && (
        <p className="text-muted">No clients match these filters.</p>
      )}
      {!error && filteredClients.length > 0 && (
        <div className="table-card">
          <table className="table">
            <thead>
              <tr>
                <th>Client</th>
                <th>Company</th>
                <th>Jurisdiction</th>
                <th>Risk</th>
                <th>Onboarded</th>
                <th>Next review</th>
              </tr>
            </thead>
            <tbody>
              {filteredClients.map((client) => (
                <tr key={client.client_id} className="clickable" onClick={() => onOpenClient(client.client_id)}>
                  <td>{client.client_id}</td>
                  <td>{client.company_name ?? "—"}</td>
                  <td>{client.jurisdiction ?? "—"}</td>
                  <td>{client.risk_rating ?? "—"}</td>
                  <td>{new Date(client.onboarded_at).toLocaleDateString()}</td>
                  <td>{new Date(client.next_review_date).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
