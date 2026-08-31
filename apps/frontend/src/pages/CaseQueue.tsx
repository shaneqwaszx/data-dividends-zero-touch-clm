import { useEffect, useMemo, useState } from "react";

import { ApiError, fetchCases } from "../api";
import { formatDateNoSeconds, stageProgressLabel } from "../shared";
import type { CaseListItem } from "../types";

function statusTagClass(status: CaseListItem["status"]): string {
  if (status === "COMPLETED") return "tag tag-accent";
  if (status === "WAITING_FOR_REVIEW" || status === "REWORK_REQUIRED") return "tag tag-neutral";
  if (status === "TECHNICAL_FAILURE") return "tag tag-outline";
  return "tag tag-accent-2";
}

export default function CaseQueue({ onOpenCase }: { onOpenCase: (caseId: string) => void }) {
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [status, setStatus] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let current = true;
    setIsLoading(true);
    void fetchCases({ status: status || undefined, jurisdiction: jurisdiction || undefined })
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
  }, [status, jurisdiction]);

  const filteredCases = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return cases;
    return cases.filter((item) =>
      [item.company_name, item.requested_uen, item.case_id]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLowerCase().includes(query)),
    );
  }, [cases, search]);

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
        <select
          className="input"
          style={{ width: 200 }}
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">Status: All</option>
          <option value="RUNNING">In review</option>
          <option value="WAITING_FOR_REVIEW">Attention required</option>
          <option value="REWORK_REQUIRED">Rework</option>
          <option value="COMPLETED">Completed</option>
        </select>
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
        <div className="table-card">
          <table className="table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Registration ID</th>
                <th>Jurisdiction</th>
                <th>Status</th>
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
                  onClick={() => onOpenCase(item.case_id)}
                >
                  <td>{item.company_name ?? item.requested_uen}</td>
                  <td>{item.requested_uen}</td>
                  <td>{item.jurisdiction ?? "—"}</td>
                  <td>
                    <span className={statusTagClass(item.status)}>
                      {item.status.replaceAll("_", " ")}
                    </span>
                  </td>
                  <td>{stageProgressLabel(item.current_stage)}</td>
                  <td>{item.assigned_to ?? "—"}</td>
                  <td>{formatDateNoSeconds(item.created_at)}</td>
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
