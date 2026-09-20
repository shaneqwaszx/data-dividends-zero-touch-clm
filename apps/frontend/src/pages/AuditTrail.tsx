import { useEffect, useState } from "react";
import { Link } from "react-router";

import { ApiError, fetchZeroTouchCase, fetchZeroTouchCases } from "../api";
import { paths } from "../navigation";
import { formatTimestamp } from "../shared";
import type { AuditEntryView } from "../viewModels";
import { mapCaseTimelineToAuditEntries } from "../viewModels";
import { PriorityBadge } from "./PriorityControl";

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

export default function AuditTrail({ caseId }: { caseId?: string | null }) {
  const [entries, setEntries] = useState<AuditEntryView[]>([]);
  const [action, setAction] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setIsLoading(true);
    const load = async () => {
      const summaries = caseId
        ? [await fetchZeroTouchCase(caseId, controller.signal)]
        : await Promise.all(
            (await fetchZeroTouchCases(undefined, "all", "highest_first", undefined, controller.signal))
              .map((item) => fetchZeroTouchCase(item.case_id, controller.signal)),
          );
      const allEntries = summaries.flatMap(mapCaseTimelineToAuditEntries);
      return allEntries.filter((entry) => matchesAction(entry, action));
    };
    void load()
      .then((items) => {
        if (!current) return;
        setEntries(items);
        setError(null);
      })
      .catch((requestError) => {
        if (!current || controller.signal.aborted) return;
        setError(
          requestError instanceof ApiError ? requestError.message : "The audit trail is unavailable.",
        );
      })
      .finally(() => {
        if (current) setIsLoading(false);
      });
    return () => {
      current = false;
      controller.abort();
    };
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
            <Link className="btn btn-ghost" to={paths.audit}>
              Clear case filter
            </Link>
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
                <th>Priority</th>
                <th>Client scope</th>
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
                  <td><PriorityBadge priority={entry.priority} /></td>
                  <td>{entry.client_scope_label ?? "Legacy unassigned"}</td>
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
