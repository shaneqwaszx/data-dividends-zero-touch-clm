import { useEffect, useMemo, useState } from "react";

import { ApiError, fetchZeroTouchCase, fetchZeroTouchCases } from "../api";
import type { OnboardedRowView } from "../viewModels";
import { mapCompletedCaseToOnboardedRow } from "../viewModels";

export default function OnboardedClients({
  onOpenClient,
}: {
  onOpenClient: (clientId: string) => void;
}) {
  const [clients, setClients] = useState<OnboardedRowView[]>([]);
  const [jurisdiction, setJurisdiction] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    void fetchZeroTouchCases("COMPLETED")
      .then(async (items) => {
        const details = await Promise.all(items.map((item) => fetchZeroTouchCase(item.case_id)));
        setClients(items.map((item, index) => mapCompletedCaseToOnboardedRow(item, details[index])));
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
  }, []);

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

      {error && <div className="ds-banner ds-banner-warn">{error}</div>}
      {!error && isLoading && <p className="text-muted">Loading clients…</p>}
      {!error && !isLoading && filteredClients.length === 0 && (
        <p className="text-muted">No clients match these filters.</p>
      )}
      {!error && filteredClients.length > 0 && (
        <div className="table-card table-scroll" tabIndex={0} aria-label="Completed Mock workflow cases">
          <table className="table onboarded-table">
            <thead>
              <tr>
                <th>Mock GoldTier party ID</th>
                <th>Case</th>
                <th>Registration ID</th>
                <th>Company</th>
                <th>Jurisdiction</th>
                <th>Risk</th>
                <th>Onboarded</th>
                <th>Next review</th>
                <th><span className="sr-only">Open</span></th>
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
