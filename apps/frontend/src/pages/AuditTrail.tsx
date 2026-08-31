import { useEffect, useState } from "react";

import { ApiError, auditExportUrl, fetchAuditLog } from "../api";
import { formatTimestamp } from "../shared";
import type { AuditEntry } from "../types";

const ACTIONS: AuditEntry["action"][] = [
  "CREATE",
  "EXTRACT",
  "UPDATE",
  "UPLOAD",
  "SUBMIT",
  "CHECK",
  "ASSIGN",
  "APPROVE",
  "RETURN",
  "COMPLETE",
];

export default function AuditTrail({ initialCaseId }: { initialCaseId?: string | null }) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [action, setAction] = useState("");
  const [caseId, setCaseId] = useState(initialCaseId ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    void fetchAuditLog({ action: action || undefined, caseId: caseId || undefined })
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
          <a className="btn btn-secondary" href={auditExportUrl({ action: action || undefined, caseId: caseId || undefined })}>
            Export CSV
          </a>
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
      {error && <div className="ds-banner ds-banner-warn">{error}</div>}
      {!error && isLoading && <p className="text-muted">Loading audit trail…</p>}
      {!error && !isLoading && entries.length === 0 && (
        <p className="text-muted">No entries match this filter.</p>
      )}
      {!error && entries.length > 0 && (
        <div className="table-card">
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
                  <td>{entry.actor}</td>
                  <td>{entry.description}</td>
                  <td>{entry.loop_number}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
