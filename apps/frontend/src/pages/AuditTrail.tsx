import { useEffect, useState } from "react";

import { ApiError, fetchZeroTouchCase, fetchZeroTouchCases } from "../api";
import { formatTimestamp } from "../shared";
import type { AuditEntryView } from "../viewModels";
import { mapCaseTimelineToAuditEntries } from "../viewModels";

const ACTIONS = ["CREATED", "DOCUMENT", "RECONCILIATION", "OWNERSHIP", "TARGET", "COMPLETED"];

function matchesAction(entry: AuditEntryView, action: string): boolean {
  if (!action) return true;
  if (action === "CREATED") return entry.action.includes("CREATED");
  if (action === "DOCUMENT") return entry.stage === "DOCUMENT";
  if (action === "RECONCILIATION") return entry.action.includes("RECONCILIATION");
  if (action === "OWNERSHIP") return entry.stage === "OWNERSHIP";
  if (action === "TARGET") return entry.stage === "MOCK_GOLDTIER" || entry.action.includes("MOCK_SUBMISSION");
  if (action === "COMPLETED") return entry.action.includes("COMPLETED") || entry.stage === "COMPLETE";
  return false;
}

export default function AuditTrail({ initialCaseId }: { initialCaseId?: string | null }) {
  const [entries, setEntries] = useState<AuditEntryView[]>([]);
  const [action, setAction] = useState("");
  const [caseId, setCaseId] = useState(initialCaseId ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    const load = async () => {
      const summaries = caseId
        ? [await fetchZeroTouchCase(caseId)]
        : await Promise.all((await fetchZeroTouchCases()).map((item) => fetchZeroTouchCase(item.case_id)));
      const allEntries = summaries.flatMap(mapCaseTimelineToAuditEntries);
      return allEntries.filter((entry) => matchesAction(entry, action));
    };
    void load()
      .then((items) => {
        setEntries(items);
        setError(null);
      })
      .catch((requestError) => {
        setError(
          requestError instanceof ApiError ? requestError.message : "The audit trail is unavailable.",
        );
      })
      .finally(() => setIsLoading(false));
  }, [action, caseId]);

  return (
    <div className="ds-root ds-page">
      <div className="ds-page-header">
        <div>
          <h1>Audit trail</h1>
          <p className="text-muted">
            {entries.length} entries{caseId ? ` for ${caseId}` : ""}.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {caseId && (
            <button type="button" className="btn btn-ghost" onClick={() => setCaseId("")}>
              Clear case filter
            </button>
          )}
          <button className="btn btn-secondary" type="button" disabled title="Not available in current POC">
            Export CSV
          </button>
        </div>
      </div>
      <div className="ds-toolbar">
        <button
          type="button"
          className={action === "" ? "tag tag-accent" : "tag tag-neutral"}
          onClick={() => setAction("")}
        >
          All
        </button>
        {ACTIONS.map((item) => (
          <button
            key={item}
            type="button"
            className={action === item ? "tag tag-accent" : "tag tag-neutral"}
            onClick={() => setAction(item)}
          >
            {item.toLowerCase()}
          </button>
        ))}
      </div>
      <p className="control-help">Backend timeline events only. Actor and loop are not supplied; CSV export is not available in current POC.</p>
      {error && <div className="ds-banner ds-banner-warn">{error}</div>}
      {!error && isLoading && <p className="text-muted">Loading audit trail…</p>}
      {!error && !isLoading && entries.length === 0 && (
        <p className="text-muted">No entries match this filter.</p>
      )}
      {!error && entries.length > 0 && (
        <div className="table-card table-scroll" tabIndex={0} aria-label="Audit trail events">
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>By</th>
                <th>Change</th>
                <th>Loop</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.entry_id}>
                  <td>{formatTimestamp(entry.timestamp)}</td>
                  <td>
                    <span className="tag tag-accent-2">{entry.action.toLowerCase()}</span>
                  </td>
                  <td>{entry.actor ?? "—"}</td>
                  <td>{entry.description}</td>
                  <td>{entry.loop_number ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
